// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PowerSaver V5 - Production-Ready MEV-Arbitrage Executor
 * @notice Gas-optimized, fully hardened security
 */
contract PowerSaverV5 {
    // ============ ERRORS ============
    error NotOwner();
    error Paused();
    error NotAuthorized();
    error InvalidParams();
    error InvalidRouter();
    error SlippageExceeded();
    error NotAavePool();
    error InvalidInitiator();
    error ProfitTooLow();
    error Reentrancy();
    error ApproveFail();
    error MaxLoanExceeded();
    error TransferFail();

    // ============ STATE ============
    address public owner;
    bool public paused;
    bool public ownerOnly = true;

    mapping(address => bool) public authorized;

    // Routers + Aave Pool (mainnet defaults)
    address public immutable uniV2;
    address public immutable sushi;
    address public immutable uniV3;
    address public immutable aavePool;

    // Limits
    uint256 public maxLoan = type(uint256).max;
    uint256 public ttl = 120;  // Transaction deadline in seconds

    // Reentrancy guard
    bool private locked;

    // Stats
    uint256 public totalLoans;
    uint256 public totalProfit;

    // Events
    event Executed(address indexed asset, uint256 amount, uint256 premium, uint256 profit);
    event SetPaused(bool paused);
    event SetOwnerOnly(bool ownerOnly);
    event SetAuth(address indexed user, bool authorized);
    event SetRouter(bytes32 indexed which, address router);
    event SetAavePool(address pool);
    event SetMaxLoan(uint256 maxLoan);
    event SetTTL(uint256 ttl);
    event OwnershipTransferred(address indexed oldOwner, address indexed newOwner);
    event Withdraw(address indexed token, uint256 amount);
    event Route(bytes32 indexed routeHash);

    // ============ MODIFIERS ============
    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier whenNotPaused() {
        if (paused) revert Paused();
        _;
    }

    modifier nonReentrant() {
        if (locked) revert Reentrancy();
        locked = true;
        _;
        locked = false;
    }

    constructor() {
        owner = msg.sender;
        authorized[msg.sender] = true;
        
        // Set router addresses
        uniV2 = address(uint160(0x7a250d5630b4cf539739df2c5dacb4c659f2488d));
        sushi = address(uint160(0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f));
        uniV3 = address(uint160(0xe592427a0aece92de3edee1f18e0157c05861564));
        aavePool = address(uint160(0x87870bca3f3fd6335c3fbdc83e7a82f43aa0b2fe));
    }

    // ============ ENTRY POINT ============
    function requestFlashLoan(
        address asset,
        uint256 amount,
        bytes calldata params
    ) external whenNotPaused {
        // Security: ownerOnly option
        if (ownerOnly) {
            if (msg.sender != owner) revert NotAuthorized();
        } else {
            if (!authorized[msg.sender]) revert NotAuthorized();
        }
        
        if (amount == 0) revert InvalidParams();
        if (amount > maxLoan) revert MaxLoanExceeded();

        // Emit route hash for debugging
        emit Route(keccak256(params));

        IAavePool(aavePool).flashLoanSimple(address(this), asset, amount, params, 0);
    }

    // ============ AAVE CALLBACK ============
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external whenNotPaused nonReentrant returns (bool) {
        if (msg.sender != aavePool) revert NotAavePool();
        if (initiator != address(this)) revert InvalidInitiator();

        // Decode swap plan
        (
            address[] memory path,
            address[] memory routers,
            uint24[] memory v3Fees,
            uint256[] memory minOuts,
            uint256 minProfit
        ) = abi.decode(params, (address[], address[], uint24[], uint256[], uint256));

        // Validation
        uint256 hops = routers.length;
        if (hops == 0) revert InvalidParams();
        if (path.length != hops || minOuts.length != hops || v3Fees.length != hops) 
            revert InvalidParams();
        
        // Security: route must end in original asset for repayment
        if (path[hops - 1] != asset) revert InvalidParams();

        // Execute swaps
        uint256 startBal = IERC20(asset).balanceOf(address(this));
        _swapMulti(asset, amount, path, routers, v3Fees, minOuts);
        uint256 endBal = IERC20(asset).balanceOf(address(this));

        // Robust profit validation
        if (endBal <= startBal + premium) revert ProfitTooLow();
        
        uint256 profit = endBal - (startBal + premium);
        if (profit < minProfit) revert ProfitTooLow();

        totalLoans++;
        totalProfit += profit;

        // Repay Aave
        _forceApprove(asset, aavePool, amount + premium);

        emit Executed(asset, amount, premium, profit);
        return true;
    }

    // ============ SWAP ENGINE ============
    function _swapMulti(
        address tokenIn,
        uint256 amountIn,
        address[] memory path,
        address[] memory routers,
        uint24[] memory v3Fees,
        uint256[] memory minOuts
    ) internal {
        uint256 current = amountIn;
        address currentToken = tokenIn;
        uint256 deadline = block.timestamp + ttl;

        for (uint256 i = 0; i < routers.length; i++) {
            address r = routers[i];
            address tokenOut = path[i];

            // Router whitelist
            if (r != uniV2 && r != sushi && r != uniV3) revert InvalidRouter();

            // V3 fee validation
            if (r == uniV3 && v3Fees[i] == 0) revert InvalidParams();

            if (r == uniV2 || r == sushi) {
                _forceApprove(currentToken, r, current);
                address[] memory p = new address[](2);
                p[0] = currentToken;
                p[1] = tokenOut;

                uint256[] memory out = IUniV2(r).swapExactTokensForTokens(
                    current, minOuts[i], p, address(this), deadline
                );
                uint256 got = out[out.length - 1];
                if (got < minOuts[i]) revert SlippageExceeded();
                current = got;
            } else {
                _forceApprove(currentToken, r, current);
                current = IUniV3(r).exactInputSingle(
                    IUniV3.ExactInputSingleParams({
                        tokenIn: currentToken,
                        tokenOut: tokenOut,
                        fee: v3Fees[i],
                        recipient: address(this),
                        deadline: deadline,
                        amountIn: current,
                        amountOutMinimum: minOuts[i],
                        sqrtPriceLimitX96: 0
                    })
                );
                if (current < minOuts[i]) revert SlippageExceeded();
            }
            currentToken = tokenOut;
        }
    }

    // ============ SAFE APPROVE/TRANSFER ============
    function _forceApprove(address token, address spender, uint256 amount) internal {
        // 1) Try direct approve
        (bool ok1, bytes memory data1) = token.call(
            abi.encodeWithSelector(IERC20.approve.selector, spender, amount)
        );
        if (ok1 && (data1.length == 0 || abi.decode(data1, (bool)))) return;

        // 2) Reset to zero
        (bool ok2, bytes memory data2) = token.call(
            abi.encodeWithSelector(IERC20.approve.selector, spender, 0)
        );
        if (!(ok2 && (data2.length == 0 || abi.decode(data2, (bool))))) revert ApproveFail();

        // 3) Try approve again
        (bool ok3, bytes memory data3) = token.call(
            abi.encodeWithSelector(IERC20.approve.selector, spender, amount)
        );
        if (!(ok3 && (data3.length == 0 || abi.decode(data3, (bool))))) revert ApproveFail();
    }

    function _safeTransfer(address token, address to, uint256 amount) internal {
        (bool ok, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transfer.selector, to, amount)
        );
        if (!(ok && (data.length == 0 || abi.decode(data, (bool))))) revert TransferFail();
    }

    // ============ ADMIN ============
    function setPause(bool _paused) external onlyOwner {
        paused = _paused;
        emit SetPaused(_paused);
    }

    function setOwnerOnly(bool _ownerOnly) external onlyOwner {
        ownerOnly = _ownerOnly;
        emit SetOwnerOnly(_ownerOnly);
    }

    function setAuth(address user, bool _auth) external onlyOwner {
        authorized[user] = _auth;
        emit SetAuth(user, _auth);
    }

    // NOTE: Routers are immutable - cannot be changed after deployment
    // If you need different routers, deploy a new contract
    
    function setMaxLoan(uint256 _maxLoan) external onlyOwner {
        maxLoan = _maxLoan;
        emit SetMaxLoan(_maxLoan);
    }

    function setTTL(uint256 _ttl) external onlyOwner {
        // Range: 10-600 seconds
        if (_ttl < 10 || _ttl > 600) revert InvalidParams();
        ttl = _ttl;
        emit SetTTL(_ttl);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert InvalidParams();
        address oldOwner = owner;
        
        // Clear old owner authorization
        authorized[oldOwner] = false;
        
        owner = newOwner;
        authorized[newOwner] = true;
        
        emit OwnershipTransferred(oldOwner, newOwner);
    }

    function withdraw(address token, uint256 amount) external onlyOwner {
        if (token == address(0)) {
            payable(owner).transfer(amount);
        } else {
            _safeTransfer(token, owner, amount);
        }
        emit Withdraw(token, amount);
    }

    receive() external payable {}
}

// ===== Interfaces =====
interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
    function transfer(address, uint256) external returns (bool);
}

interface IAavePool {
    function flashLoanSimple(
        address receiverAddress,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

interface IUniV2 {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

interface IUniV3 {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256);
}

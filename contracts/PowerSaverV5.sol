// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PowerSaver V5 - Ultimate MEV-Arbitrage Executor
 * @notice Production-ready, gas-optimized, with full MEV protection
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

    // ============ STATE ============
    address public owner;
    bool public paused;

    mapping(address => bool) public authorized;

    // Routers + Aave Pool
    address public uniV2 = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;
    address public sushi = 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F;
    address public uniV3 = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address public aavePool = 0x87870Bca3F3fD6335C3FbdC83E7a82f43aa0B2fE;

    // Reentrancy guard
    bool private locked;

    // Stats
    uint256 public totalLoans;
    uint256 public totalProfit;

    // Events
    event Executed(address indexed asset, uint256 amount, uint256 premium, uint256 profit);
    event SetPaused(bool paused);
    event SetAuth(address indexed user, bool authorized);
    event SetRouter(bytes32 indexed which, address router);
    event SetAavePool(address pool);
    event Withdraw(address indexed token, uint256 amount);

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
        if (locked) revert NotAuthorized();
        locked = true;
        _;
        locked = false;
    }

    constructor() {
        owner = msg.sender;
        authorized[msg.sender] = true;
    }

    // ============ ENTRY POINT ============
    /**
     * @notice Request Aave V3 simple flash loan
     */
    function requestFlashLoan(
        address asset,
        uint256 amount,
        bytes calldata params
    ) external whenNotPaused {
        if (!authorized[msg.sender]) revert NotAuthorized();
        if (amount == 0) revert InvalidParams();

        IAavePool(aavePool).flashLoanSimple(address(this), asset, amount, params, 0);
    }

    // ============ AAVE CALLBACK ============
    /**
     * @notice Aave V3 callback - validates caller & executes arbitrage
     */
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

        uint256 hops = routers.length;
        if (hops == 0 || path.length != hops || minOuts.length != hops || v3Fees.length != hops) 
            revert InvalidParams();

        // Execute swaps
        uint256 startBal = IERC20(asset).balanceOf(address(this));
        _swapMulti(asset, amount, path, routers, v3Fees, minOuts);
        uint256 endBal = IERC20(asset).balanceOf(address(this));

        // Profit validation
        uint256 required = startBal + premium + minProfit;
        if (endBal < required) revert ProfitTooLow();

        uint256 profit = endBal - (startBal + premium);
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

        for (uint256 i = 0; i < routers.length; i++) {
            address r = routers[i];
            address tokenOut = path[i];

            if (r != uniV2 && r != sushi && r != uniV3) revert InvalidRouter();

            if (r == uniV2 || r == sushi) {
                _forceApprove(currentToken, r, current);
                address[] memory p = new address[](2);
                p[0] = currentToken;
                p[1] = tokenOut;

                uint256[] memory out = IUniV2(r).swapExactTokensForTokens(
                    current, minOuts[i], p, address(this), block.timestamp + 120
                );
                if (out[1] < minOuts[i]) revert SlippageExceeded();
                current = out[1];
            } else {
                _forceApprove(currentToken, r, current);
                current = IUniV3(r).exactInputSingle(
                    IUniV3.ExactInputSingleParams({
                        tokenIn: currentToken,
                        tokenOut: tokenOut,
                        fee: v3Fees[i],
                        recipient: address(this),
                        deadline: block.timestamp + 120,
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

    function _forceApprove(address token, address spender, uint256 amount) internal {
        IERC20(token).approve(spender, 0);
        IERC20(token).approve(spender, amount);
    }

    // ============ ADMIN ============
    function setPause(bool _paused) external onlyOwner {
        paused = _paused;
        emit SetPaused(_paused);
    }

    function setAuth(address user, bool _auth) external onlyOwner {
        authorized[user] = _auth;
        emit SetAuth(user, _auth);
    }

    function setRouter(bytes32 which, address router) external onlyOwner {
        if (which == bytes32("uniV2")) uniV2 = router;
        else if (which == bytes32("uniV3")) uniV3 = router;
        else if (which == bytes32("sushi")) sushi = router;
        else revert InvalidParams();
        emit SetRouter(which, router);
    }

    function setAavePool(address pool) external onlyOwner {
        aavePool = pool;
        emit SetAavePool(pool);
    }

    function withdraw(address token, uint256 amount) external onlyOwner {
        if (token == address(0)) payable(owner).transfer(amount);
        else IERC20(token).transfer(owner, amount);
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

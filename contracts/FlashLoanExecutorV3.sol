// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PowerSaver V3 - Optimized Flash Loan Arbitrage
 * @notice Minimal, gas-optimized, production-ready
 */
contract PowerSaverV3 {
    error NotOwner();
    error Paused();
    error ZeroAmount();
    error SlippageExceeded();
    error NotAuthorized();

    address public owner;
    bool public paused;
    mapping(address => bool) public authorized;

    // Routers
    address public uniV2 = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;
    address public uniV3 = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address public sushi = 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F;
    address public aavePool = 0x87870Bca3F3fD6335C3FbdC83E7a82f43aa0B2fE;

    // Stats
    uint256 public totalLoans;
    uint256 public totalProfit;

    // Events
    event Executed(address token, uint256 amount, uint256 profit);
    event Unauthorized(address user);

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier whenNotPaused() {
        if (paused) revert Paused();
        _;
    }

    constructor() {
        owner = msg.sender;
        authorized[msg.sender] = true;
    }

    /// @notice Aave flash loan callback
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address,
        bytes calldata params
    ) external whenNotPaused returns (bool) {
        if (!authorized[msg.sender] && msg.sender != aavePool) revert NotAuthorized();
        
        (address[] memory path, address[] memory routers, uint256 minOut) = abi.decode(
            params, (address[], address[], uint256)
        );

        uint256 balanceBefore = IERC20(asset).balanceOf(address(this));
        uint256 amountOut = _swapMulti(asset, path, routers, amount);
        
        if (amountOut < minOut) revert SlippageExceeded();

        uint256 profit = amountOut + balanceBefore - amount - premium;
        totalLoans++;
        totalProfit += profit;

        IERC20(asset).approve(aavePool, amount + premium);
        emit Executed(asset, amount, profit);
        
        return true;
    }

    /// @notice Multi-hop swap across DEXes
    function _swapMulti(
        address tokenIn,
        address[] memory path,
        address[] memory routers,
        uint256 amount
    ) internal returns (uint256) {
        uint256 current = amount;
        
        for (uint256 i = 0; i < routers.length && i < path.length; i++) {
            if (routers[i] == uniV2 || routers[i] == sushi) {
                IERC20(tokenIn).approve(routers[i], current);
                address[] memory p = new address[](2);
                p[0] = tokenIn;
                p[1] = path[i];
                uint256[] memory out = IUniV2(routers[i]).swapExactTokensForTokens(
                    current, 0, p, address(this), block.timestamp + 300
                );
                current = out[1];
                tokenIn = path[i];
            } else if (routers[i] == uniV3) {
                IERC20(tokenIn).approve(routers[i], current);
                current = IUniV3(routers[i]).exactInputSingle(
                    IUniV3.ExactInputSingleParams({
                        tokenIn: tokenIn,
                        tokenOut: path[i],
                        fee: 3000,
                        recipient: address(this),
                        deadline: block.timestamp + 300,
                        amountIn: current,
                        amountOutMinimum: 0,
                        sqrtPriceLimitX96: 0
                    })
                );
                tokenIn = path[i];
            }
        }
        return current;
    }

    // === ADMIN ===
    function setPause(bool _paused) external onlyOwner {
        paused = _paused;
    }

    function setAuth(address user, bool _auth) external onlyOwner {
        authorized[user] = _auth;
    }

    function setRouter(string calldata name, address router) external onlyOwner {
        if (keccak256(abi.encodePacked(name)) == keccak256("uniV2")) uniV2 = router;
        else if (keccak256(abi.encodePacked(name)) == keccak256("uniV3")) uniV3 = router;
        else if (keccak256(abi.encodePacked(name)) == keccak256("sushi")) sushi = router;
    }

    function withdraw(address token, uint256 amount) external onlyOwner {
        if (token == address(0)) payable(owner).transfer(amount);
        else IERC20(token).transfer(owner, amount);
    }

    receive() external payable {}
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function approve(address, uint256) external;
    function transfer(address, uint256) external returns (bool);
}

interface IUniV2 {
    function swapExactTokensForTokens(uint256, uint256, address[], address, uint256) 
        external returns (uint256[] memory);
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
    function exactInputSingle(ExactInputSingleParams calldata) external payable returns (uint256);
}

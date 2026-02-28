// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@aave/v3-core/contracts/flashloan/base/FlashLoanSimpleRecipientBase.sol";
import "@aave/v3-core/contracts/interfaces/IPool.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title FlashLoanExecutor
 * @author Autonomous Trading System
 * @notice Advanced flash loan executor with arbitrage capabilities
 * @dev Includes ReentrancyGuard for security
 */
contract FlashLoanExecutor is FlashLoanSimpleRecipientBase, Ownable, ReentrancyGuard {

    // Configuration
    struct TradingConfig {
        uint256 minProfitThreshold; // Minimum profit in basis points (100 = 1%)
        uint256 maxLoanAmount;      // Maximum loan amount
        bool enabled;
    }

    // State
    mapping(address => TradingConfig) public tradingConfigs;
    mapping(bytes32 => bool) public processedLoans;
    uint256 public totalLoansExecuted;
    uint256 public totalProfitEarned;

    // DEX interfaces
    address public uniswapV2Router;
    address public uniswapV3Router;
    address public balancerVault;

    // Emergency pause
    bool public paused;
    mapping(address => bool) public authorizedUsers;

    // Events
    event FlashLoanExecuted(
        address indexed token,
        uint256 amount,
        uint256 fee,
        uint256 profit,
        bytes32 indexed loanId
    );

    event ArbitrageExecuted(
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 amountOut,
        uint256 profit
    );

    event EmergencyPaused(address indexed by, string reason);
    event EmergencyResumed(address indexed by);
    event UserAuthorized(address indexed user);
    event UserDeauthorized(address indexed user);

    constructor(address pool) FlashLoanSimpleRecipientBase(pool) Ownable(msg.sender) {}

    /**
     * @notice Execute flash loan and perform arbitrage
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param params Custom parameters for arbitrage strategy
     */
    function executeArbitrage(
        address token,
        uint256 amount,
        bytes calldata params
    ) external override onlyPool nonReentrant {
        require(!paused, "Contract is paused");
        require(amount > 0, "Invalid amount");

        // Validate loan hasn't been processed
        bytes32 loanId = keccak256(abi.encodePacked(token, amount, msg.sender, block.timestamp));
        require(!processedLoans[loanId], "Loan already processed");

        // Execute arbitrage
        uint256 profit = _executeArbitrage(token, amount, params);

        // Mark as processed
        processedLoans[loanId] = true;

        // Update stats
        totalLoansExecuted++;
        totalProfitEarned += profit;

        // Repay loan with fee
        _repayFlashLoan(token, amount);

        // Emit events
        emit FlashLoanExecuted(token, amount, 0, profit, loanId);
        if (profit > 0) {
            emit ArbitrageExecuted(token, token, amount, amount + profit, profit);
        }
    }

    /**
     * @notice Execute arbitrage with multiple DEXes
     * @param token Token to trade
     * @param amount Amount to trade
     * @param params Parameters for multi-DEX arbitrage
     */
    function _executeArbitrage(address token, uint256 amount, bytes calldata params) internal returns (uint256) {
        // Decode parameters
        (address[] memory tokens, address[] memory exchanges) = abi.decode(params, (address[], address[]));

        require(tokens.length > 0, "No tokens specified");
        require(exchanges.length > 0, "No exchanges specified");

        uint256 initialAmount = amount;
        uint256 currentAmount = amount;

        // Execute swaps on specified exchanges
        for (uint256 i = 0; i < exchanges.length && i < 5; i++) {
            address exchange = exchanges[i];
            address nextToken = tokens[i % tokens.length];

            if (exchange == address(0)) continue;

            currentAmount = _swapOnExchange(token, nextToken, currentAmount, exchange);
            token = nextToken;

            // Safety check: ensure we're not losing value
            require(currentAmount >= initialAmount * 99 / 100, "Excessive slippage");
        }

        return currentAmount - initialAmount;
    }

    /**
     * @notice Swap tokens on Uniswap V2
     * @param fromToken Token to swap from
     * @param toToken Token to swap to
     * @param amount Amount to swap
     * @param minAmountOut Minimum amount out (for slippage protection)
     */
    function _swapOnUniswapV2(
        address fromToken,
        address toToken,
        uint256 amount,
        uint256 minAmountOut
    ) internal returns (uint256) {
        require(uniswapV2Router != address(0), "Router not set");
        require(fromToken != toToken, "Same token");

        // Approve router
        IERC20(fromToken).approve(uniswapV2Router, amount);

        // Execute swap
        uint256[] memory amounts = IUniswapV2Router(uniswapV2Router).swapExactTokensForTokens(
            amount,
            minAmountOut,
            new address[](2){fromToken, toToken},
            address(this),
            block.timestamp + 300 // 5 minute deadline
        );

        return amounts[1];
    }

    /**
     * @notice Swap tokens on Uniswap V3
     * @param fromToken Token to swap from
     * @param toToken Token to swap to
     * @param amount Amount to swap
     * @param minAmountOut Minimum amount out
     */
    function _swapOnUniswapV3(
        address fromToken,
        address toToken,
        uint256 amount,
        uint256 minAmountOut
    ) internal returns (uint256) {
        require(uniswapV3Router != address(0), "Router not set");
        require(fromToken != toToken, "Same token");

        // Approve router
        IERC20(fromToken).approve(uniswapV3Router, amount);

        // Execute swap
        uint256[] memory amounts = IUniswapV3Router(uniswapV3Router).swapExactTokensForTokens(
            amount,
            minAmountOut,
            new address[](2){fromToken, toToken},
            address(this),
            block.timestamp + 300
        );

        return amounts[1];
    }

    /**
     * @notice Swap tokens on Balancer
     * @param fromToken Token to swap from
     * @param toToken Token to swap to
     * @param amount Amount to swap
     * @param minAmountOut Minimum amount out
     */
    function _swapOnBalancer(
        address fromToken,
        address toToken,
        uint256 amount,
        uint256 minAmountOut
    ) internal returns (uint256) {
        require(balancerVault != address(0), "Vault not set");
        require(fromToken != toToken, "Same token");

        // Execute swap
        uint256[] memory amounts = IBalancerVault(balancerVault).swap(
            bytes32(0),
            address(this),
            [IERC20(fromToken), IERC20(toToken)],
            [uint256(amount), uint256(minAmountOut)],
            false
        );

        return amounts[1];
    }

    /**
     * @notice Swap on specified exchange
     * @param fromToken Token to swap from
     * @param toToken Token to swap to
     * @param amount Amount to swap
     * @param exchange Exchange address
     */
    function _swapOnExchange(
        address fromToken,
        address toToken,
        uint256 amount,
        address exchange
    ) internal returns (uint256) {
        if (exchange == uniswapV2Router) {
            return _swapOnUniswapV2(fromToken, toToken, amount, amount * 995 / 1000);
        } else if (exchange == uniswapV3Router) {
            return _swapOnUniswapV3(fromToken, toToken, amount, amount * 995 / 1000);
        } else if (exchange == balancerVault) {
            return _swapOnBalancer(fromToken, toToken, amount, amount * 995 / 1000);
        } else {
            revert("Unknown exchange");
        }
    }

    /**
     * @notice Repay flash loan with fee
     * @param token Token to repay
     * @param amount Amount to repay
     */
    function _repayFlashLoan(address token, uint256 amount) internal {
        // Calculate fee (0.09% for Aave)
        uint256 fee = amount * 9 / 10000;
        uint256 totalRepayment = amount + fee;

        // Transfer repayment to pool
        IERC20(token).transfer(IPool(pool), totalRepayment);
    }

    /**
     * @notice Emergency pause contract
     * @param reason Reason for pause
     */
    function emergencyPause(string calldata reason) external onlyOwner {
        paused = true;
        emit EmergencyPaused(msg.sender, reason);
    }

    /**
     * @notice Resume contract after emergency pause
     */
    function emergencyResume() external onlyOwner {
        paused = false;
        emit EmergencyResumed(msg.sender);
    }

    /**
     * @notice Authorize user to execute trades
     * @param user User address to authorize
     */
    function authorizeUser(address user) external onlyOwner {
        authorizedUsers[user] = true;
        emit UserAuthorized(user);
    }

    /**
     * @notice Deauthorize user
     * @param user User address to deauthorize
     */
    function deauthorizeUser(address user) external onlyOwner {
        authorizedUsers[user] = false;
        emit UserDeauthorized(user);
    }

    /**
     * @notice Withdraw profits
     * @param token Token to withdraw
     * @param amount Amount to withdraw
     */
    function withdrawTokens(address token, uint256 amount) external onlyOwner {
        require(token != address(0), "Invalid token");
        IERC20(token).transfer(msg.sender, amount);
    }

    /**
     * @notice Get contract stats
     */
    function getStats() external view returns (
        uint256 totalLoans,
        uint256 totalProfit,
        bool paused,
        uint256 minProfitThreshold
    ) {
        return (
            totalLoansExecuted,
            totalProfitEarned,
            paused,
            tradingConfigs[msg.sender].minProfitThreshold
        );
    }

    /**
     * @notice Set trading configuration
     * @param config Trading configuration
     */
    function setTradingConfig(TradingConfig calldata config) external onlyOwner {
        tradingConfigs[msg.sender] = config;
    }

    /**
     * @notice Set router addresses
     * @param uniswapV2 Uniswap V2 router address
     * @param uniswapV3 Uniswap V3 router address
     * @param balancer Balancer vault address
     */
    function setRouterAddresses(
        address uniswapV2,
        address uniswapV3,
        address balancer
    ) external onlyOwner {
        uniswapV2Router = uniswapV2;
        uniswapV3Router = uniswapV3;
        balancerVault = balancer;
    }

    /**
     * @notice Get router addresses
     */
    function getRouterAddresses() external view returns (
        address,
        address,
        address
    ) {
        return (uniswapV2Router, uniswapV3Router, balancerVault);
    }

    /**
     * @notice Get authorized users
     */
    function getAuthorizedUsers() external view returns (address[] memory) {
        // Note: This is a simplified version
        // In production, use a mapping with counter
        return new address[](0);
    }

    /**
     * @notice Get processed loans count
     */
    function getProcessedLoansCount() external view returns (uint256) {
        uint256 count = 0;
        for (uint256 i = 0; i < 1000; i++) {
            bytes32 loanId = keccak256(abi.encodePacked(i));
            if (processedLoans[loanId]) {
                count++;
            }
        }
        return count;
    }

    /**
     * @notice Clean up processed loans (for testing)
     * @param loanId Loan ID to clean
     */
    function cleanupProcessedLoan(bytes32 loanId) external onlyOwner {
        processedLoans[loanId] = false;
    }

    /**
     * @notice Fallback function
     */
    receive() external payable {}
}

// Interface for Uniswap V2 Router
interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

// Interface for Uniswap V3 Router
interface IUniswapV3Router {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

// Interface for Balancer Vault
interface IBalancerVault {
    function swap(
        bytes32 poolId,
        address sender,
        address[] calldata tokens,
        uint256[] calldata amounts,
        bool
    ) external returns (uint256[] memory);
}

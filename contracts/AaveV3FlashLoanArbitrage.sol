// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {IPool} from "@aave/core-v3/contracts/interfaces/IPool.sol";
import {IPoolAddressesProvider} from "@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol";
import {IERC20} from "@aave/core-v3/contracts/dependencies/openzeppelin/contracts/IERC20.sol";
import {SafeERC20} from "@aave/core-v3/contracts/dependencies/openzeppelin/contracts/SafeERC20.sol";

/**
 * @title AaveV3FlashLoanArbitrage
 * @dev Flashloan-enabled arbitrage contract for Aave V3
 */
contract AaveV3FlashLoanArbitrage {
    using SafeERC20 for IERC20;

    // Aave V3 Pool addresses (Ethereum Mainnet)
    address public constant AAVE_V3_POOL = 0x87870Bca3F3fD6335C3F4ce6260135144110A857;
    address public constant AAVE_ADDRESSES_PROVIDER = 0x2f39d218133AFaB8F2B819B1066c7E434Ad116E;

    // Owner
    address public owner;

    // Events
    event FlashLoanExecuted(address token, uint256 amount, uint256 profit);
    event ArbitrageExecuted(address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event Withdraw(address token, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Execute flashloan arbitrage
     * @param token0 Address of first token
     * @param token1 Address of second token
     * @param amount Amount to borrow
     * @param router Uniswap router address
     * @param path Swap path (token0 -> token1 -> token0)
     */
    function executeArbitrage(
        address token0,
        address token1,
        uint256 amount,
        address router,
        bytes calldata path
    ) external onlyOwner {
        // Request flashloan from Aave V3
        address[] memory assets = new address[](1);
        assets[0] = token0;

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;

        uint16 referralCode = 0;

        IPool(AAVE_V3_POOL).flashLoan(
            address(this),
            assets,
            amounts,
            new uint256[](1), // 0 = no debt, 1 = stable debt, 2 = variable debt
            referralCode,
            abi.encode(token0, token1, router, path),
            0
        );
    }

    /**
     * @dev Aave V3 flashloan callback
     * This is called by Aave after providing the flashloan
     */
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(msg.sender == AAVE_V3_POOL, "Not Aave Pool");

        (address token0, address token1, address router, bytes calldata path) = 
            abi.decode(params, (address, address, address, bytes));

        uint256 amount = amounts[0];
        uint256 fee = premiums[0];

        // Approve tokens for swap
        IERC20(token0).forceApprove(AAVE_V3_POOL, amount + fee);

        // Execute arbitrage trade
        // For now, just return the borrowed amount + fee to demonstrate it works
        // In production, you would do: token0 -> token1 -> token0 on Uniswap

        emit FlashLoanExecuted(token0, amount, fee);

        return true;
    }

    /**
     * @dev Withdraw tokens from contract
     */
    function withdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner, amount);
        emit Withdraw(token, amount);
    }

    /**
     * @dev Withdraw ETH
     */
    function withdrawETH(uint256 amount) external onlyOwner {
        payable(owner).transfer(amount);
        emit Withdraw(address(0), amount);
    }

    // Receive ETH
    receive() external payable {}
}

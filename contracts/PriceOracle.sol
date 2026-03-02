"""
On-Chain Price Oracle Contract
This is the SOL contract that publishes prices to blockchain
Other DeFi protocols will use this as price reference

Deploy this contract first, then configure the address in the publisher
"""

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PriceOracle
 * @notice On-chain price oracle that can be used by other DeFi protocols
 * @dev Other contracts read prices from this contract
 */
contract PriceOracle {
    
    // ===== EVENTS =====
    event PriceUpdated(address indexed token, uint256 price, uint256 timestamp, address updater);
    
    // ===== STATE =====
    // Admin who can update prices
    address public admin;
    
    // Mapping of token address to price data
    struct PriceData {
        uint256 price;          // Price with 8 decimals (Chainlink standard)
        uint256 timestamp;      // Last update timestamp
        uint256 roundId;        // Incrementing round ID
    }
    
    mapping(address => PriceData) public prices;
    
    // Token symbol mapping (for convenience)
    mapping(address => string) public tokenSymbols;
    
    // List of supported tokens
    address[] public supportedTokens;
    
    // ===== MODIFIERS =====
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }
    
    // ===== CONSTRUCTOR =====
    constructor(address _admin) {
        admin = _admin;
    }
    
    // ===== ADMIN FUNCTIONS =====
    
    /**
     * @notice Update price for a token
     * @param token Token address
     * @param price Price with 8 decimals (e.g., 1850_50000000 = $1850.50)
     */
    function updatePrice(address token, uint256 price) external onlyAdmin {
        require(price > 0, "Price must be > 0");
        require(token != address(0), "Invalid token");
        
        PriceData storage data = prices[token];
        
        // First time adding token
        if (data.roundId == 0) {
            supportedTokens.push(token);
        }
        
        data.price = price;
        data.timestamp = block.timestamp;
        data.roundId++;
        
        emit PriceUpdated(token, price, block.timestamp, msg.sender);
    }
    
    /**
     * @notice Batch update multiple prices
     * @param tokens Array of token addresses
     * @param prices_ Array of prices (must match length)
     */
    function batchUpdate(address[] calldata tokens, uint256[] calldata prices_) external onlyAdmin {
        require(tokens.length == prices_.length, "Length mismatch");
        
        for (uint256 i = 0; i < tokens.length; i++) {
            updatePrice(tokens[i], prices_[i]);
        }
    }
    
    /**
     * @notice Set token symbol
     * @param token Token address
     * @param symbol Token symbol (e.g., "ETH")
     */
    function setTokenSymbol(address token, string calldata symbol) external onlyAdmin {
        tokenSymbols[token] = symbol;
    }
    
    /**
     * @notice Transfer admin
     * @param newAdmin New admin address
     */
    function transferAdmin(address newAdmin) external onlyAdmin {
        require(newAdmin != address(0), "Invalid address");
        admin = newAdmin;
    }
    
    // ===== PUBLIC VIEW FUNCTIONS =====
    
    /**
     * @notice Get current price for token
     * @param token Token address
     * @return price Price with 8 decimals
     * @return timestamp Last update time
     */
    function getPrice(address token) external view returns (uint256 price, uint256 timestamp) {
        PriceData memory data = prices[token];
        require(data.roundId > 0, "Token not supported");
        return (data.price, data.timestamp);
    }
    
    /**
     * @notice Get price with staleness check
     * @param token Token address
     * @param maxAge Maximum age in seconds before reverting
     * @return price Price with 8 decimals
     */
    function getPriceFresh(address token, uint256 maxAge) external view returns (uint256 price) {
        PriceData memory data = prices[token];
        require(data.roundId > 0, "Token not supported");
        require(block.timestamp - data.timestamp <= maxAge, "Price stale");
        return data.price;
    }
    
    /**
     * @notice Get round data (like Chainlink)
     * @param token Token address
     * @return roundId Round ID
     * @return price Price with 8 decimals
     * @return timestamp Update timestamp
     */
    function getRoundData(address token) external view returns (
        uint256 roundId,
        uint256 price,
        uint256 timestamp
    ) {
        PriceData memory data = prices[token];
        require(data.roundId > 0, "Token not supported");
        return (data.roundId, data.price, data.timestamp);
    }
    
    /**
     * @notice Get latest round ID for token
     * @param token Token address
     * @return roundId Latest round ID
     */
    function latestRound(address token) external view returns (uint256 roundId) {
        return prices[token].roundId;
    }
    
    /**
     * @notice Get all supported tokens
     * @return Array of token addresses
     */
    function getSupportedTokens() external view returns (address[] memory) {
        return supportedTokens;
    }
    
    /**
     * @notice Check if token is supported
     * @param token Token address
     * @return true if supported
     */
    function isSupported(address token) external view returns (bool) {
        return prices[token].roundId > 0;
    }
}

/**
 * ===== HOW TO USE =====
 * 
 * 1. DEPLOY CONTRACT:
 *    Deploy PriceOracle.sol with your admin address
 *    Example: 0xYourOracleAddress
 * 
 * 2. CONFIGURE PUBLISHER:
 *    Set ORACLE_CONTRACT_ADDRESS=0xYourOracleAddress
 *    in on_chain_oracle_publisher.py
 * 
 * 3. OTHER DEFI PROTOCOLS READ PRICE:
 * 
 *    // In your DeFi contract:
 *    interface IPriceOracle {
 *        function getPrice(address token) external view returns (uint256 price, uint256 timestamp);
 *    }
 *    
 *    contract MyDefiProtocol {
 *        IPriceOracle public oracle = IPriceOracle(0xYourOracleAddress);
 *        
 *        function getEthPrice() external view returns (uint256) {
 *            (uint256 price,) = oracle.getPrice(0xWETH);
 *            return price;
 *        }
 *    }
 * 
 * 4. PUBLISH PRICE:
 *    curl -X POST http://localhost:8080/api/signal \
 *      -H "Content-Type: application/json" \
 *      -d '{
 *        "signal": "publish",
 *        "token": "ETH",
 *        "price": 1850.50,
 *        "source": "uniswap"
 *      }'
 */

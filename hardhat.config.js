require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const pk = process.env.PRIVATE_KEY || process.env.TRADING_WALLET_PRIVATE_KEY;
const sepoliaUrl = process.env.SEPOLIA_RPC_URL || "https://sepolia.infura.io/v3/7a6465e870ad43b19e62011d8947c2bd";

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.19",
  networks: {
    mainnet: {
      url: process.env.ETHEREUM_RPC_URL || "http://localhost:8545",
      accounts: pk ? [pk] : [],
      chainId: 1,
    },
    sepolia: {
      url: sepoliaUrl,
      accounts: pk ? [pk] : [],
      chainId: 11155111,
    },
    localhost: {
      url: "http://localhost:8545",
      chainId: 31337,
    },
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY || "",
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS === "true",
    currency: "USD",
  },
};

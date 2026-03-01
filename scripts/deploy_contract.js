/**
 * PowerSaver Contract Deployment Script
 * Deploys FlashLoanExecutorV2 to Ethereum mainnet
 */

const hre = require("hardhat");

async function main() {
  console.log("🚀 Deploying PowerSaver FlashLoan Executor...\n");

  // Mainnet Aave V3 Pool
  const AAVE_POOL_MAINNET = "0x87870Bca3F3fD6335C3FbdC83E7a82f43aa0B2fE";
  
  // Sepolia Testnet (for testing)
  const AAVE_POOL_SEPOLIA = "0x6Ae43d3271ff6888e7Fc43Fd7321e5031dA2E2A";

  // Get network
  const network = hre.network.name;
  const poolAddress = network === "mainnet" ? AAVE_POOL_MAINNET : AAVE_POOL_SEPOLIA;

  console.log(`📍 Network: ${network}`);
  console.log(`🏦 Aave Pool: ${poolAddress}\n`);

  // Deploy contract
  const FlashLoanExecutor = await hre.ethers.getContractFactory("FlashLoanExecutorV2");
  
  const contract = await FlashLoanExecutor.deploy(poolAddress);
  
  await contract.waitForDeployment();
  const contractAddress = await contract.getAddress();

  console.log("✅ Contract deployed successfully!");
  console.log(`📄 Address: ${contractAddress}\n`);

  // Verify deployment
  const owner = await contract.owner();
  const isPaused = await contract.paused();
  
  console.log("📋 Deployment Details:");
  console.log(`   Owner: ${owner}`);
  console.log(`   Paused: ${isPaused}`);
  console.log(`   Aave Pool: ${await contract.AAVE_POOL()}`);
  console.log(`   Uniswap V2: ${await contract.uniswapV2Router()}`);
  console.log(`   Uniswap V3: ${await contract.uniswapV3Router()}`);
  console.log(`   Sushiswap: ${await contract.sushiswapRouter()}`);
  console.log(`   Balancer: ${await contract.balancerVault()}\n`);

  // Add your bot as executor (replace with your bot address)
  const BOT_ADDRESS = process.env.BOT_ADDRESS || "YOUR_BOT_ADDRESS";
  if (BOT_ADDRESS !== "YOUR_BOT_ADDRESS") {
    console.log(`🤖 Adding bot as executor: ${BOT_ADDRESS}`);
    const tx = await contract.addExecutor(BOT_ADDRESS);
    await tx.wait();
    console.log("✅ Bot added as executor\n");
  }

  console.log("📝 Next Steps:");
  console.log(`   1. Verify contract on Etherscan:`);
  console.log(`      npx hardhat verify --network ${network} ${contractAddress} ${poolAddress}`);
  console.log(`   2. Fund the contract with native ETH for gas`);
  console.log(`   3. Set up your bot's .env with CONTRACT_ADDRESS=${contractAddress}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

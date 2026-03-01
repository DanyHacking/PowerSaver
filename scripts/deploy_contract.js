/**
 * PowerSaver V3 Deployment
 */
const hre = require("hardhat");

async function main() {
  console.log("🚀 Deploying PowerSaver V3...\n");

  const network = hre.network.name;
  const poolAddress = network === "mainnet" 
    ? "0x87870Bca3F3fD6335C3FbdC83E7a82f43aa0B2fE"  // Mainnet
    : "0x6Ae43d3271ff6888e7Fc43Fd7321e5031dA2E2A"; // Sepolia

  console.log(`Network: ${network}`);
  console.log(`Aave Pool: ${poolAddress}\n`);

  const PowerSaver = await hre.ethers.getContractFactory("PowerSaverV3");
  const contract = await PowerSaver.deploy();
  
  await contract.waitForDeployment();
  const addr = await contract.getAddress();

  console.log("✅ Deployed!");
  console.log(`Address: ${addr}\n`);
  
  console.log(`📝 Next: npx hardhat verify --network ${network} ${addr}`);
}

main().catch(console.error);

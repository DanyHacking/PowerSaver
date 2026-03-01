/**
 * PowerSaver V5 Deployment
 */
const hre = require("hardhat");

async function main() {
  console.log("🚀 Deploying PowerSaver V5...\n");

  const network = hre.network.name;
  console.log(`Network: ${network}\n`);

  const PowerSaver = await hre.ethers.getContractFactory("PowerSaverV5");
  const contract = await PowerSaver.deploy();
  
  await contract.waitForDeployment();
  const addr = await contract.getAddress();

  console.log("✅ Deployed!");
  console.log(`Address: ${addr}`);
  console.log(`\nOwner: ${await contract.owner()}`);
  console.log(`UniV2: ${await contract.uniV2()}`);
  console.log(`UniV3: ${await contract.uniV3()}`);
  console.log(`Sushi: ${await contract.sushi()}`);
  console.log(`AavePool: ${await contract.aavePool()}`);
}

main().catch(console.error);

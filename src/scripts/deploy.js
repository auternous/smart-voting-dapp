const { ethers, artifacts, network } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log(`👤 Deployer: ${deployer.address}`);
  const balance = await deployer.getBalance();
  console.log(`💰 ETH Balance: ${ethers.utils.formatEther(balance)} ETH`);

  console.log("📦 Deploying PollToken...");
  const PollToken = await ethers.getContractFactory("PollToken");
  const token = await PollToken.deploy();
  await token.deployed();
  console.log(`✅ PollToken deployed at: ${token.address}`);

  console.log("🗳️ Deploying PollSystem...");
  const PollSystem = await ethers.getContractFactory("PollSystem");
  const pollSystem = await PollSystem.deploy(token.address, deployer.address); // relayer = deployer
  await pollSystem.deployed();
  console.log(`✅ PollSystem deployed at: ${pollSystem.address}`);

  console.log("💸 Sending 1000 POLL to PollSystem...");
  const giveTokens = await token.transfer(pollSystem.address, ethers.utils.parseEther("1000"));
  await giveTokens.wait();
  console.log("✅ Token transfer complete.");

  // ✅ Make sure deployments/ directory exists
  const outputDir = path.join(__dirname, "../deployments");
  fs.mkdirSync(outputDir, { recursive: true });

  // 🧾 Write deploy.json
  const deploymentData = {
    pollTokenAddress: token.address,
    pollSystemAddress: pollSystem.address,
    relayer: deployer.address,
    network: network.name,
    timestamp: new Date().toISOString()
  };
  fs.writeFileSync(
    path.join(outputDir, "deploy.json"),
    JSON.stringify(deploymentData, null, 2)
  );

  // ✅ Save ABI *as array* directly
  const pollTokenArtifact = await artifacts.readArtifact("PollToken");
  fs.writeFileSync(
    path.join(outputDir, "poll_token_abi.json"),
    JSON.stringify(pollTokenArtifact.abi, null, 2)  // <--- WRITE RAW ABI
  );

  const pollSystemArtifact = await artifacts.readArtifact("PollSystem");
  fs.writeFileSync(
    path.join(outputDir, "poll_system_abi.json"),
    JSON.stringify(pollSystemArtifact.abi, null, 2)
  );

  // ✅ .env for backend
  const backendEnv = `
RPC_URL=http://127.0.0.1:8545
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
CONTRACT_ADDRESS=${pollSystem.address}
POLL_TOKEN_ADDRESS=${token.address}
`.trim();

  fs.writeFileSync(path.join(__dirname, "../backend/.env"), backendEnv);

  // ✅ .env for frontend
  const frontendEnv = `
VITE_POLL_SYSTEM_ADDRESS=${pollSystem.address}
VITE_POLL_TOKEN_ADDRESS=${token.address}
VITE_BACKEND_API_URL=http://localhost:8000
`.trim();

  fs.writeFileSync(path.join(__dirname, "../frontend/.env"), frontendEnv);

  console.log("✅ Deployment complete! ABI + .env files generated.");
}

main().catch((err) => {
  console.error("❌ Deployment error:", err);
  process.exit(1);
});
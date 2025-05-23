async function main() {
  const [deployer] = await ethers.getSigners();
  
  // Деплой PollToken
  const PollToken = await ethers.getContractFactory("PollToken");
  const token = await PollToken.deploy();
  console.log("PollToken deployed to:", await token.getAddress());

  // Деплой PollSystem
  const PollSystem = await ethers.getContractFactory("PollSystem");
  const pollSystem = await PollSystem.deploy(await token.getAddress());
  
  console.log("PollSystem deployed to:", await pollSystem.getAddress());
  console.log("Transaction hash:", pollSystem.deploymentTransaction().hash);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
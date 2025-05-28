async function main() {
  const [deployer] = await ethers.getSigners();

  const PollToken = await ethers.getContractFactory("PollToken");
  const token = await PollToken.deploy();
  await token.deployed();
  console.log("PollToken deployed to:", token.address);

  const someValue = 42; // <--- Определи нужное значение здесь

  const PollSystem = await ethers.getContractFactory("PollSystem");
  const pollSystem = await PollSystem.deploy(token.address, someValue);
  await pollSystem.deployed();

  console.log("PollSystem deployed to:", pollSystem.address);
  console.log("Transaction hash:", pollSystem.deployTransaction.hash);
}

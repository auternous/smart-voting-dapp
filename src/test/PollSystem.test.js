const { expect } = require("chai");
const { ethers } = require("hardhat");
const { parseEther } = ethers;

describe("PollSystem", function () {
  let pollSystem, token;
  let owner, user1, user2;

  beforeEach(async () => {
    [owner, user1, user2] = await ethers.getSigners();

    const PollTokenFactory = await ethers.getContractFactory("PollToken");
    token = await PollTokenFactory.deploy();
    await token.waitForDeployment();

    const PollSystemFactory = await ethers.getContractFactory("PollSystem");
    pollSystem = await PollSystemFactory.deploy(token.target);
    await pollSystem.waitForDeployment();

    await token.transfer(user1.address, parseEther("1000"));
    await token.transfer(user2.address, parseEther("1000"));
  });

  describe("Poll Creation", () => {
    it("Should require token payment", async () => {
      await token.connect(user1).approve(pollSystem.target, parseEther("100"));
      await expect(
        pollSystem.connect(user1).createPoll("Test?", ["Yes", "No"], 3600)
      ).to.emit(pollSystem, "PollCreated");
    });
  });

  describe("Voting", () => {
    beforeEach(async () => {
      await token.connect(user1).approve(pollSystem.target, parseEther("100"));
      await pollSystem.connect(user1).createPoll("Test?", ["Yes", "No"], 86400);
    });

    it("Should allow gasless voting", async () => {
      const pollId = 0;
      const optionId = 1;
      const messageHash = ethers.solidityPackedKeccak256(
        ["uint256", "uint256"],
        [pollId, optionId]
      );
      const signature = await user2.signMessage(ethers.getBytes(messageHash));

      await expect(
        pollSystem.connect(owner).voteWithSignature(pollId, optionId, signature)
      ).to.emit(pollSystem, "Voted");
    });
  });
  
  describe("View Functions", () => {
  beforeEach(async () => {
    // Увеличиваем approve и создаем два опроса
    await token.connect(user1).approve(
      await pollSystem.getAddress(), 
      ethers.parseEther("200") // Двойная сумма для двух опросов
    );
    
    await pollSystem.connect(user1).createPoll("Poll 1", ["A", "B"], 3600);
    await pollSystem.connect(user1).createPoll("Poll 2", ["X", "Y", "Z"], 3600);
  });

  it("Should return all poll IDs", async () => {
    const ids = await pollSystem.getAllPolls();
    expect(ids.length).to.equal(2);
    expect(ids[0]).to.equal(0);
    expect(ids[1]).to.equal(1);
  });

  it("Should return poll results", async () => {
    // Голосуем в первом опросе за вариант 1
    const messageHash = ethers.solidityPackedKeccak256(
      ["uint256", "uint256"], 
      [0, 1] // pollId = 0, optionId = 1
    );
    const signature = await user2.signMessage(ethers.getBytes(messageHash));
    await pollSystem.connect(owner).voteWithSignature(0, 1, signature);

    const results = await pollSystem.getPollResults(0);
    expect(results.length).to.equal(2); // Два варианта в первом опросе
    expect(results[0]).to.equal(0); // Вариант A - 0 голосов
    expect(results[1]).to.equal(1); // Вариант B - 1 голос
  });
});
});

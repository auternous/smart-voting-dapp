const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("PollSystem", function () {
  let PollSystem;
  let pollSystem;
  let owner;
  let addr1;
  let addr2;

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    
    PollSystem = await ethers.getContractFactory("PollSystem");
    pollSystem = await PollSystem.deploy(); // Убрали .deployed()
    // В Hardhat 6+ deployed() не требуется, так как deploy() уже возвращает готовый контракт
  });

  // Остальные тесты остаются без изменений
  it("Should create a new poll", async function () {
    const question = "Favorite color?";
    const options = ["Red", "Green", "Blue"];
    const duration = 3600;
    
    await expect(pollSystem.createPoll(question, options, duration))
      .to.emit(pollSystem, "PollCreated")
      .withArgs(0, question);
    
    const poll = await pollSystem.getPoll(0);
    expect(poll.question).to.equal(question);
    expect(poll.options).to.deep.equal(options);
    expect(poll.votes).to.deep.equal([0, 0, 0]);
  });

  it("Should allow voting", async function () {
    await pollSystem.createPoll("Q?", ["A", "B"], 3600);
    
    // Первое голосование
    await expect(pollSystem.connect(addr1).vote(0, 0))
      .to.emit(pollSystem, "Voted")
      .withArgs(0, 0);
    
    let poll = await pollSystem.getPoll(0);
    expect(poll.votes).to.deep.equal([1, 0]);
    
    // Второе голосование другим пользователем
    await pollSystem.connect(addr2).vote(0, 1);
    poll = await pollSystem.getPoll(0);
    expect(poll.votes).to.deep.equal([1, 1]);
  });

  it("Should prevent double voting", async function () {
    await pollSystem.createPoll("Q?", ["A"], 3600);
    await pollSystem.connect(addr1).vote(0, 0);
    
    await expect(
      pollSystem.connect(addr1).vote(0, 0)
    ).to.be.revertedWith("Already voted");
  });

  it("Should prevent voting after end time", async function () {
    // Опрос длится 1 секунду
    await pollSystem.createPoll("Q?", ["A"], 1);
    
    // Ждём 2 секунды
    await new Promise(res => setTimeout(res, 2000));
    
    await expect(
      pollSystem.vote(0, 0)
    ).to.be.revertedWith("Poll ended");
  });

  it("Should prevent voting for invalid options", async function () {
    await pollSystem.createPoll("Q?", ["A"], 3600);
    
    await expect(
      pollSystem.vote(0, 1) // Несуществующий вариант
    ).to.be.revertedWith("Invalid option");
  });

  it("Should return correct poll count", async function () {
    expect(await pollSystem.pollCount()).to.equal(0);
    
    await pollSystem.createPoll("Q1?", ["A"], 3600);
    expect(await pollSystem.pollCount()).to.equal(1);
    
    await pollSystem.createPoll("Q2?", ["B"], 3600);
    expect(await pollSystem.pollCount()).to.equal(2);
  });

  it("Should restrict poll creation to admins", async function () {
    const [admin, creator, user] = await ethers.getSigners();
    
    // Только админ может добавлять создателей
    await pollSystem.connect(admin).addPollCreator(creator.address);
    
    // Проверяем создание опроса
    await expect(
      pollSystem.connect(creator).createPoll("Admin question", ["Yes", "No"], 3600)
    ).to.emit(pollSystem, "PollCreated");
  
    // Обычный пользователь не может создать опрос
    await expect(
      pollSystem.connect(user).createPoll("User question", ["Yes", "No"], 3600)
    ).to.be.revertedWith("Only poll creators");
  });
  
});
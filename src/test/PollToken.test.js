const { expect } = require("chai");
const { ethers } = require("hardhat");
const { parseEther } = require("ethers");

describe("PollToken", function () {
  let token;
  let owner, addr1;

  beforeEach(async () => {
    [owner, addr1] = await ethers.getSigners();
    const PollToken = await ethers.getContractFactory("PollToken");
    token = await PollToken.deploy();
  });

  it("Should have correct name and symbol", async () => {
    expect(await token.name()).to.equal("Poll Token");
    expect(await token.symbol()).to.equal("POLL");
  });

  it("Should mint initial supply to owner", async () => {
    const ownerBalance = await token.balanceOf(owner.address);
    expect(ownerBalance).to.equal(parseEther("1000000"));
  });

  it("Should transfer tokens between accounts", async () => {
    await token.transfer(addr1.address, parseEther("1000"));
    expect(await token.balanceOf(addr1.address)).to.equal(parseEther("1000"));
  });
});

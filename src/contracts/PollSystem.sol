// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PollSystem {
    address public admin;
    mapping(address => bool) public pollCreators;
    
    struct Poll {
        string question;
        string[] options;
        uint256[] votes;
        uint256 endTime;
        mapping(address => bool) voters;
    }

    uint256 public pollCount;
    mapping(uint256 => Poll) public polls;

    event PollCreated(uint256 pollId, string question);
    event Voted(uint256 pollId, uint256 optionId);

    constructor() {
        admin = msg.sender; 
        pollCreators[msg.sender] = true; 
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    modifier onlyPollCreator() {
        require(pollCreators[msg.sender], "Only poll creators");
        _;
    }

    function addPollCreator(address _creator) public onlyAdmin {
        pollCreators[_creator] = true;
    }

    function createPoll(string memory _question, string[] memory _options, uint256 _duration) public onlyPollCreator {
        Poll storage newPoll = polls[pollCount];
        newPoll.question = _question;
        newPoll.options = _options;
        newPoll.votes = new uint256[](_options.length);
        newPoll.endTime = block.timestamp + _duration;

        emit PollCreated(pollCount, _question);
        pollCount++;
    }

    function vote(uint256 _pollId, uint256 _optionId) public {
        require(_optionId < polls[_pollId].options.length, "Invalid option");
        require(!polls[_pollId].voters[msg.sender], "Already voted");
        require(block.timestamp <= polls[_pollId].endTime, "Poll ended");

        polls[_pollId].votes[_optionId]++;
        polls[_pollId].voters[msg.sender] = true;
        emit Voted(_pollId, _optionId);
    }

    function getPoll(uint256 _pollId) public view returns (
        string memory question,
        string[] memory options,
        uint256[] memory votes,
        uint256 endTime
    ) {
        Poll storage poll = polls[_pollId];
        return (poll.question, poll.options, poll.votes, poll.endTime);
    }
}
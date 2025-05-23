// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

contract PollSystem {
    using ECDSA for bytes32;
    
    IERC20 public pollToken;
    address public admin;
    uint256 public pollCreationFee = 100 ether;

    struct Poll {
        string question;
        string[] options;
        uint256 endTime;
        mapping(address => bool) voters;
        mapping(uint256 => uint256) votes;
    }

    mapping(uint256 => Poll) public polls;
    uint256 public pollCount;

    event PollCreated(uint256 indexed pollId, string question);
    event Voted(uint256 indexed pollId, address voter, uint256 optionId);

    constructor(address _token) {
        pollToken = IERC20(_token);
        admin = msg.sender;
    }

    function createPoll(
        string memory _question,
        string[] memory _options,
        uint256 _duration
    ) external {
        pollToken.transferFrom(msg.sender, admin, pollCreationFee);
        
        Poll storage newPoll = polls[pollCount];
        newPoll.question = _question;
        newPoll.options = _options;
        newPoll.endTime = block.timestamp + _duration;
        
        emit PollCreated(pollCount, _question);
        pollCount++;
    }

    function voteWithSignature(
        uint256 _pollId,
        uint256 _optionId,
        bytes memory _signature
    ) external {
        bytes32 messageHash = keccak256(abi.encodePacked(_pollId, _optionId));
        address voter = ECDSA.recover(messageHash, _signature);
        
        Poll storage poll = polls[_pollId];
        require(!poll.voters[voter], "Already voted");
        require(_optionId < poll.options.length, "Invalid option");
        require(block.timestamp <= poll.endTime, "Poll ended");

        poll.votes[_optionId]++;
        poll.voters[voter] = true;
        emit Voted(_pollId, voter, _optionId);
    }

    function getAllPolls() external view returns (uint256[] memory) {
        uint256[] memory ids = new uint256[](pollCount);
        for (uint256 i = 0; i < pollCount; i++) {
            ids[i] = i;
        }
        return ids;
    }

    function getPollResults(uint256 _pollId) external view returns (uint256[] memory) {
        uint256[] memory results = new uint256[](polls[_pollId].options.length);
        for (uint256 i = 0; i < results.length; i++) {
            results[i] = polls[_pollId].votes[i];
        }
        return results;
    }

    function getPoll(uint256 _pollId) external view returns (
        string memory question,
        string[] memory options,
        uint256 endTime
    ) {
        Poll storage poll = polls[_pollId];
        return (poll.question, poll.options, poll.endTime);
    }
}
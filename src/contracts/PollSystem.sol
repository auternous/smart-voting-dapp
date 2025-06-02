// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

contract PollSystem {
    using ECDSA for bytes32;

    IERC20 public pollToken;
    address public relayer;

    uint256 public pollCreationFee = 100 ether; // За создание опроса
    uint256 public voteReward = 10 ether;       // Награда за голос

    struct Poll {
        string question;
        string[] options;
        uint256 endTime;
        mapping(address => bool) voters;
        mapping(uint256 => uint256) votes;
    }

    uint256 public pollCount;
    mapping(uint256 => Poll) private polls;

    event PollCreated(uint256 indexed pollId, string question);
    event Voted(uint256 indexed pollId, address indexed voter, uint256 optionId);
    event Rewarded(address indexed voter, uint256 amount);

    constructor(address _token, address _relayer) {
        pollToken = IERC20(_token);
        relayer = _relayer;
    }

    function createPoll(
        string memory _question,
        string[] memory _options,
        uint256 _duration
    ) external {
        require(bytes(_question).length > 0, "Empty question");
        require(_options.length >= 2, "Need at least 2 options");
        require(_duration > 0, "Duration must be > 0");

        // Пользователь платит токенами за создание опроса
        bool success = pollToken.transferFrom(msg.sender, address(this), pollCreationFee);
        require(success, "Poll creation fee failed");

        Poll storage newPoll = polls[pollCount];
        newPoll.question = _question;
        newPoll.options = _options;
        newPoll.endTime = block.timestamp + _duration;

        emit PollCreated(pollCount, _question);
        pollCount++;
    }

    function voteWithSignature(
        uint256 pollId,
        uint256 optionId,
        address voter,
        bytes memory signature
    ) external {
        require(msg.sender == relayer, "Only relayer can relay");

        Poll storage poll = polls[pollId];

        require(!poll.voters[voter], "Already voted");
        require(optionId < poll.options.length, "Invalid option");
        require(block.timestamp <= poll.endTime, "Poll ended");

        // Восстановление подписи
        bytes32 dataHash = keccak256(abi.encodePacked(pollId, optionId, voter));
        bytes32 ethSignedHash = dataHash.toEthSignedMessageHash();
        address recovered = ethSignedHash.recover(signature);
        require(recovered == voter, "Invalid signature");

        // Зачисление голоса
        poll.votes[optionId]++;
        poll.voters[voter] = true;

        emit Voted(pollId, voter, optionId);

        // 🎁 Выплата за голос
        bool success = pollToken.transfer(voter, voteReward);
        require(success, "Reward transfer failed");
        emit Rewarded(voter, voteReward);
    }

    function getPoll(uint256 pollId)
        external
        view
        returns (
            string memory question,
            string[] memory options,
            uint256 endTime
        )
    {
        Poll storage p = polls[pollId];
        return (p.question, p.options, p.endTime);
    }

    // Результаты опроса
    function getVotes(uint256 pollId) external view returns (uint256[] memory results) {
        Poll storage p = polls[pollId];
        uint256 length = p.options.length;
        results = new uint256[](length);
        for (uint256 i = 0; i < length; i++) {
            results[i] = p.votes[i];
        }
    }

    // Получить все pollId
    function getAllPollIds() external view returns (uint256[] memory ids) {
        ids = new uint256[](pollCount);
        for (uint256 i = 0; i < pollCount; i++) {
            ids[i] = i;
        }
    }

    // Проверка, голосовал ли пользователь
    function hasVoted(uint256 pollId, address user) external view returns (bool) {
        return polls[pollId].voters[user];
    }
}
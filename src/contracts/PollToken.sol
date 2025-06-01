// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract PollToken is ERC20 {
    constructor() ERC20("Poll Token", "POLL") {
        _mint(msg.sender, 1000000 * 1e18);
    }
}

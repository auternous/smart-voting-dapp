// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract PollToken is ERC20, Ownable {
    constructor() ERC20("Poll Token", "POLL") {
        _mint(msg.sender, 1000000 * 1e18); // Начальная эмиссия 1 млн токенов
    }

    /**
     * @dev Функция для выпуска новых токенов (доступна только владельцу контракта)
     * @param to Адрес получателя новых токенов
     * @param amount Количество токенов для выпуска (в наименьших единицах)
     */
    function mint(address to, uint256 amount) public onlyOwner {
        _mint(to, amount);
    }
}
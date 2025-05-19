const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

module.exports = buildModule("PollSystemModule", (m) => {
  const adminAddress = m.getParameter("admin", "0x9b989F0E49326425aa292b333e2cbE202BfDa089");

  // Деплоим с передачей адреса админа в конструктор
  const pollSystem = m.contract("PollSystem", [adminAddress]);

  return { pollSystem };
});
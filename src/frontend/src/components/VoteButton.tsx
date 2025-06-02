import React from "react";
import { ethers } from "ethers";

type VoteButtonProps = {
  pollId: number;
  optionId: number;
};

declare global {
  interface Window {
    ethereum?: any;
  }
}

const VoteButton: React.FC<VoteButtonProps> = ({ pollId, optionId }) => {
  const vote = async () => {
    try {
      // 1. Проверка MetaMask
      if (!window.ethereum) {
        alert("🦊 Установи MetaMask, чтобы голосовать");
        return;
      }

      // 2. Подключение к кошельку
      const provider = new ethers.providers.Web3Provider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const signer = provider.getSigner();
      const voter = await signer.getAddress();

      // 3. Подготовка хэша голоса
      const messageHash = ethers.utils.solidityKeccak256(
        ["uint256", "uint256", "address"],
        [pollId, optionId, voter]
      );

      const arrayifiedHash = ethers.utils.arrayify(messageHash);

      // 4. Подписание сообщения
      const signature = await signer.signMessage(arrayifiedHash);

      // 5. Отправка на бэкенд (relay)
      const response = await fetch(
        `${import.meta.env.VITE_BACKEND_API_URL}/relay-vote`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            poll_id: pollId,
            option_id: optionId,
            voter: voter,
            signature: signature,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        alert("❌ Ошибка: " + (data.detail || "Ошибка при голосовании"));
      } else {
        alert("✅ Голос принят! Tx: " + data.tx_hash);
      }
    } catch (error) {
      console.error("Ошибка голосования:", error);
      alert("❌ Что-то пошло не так");
    }
  };

  return (
    <button onClick={vote}>
      Голосовать за вариант #{optionId}
    </button>
  );
};

export default VoteButton;
import React, { useEffect, useState } from "react";
import { ethers } from "ethers";

type VoteButtonProps = {
  pollId: number;
  optionId: number;
  currentAddress: string | null;
};

declare global {
  interface Window {
    ethereum?: any;
  }
}

const VoteButton: React.FC<VoteButtonProps> = ({ pollId, optionId, currentAddress }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);

  useEffect(() => {
    if (!currentAddress) return;
    const key = `voted_${pollId}_${currentAddress}`;
    setHasVoted(!!localStorage.getItem(key));
  }, [pollId, currentAddress]);

  const showError = (message: string) => alert(`❌ ${message}`);
  const showSuccess = (message: string) => alert(`✅ ${message}`);

  const vote = async () => {
    if (hasVoted) {
      showError("Вы уже голосовали в этом опросе");
      return;
    }

    setIsLoading(true);

    try {
      if (!window.ethereum) {
        showError("🦊 Установите MetaMask для голосования");
        return;
      }

      const provider = new ethers.providers.Web3Provider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const signer = provider.getSigner();
      const voter = await signer.getAddress();

      const messageHash = ethers.utils.solidityKeccak256(
        ["uint256", "uint256", "address"],
        [pollId, optionId, voter]
      );

      const arrayifiedHash = ethers.utils.arrayify(messageHash);
      const signature = await signer.signMessage(arrayifiedHash);

      const response = await fetch(`${import.meta.env.VITE_BACKEND_API_URL}/relay-vote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          poll_id: pollId,
          option_id: optionId,
          voter,
          signature,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        const errorString = JSON.stringify(data);
        if (errorString.includes("Already voted")) {
          showError("Вы уже голосовали в этом опросе");
        } else {
          showError(data.detail || "Ошибка при отправке голоса");
        }
        return;
      }

      showSuccess(`Ваш голос за вариант #${optionId} принят!`);
      localStorage.setItem(`voted_${pollId}_${voter}`, "true");
      setHasVoted(true);
      window.dispatchEvent(new Event("vote-recorded"));
    } catch (error: any) {
      console.error("Ошибка голосования:", error);
      const msg = error?.message || "";
      if (msg.includes("Already voted")) {
        showError("Вы уже голосовали в этом опросе");
      } else if (msg.includes("User denied")) {
        showError("Вы отклонили MetaMask запрос");
      } else {
        showError("Произошла неизвестная ошибка");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={vote}
      disabled={isLoading || hasVoted}
      className={`px-4 py-2 rounded-md font-medium ${
        hasVoted
          ? "bg-gray-300 text-gray-600 cursor-not-allowed"
          : "bg-blue-600 text-white hover:bg-blue-700"
      } ${isLoading ? "opacity-70 cursor-wait" : ""} transition-colors duration-200`}
    >
      {isLoading ? (
        <span className="flex items-center">
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Обработка...
        </span>
      ) : hasVoted ? (
        "✓ Вы уже голосовали"
      ) : (
        `Голосовать за вариант #${optionId}`
      )}
    </button>
  );
};

export default VoteButton;
import React, { useState } from 'react';
import { ethers } from 'ethers';

// ✅ Импорт ABI
import PollSystemABI from '../../../deployments/poll_system_abi.json';
import PollTokenJson from '../../../deployments/poll_token_abi.json';
const PollTokenABI: any[] = Array.isArray(PollTokenJson) ? PollTokenJson : (PollTokenJson as any).abi;
// ✅ Адреса из .env
const POLL_SYSTEM_ADDRESS = import.meta.env.VITE_POLL_SYSTEM_ADDRESS!;
const POLL_TOKEN_ADDRESS = import.meta.env.VITE_POLL_TOKEN_ADDRESS!;
const POLL_CREATION_FEE = ethers.utils.parseEther("100"); // 100 POLL

export default function CreatePollFormMetaMask() {
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState<string[]>(["", ""]);
  const [duration, setDuration] = useState(600); // В секундах
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const addOption = () => setOptions([...options, ""]);
  const handleOptionChange = (i: number, value: string) => {
    const updated = [...options];
    updated[i] = value;
    setOptions(updated);
  };
  const removeOption = (index: number) => {
    if (options.length <= 2) return;
    setOptions(options.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("⏳ Проверка MetaMask...");
    setLoading(true);

    try {
      if (!window.ethereum) throw new Error("🦊 Установите MetaMask");

      // Провайдер и signer
      const provider = new ethers.providers.Web3Provider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const signer = provider.getSigner();
      const userAddress = await signer.getAddress();

      // Лог адресов и ABI
      console.log("📦 PollToken ABI sample:", PollTokenABI.find((x: any) => x.name === "balanceOf"));
      console.log("📬 PollToken address:", POLL_TOKEN_ADDRESS);

      // Контракты
      const pollToken = new ethers.Contract(POLL_TOKEN_ADDRESS, PollTokenABI, signer);
      const pollSystem = new ethers.Contract(POLL_SYSTEM_ADDRESS, PollSystemABI, signer);

      // ✅ Проверка баланса
      const balance: ethers.BigNumber = await pollToken.balanceOf(userAddress);
      if (balance.lt(POLL_CREATION_FEE)) {
        throw new Error(`❌ Недостаточно POLL. Нужно 100, у вас ${ethers.utils.formatEther(balance)}`);
      }

      // ✅ Проверка allowance
      const allowance: ethers.BigNumber = await pollToken.allowance(userAddress, POLL_SYSTEM_ADDRESS);
      if (allowance.lt(POLL_CREATION_FEE)) {
        setStatus("✍️ Подтвердите разрешение (approve) в MetaMask...");
        const tx = await pollToken.approve(POLL_SYSTEM_ADDRESS, POLL_CREATION_FEE);
        await tx.wait();
        setStatus("✅ Разрешение успешно выдано");
      }

      // 🚀 Вызов createPoll()
      setStatus("📦 Подтвердите создание опроса в MetaMask...");
      const tx = await pollSystem.createPoll(question, options, duration);
      setStatus(`⛓ Ожидание подтверждения транзакции... (${tx.hash})`);
      await tx.wait();
      setStatus(`✅ Опрос создан! Tx: ${tx.hash}`);

      // Очистить форму
      setQuestion("");
      setOptions(["", ""]);
      setDuration(600);
    } catch (err: any) {
      console.error("💥 Ошибка:", err);
      setStatus(`❌ Ошибка: ${err.reason || err.message || "Что-то пошло не так"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 border p-6 rounded-md max-w-xl mx-auto bg-white text-black">
      <h2 className="text-xl font-bold">📋 Новый опрос (через MetaMask)</h2>

      <div>
        <label className="block mb-1">📝 Вопрос:</label>
        <input
          className="w-full border p-2"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          required
        />
      </div>

      <div>
        <label className="block mb-1">🧾 Варианты:</label>
        {options.map((opt, i) => (
          <div key={i} className="flex gap-2 mb-1">
            <input
              className="flex-1 border p-2"
              value={opt}
              onChange={(e) => handleOptionChange(i, e.target.value)}
              required
            />
            {options.length > 2 && (
              <button
                type="button"
                onClick={() => removeOption(i)}
                className="text-red-500"
              >
                ✖️
              </button>
            )}
          </div>
        ))}
        <button type="button" onClick={addOption} className="text-blue-600 text-sm">
          ➕ Добавить вариант
        </button>
      </div>

      <div>
        <label className="block mb-1">⏱️ Длительность (в секундах):</label>
        <input
          type="number"
          className="border p-2 w-full"
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          required
          min={1}
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="px-4 py-2 bg-black text-white rounded disabled:opacity-40"
      >
        🚀 Создать через MetaMask
      </button>

      {status && (
        <p className="mt-4 whitespace-pre-wrap text-sm text-gray-800 border-t pt-2">
          {status}
        </p>
      )}
    </form>
  );
}
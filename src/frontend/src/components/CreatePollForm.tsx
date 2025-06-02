import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';

// Импорт ABI
import PollSystemABI from '../../../deployments/poll_system_abi.json';
import PollTokenJson from '../../../deployments/poll_token_abi.json';

const PollTokenABI: any[] = (PollTokenJson as { abi?: any[] }).abi ?? (PollTokenJson as any[]);
// Адреса из .env
const POLL_SYSTEM_ADDRESS = import.meta.env.VITE_POLL_SYSTEM_ADDRESS!;
const POLL_TOKEN_ADDRESS = import.meta.env.VITE_POLL_TOKEN_ADDRESS!;
const POLL_CREATION_FEE = ethers.utils.parseEther("100"); // 100 POLL

export default function CreatePollFormMetaMask() {
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState<string[]>(["", ""]);
  const [duration, setDuration] = useState(600);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [faucetLoading, setFaucetLoading] = useState(false);
  const [contractOwner, setContractOwner] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<string | null>(null);

  const initUser = async () => {
  if (!window.ethereum) return;
  const provider = new ethers.providers.Web3Provider(window.ethereum);
  const signer = provider.getSigner();
  const address = await signer.getAddress();
  setCurrentUser(address);
};

  // Проверяем владельца контракта при загрузке
  useEffect(() => {
    checkContractOwner();
  }, []);

  useEffect(() => {
  initUser();
}, []);

  useEffect(() => {
  if (!window.ethereum) return;
  

  const handleAccountsChanged = async (accounts: string[]) => {
    if (accounts.length === 0) {
      console.warn("🦊 MetaMask аккаунт не выбран");
      setCurrentUser(null);
    } else {
      const newAddress = accounts[0];
      setCurrentUser(newAddress);

      // Можно также обновить баланс
      try {
        const provider = new ethers.providers.Web3Provider(window.ethereum);
        const pollToken = new ethers.Contract(POLL_TOKEN_ADDRESS, PollTokenABI, provider);
        const balance: ethers.BigNumber = await pollToken.balanceOf(newAddress);
        console.log("👉 Новый баланс:", ethers.utils.formatEther(balance));
      } catch (err) {
        console.error("Ошибка обновления баланса:", err);
      }
    }
  };

  // Подписка на событие
  window.ethereum.on('accountsChanged', handleAccountsChanged);

  // Очистка подписки при удалении компонента
  return () => {
    window.ethereum?.removeListener('accountsChanged', handleAccountsChanged);
  };
}, []);

  const checkContractOwner = async () => {
    try {
      if (!window.ethereum) return;
      
      const provider = new ethers.providers.Web3Provider(window.ethereum);
      const contract = new ethers.Contract(
        POLL_TOKEN_ADDRESS,
        [...PollTokenABI, "function owner() external view returns (address)"],
        provider
      );
      
      const owner = await contract.owner();
      setContractOwner(owner);
      return owner;
    } catch (err) {
      console.error("Ошибка при проверке владельца:", err);
      setStatus("⚠️ Контракт не имеет функции owner()");
      return null;
    }
  };

  const handleFaucet = async () => {
    setFaucetLoading(true);
    setStatus("⏳ Запрос тестовых токенов...");
    
    try {
      if (!window.ethereum) throw new Error("🦊 Установите MetaMask");

      const provider = new ethers.providers.Web3Provider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const signer = provider.getSigner();
      const userAddress = await signer.getAddress();
      setCurrentUser(userAddress);

      const pollToken = new ethers.Contract(POLL_TOKEN_ADDRESS, PollTokenABI, signer);
      
      setStatus("✍️ Подтвердите транзакцию в MetaMask...");
      const tx = await pollToken.mint(userAddress, ethers.utils.parseEther("1000"));
      setStatus(`⛓ Ожидание подтверждения... (${tx.hash})`);
      await tx.wait();
      
      setStatus("✅ Получено 1000 тестовых POLL токенов!");
    } catch (err: any) {
      console.error("💥 Ошибка:", err);
      setStatus(`❌ Ошибка: ${err.reason || err.message || "Не удалось получить токены"}`);
    } finally {
      setFaucetLoading(false);
    }
  };

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

      const provider = new ethers.providers.Web3Provider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const signer = provider.getSigner();
      const userAddress = await signer.getAddress();
      setCurrentUser(userAddress);

      const pollToken = new ethers.Contract(POLL_TOKEN_ADDRESS, PollTokenABI, signer);
      const pollSystem = new ethers.Contract(POLL_SYSTEM_ADDRESS, PollSystemABI, signer);

      // Проверка баланса
      const balance: ethers.BigNumber = await pollToken.balanceOf(userAddress);
      if (balance.lt(POLL_CREATION_FEE)) {
        throw new Error(`❌ Недостаточно POLL. Нужно 100, у вас ${ethers.utils.formatEther(balance)}`);
      }

      // Проверка allowance
      const allowance: ethers.BigNumber = await pollToken.allowance(userAddress, POLL_SYSTEM_ADDRESS);
      if (allowance.lt(POLL_CREATION_FEE)) {
        setStatus("✍️ Подтвердите разрешение (approve) в MetaMask...");
        const tx = await pollToken.approve(POLL_SYSTEM_ADDRESS, POLL_CREATION_FEE);
        await tx.wait();
        setStatus("✅ Разрешение успешно выдано");
      }

      // Создание опроса
      setStatus("📦 Подтвердите создание опроса в MetaMask...");
      const tx = await pollSystem.createPoll(question, options, duration);
      setStatus(`⛓ Ожидание подтверждения транзакции... (${tx.hash})`);
      await tx.wait();
      setStatus(`✅ Опрос создан! Tx: ${tx.hash}`);

      // Очистка формы
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

  const hasMintFunction = PollTokenABI.some(x => x.name === "mint");

  return (
    <form onSubmit={handleSubmit} className="space-y-4 border p-6 rounded-md max-w-xl mx-auto bg-white text-black">
      <h2 className="text-xl font-bold">📋 Новый опрос (через MetaMask)</h2>

      {/* Панель администратора */}
      <div className="bg-gray-50 p-3 rounded-md mb-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-medium">Информация о контракте</h3>
          <button
            type="button"
            onClick={checkContractOwner}
            className="text-xs bg-gray-200 px-2 py-1 rounded"
          >
            🔄 Обновить
          </button>
        </div>
        
        {contractOwner && (
          <p className="text-sm break-all">
            <span className="font-semibold">Владелец контракта:</span> {contractOwner}
          </p>
        )}
        
        {currentUser && (
          <p className="text-sm break-all mt-1">
            <span className="font-semibold">Ваш адрес:</span> {currentUser}
          </p>
        )}

        {hasMintFunction && (
          <button
            type="button"
            onClick={handleFaucet}
            disabled={faucetLoading}
            className="mt-3 w-full px-3 py-2 bg-green-500 text-white rounded disabled:opacity-40"
          >
            {faucetLoading ? "⏳ Обработка..." : "🪙 Получить тестовые токены (1000 POLL)"}
          </button>
        )}
      </div>

      {/* Форма создания опроса */}
      <div>
        <label className="block mb-1">📝 Вопрос:</label>
        <input
          className="w-full border p-2 rounded"
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
              className="flex-1 border p-2 rounded"
              value={opt}
              onChange={(e) => handleOptionChange(i, e.target.value)}
              required
            />
            {options.length > 2 && (
              <button
                type="button"
                onClick={() => removeOption(i)}
                className="text-red-500 px-2"
              >
                ✖
              </button>
            )}
          </div>
        ))}
        <button 
          type="button" 
          onClick={addOption}
          className="text-blue-600 text-sm mt-1"
        >
          ➕ Добавить вариант
        </button>
      </div>

      <div>
        <label className="block mb-1">⏱️ Длительность (в секундах):</label>
        <input
          type="number"
          className="border p-2 w-full rounded"
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          required
          min={1}
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2 bg-black text-white rounded disabled:opacity-40"
      >
        {loading ? "⏳ Обработка..." : "🚀 Создать опрос"}
      </button>

      {status && (
        <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200">
          <p className="whitespace-pre-wrap text-sm">{status}</p>
        </div>
      )}
    </form>
  );
}
import React, { useEffect, useState } from "react";
import { ethers } from "ethers";

declare global {
  interface Window {
    ethereum?: any;
  }
}

export default function UserPanel() {
  const [address, setAddress] = useState<string | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [symbol, setSymbol] = useState<string>("TOKEN");

  useEffect(() => {
    const connectAndFetch = async () => {
      try {
        if (!window.ethereum) {
          console.warn("MetaMask is not installed");
          return;
        }

        const provider = new ethers.providers.Web3Provider(window.ethereum);
        await provider.send("eth_requestAccounts", []);
        const signer = provider.getSigner();
        const userAddress = await signer.getAddress();
        setAddress(userAddress);

        // Получение баланса с бэкенда
        const res = await fetch(`${import.meta.env.VITE_BACKEND_API_URL}/balance/${userAddress}`);
        if (!res.ok) {
          throw new Error("Ошибка получения баланса");
        }

        const data = await res.json();
        const divisor = Math.pow(10, data.decimals);
        setBalance(data.balance / divisor);
        setSymbol(data.symbol);
      } catch (err) {
        console.error("Ошибка подключения:", err);
      }
    };

    connectAndFetch();
  }, []);

  return (
    <div className="text-sm space-y-2">
      <h2 className="text-lg font-bold mb-2">👤 Пользователь</h2>
      {address ? (
        <>
          <p className="break-all">📬 {address}</p>
          <p>💰 Баланс: {balance?.toFixed(4)} {symbol}</p>
        </>
      ) : (
        <p>⏳ Ожидание MetaMask...</p>
      )}
    </div>
  );
}
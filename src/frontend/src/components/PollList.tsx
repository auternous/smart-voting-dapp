import React, { useEffect, useState } from "react";
import VoteButton from "./VoteButton";
import { ethers } from "ethers";

type Poll = {
  id: number;
  question: string;
  options: string[];
  end_time: number;
  votes?: number[];
};

export default function PollList({ search = "" }: { search?: string }) {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [votedPolls, setVotedPolls] = useState<Set<number>>(new Set());
  const [currentAddress, setCurrentAddress] = useState<string | null>(null);

  useEffect(() => {
    const fetchAddress = async () => {
      if (window.ethereum) {
        const provider = new ethers.providers.Web3Provider(window.ethereum);
        const accounts = await provider.send("eth_requestAccounts", []);
        setCurrentAddress(accounts[0]);

        window.ethereum.on("accountsChanged", (accounts: string[]) => {
          setCurrentAddress(accounts[0]);
          window.dispatchEvent(new Event("vote-recorded")); 
        });
      }
    };

    fetchAddress();

    return () => {
      window.ethereum?.removeAllListeners("accountsChanged");
    };
  }, []);

  // Загружаем опросы
  useEffect(() => {
    const fetchPolls = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_BACKEND_API_URL}/polls`);
        const data = await res.json();
        const validPolls = Array.isArray(data) ? data.filter((p) => p?.id !== undefined) : [];
        setPolls(validPolls);
      } catch (err) {
        setError("❌ Не удалось загрузить опросы");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchPolls();
  }, []);

  // Проверяем, за какие опросы голосовал текущий адрес
  useEffect(() => {
    const checkVotes = () => {
      const set = new Set<number>();
      if (!currentAddress) return;

      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!key) continue; // Пропускаем, если ключ отсутствует

        const match = key.match(/^voted_(\d+)_/);
        if (match && key.includes(currentAddress)) {
          set.add(parseInt(match[1]));
        }
      }

      setVotedPolls(set);
    };

    checkVotes();
    window.addEventListener("vote-recorded", checkVotes);
    return () => window.removeEventListener("vote-recorded", checkVotes);
  }, [currentAddress]);

  const filtered = polls.filter((poll) =>
    poll.question.toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => b.id - a.id);

  if (loading) return <p>⌛ Загрузка опросов...</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (filtered.length === 0) return <p>🙁 Опросы не найдены</p>;

  return (
    <div className="space-y-6">
      {sorted.map((poll) => {
        const isFinished = Date.now() / 1000 > poll.end_time;
        const hasVoted = votedPolls.has(poll.id);

        return (
          <div
            key={poll.id}
            className={`border p-4 rounded transition-all ${
              isFinished || hasVoted ? "bg-gray-100 text-gray-500" : "hover:bg-gray-50"
            }`}
          >
            <h3 className="text-lg font-bold mb-2">🗳️ {poll.question}</h3>

            <p className="text-sm mb-3">
              ⏰ Завершение:{" "}
              {new Date(poll.end_time * 1000).toLocaleString()}
            </p>

            {isFinished ? (
              <div>
                <p className="font-semibold text-green-600 mb-1">📊 Результаты:</p>
                <ul className="space-y-1">
                  {poll.options.map((opt, idx) => (
                    <li key={idx}>
                      ✅ {opt}: <strong>{poll.votes?.[idx] ?? 0}</strong> голосов
                    </li>
                  ))}
                </ul>
              </div>
            ) : hasVoted ? (
              <p className="text-blue-600 font-semibold">
                ✅ Вы уже голосовали в этом опросе.
              </p>
            ) : (
              <ul className="space-y-3">
                {poll.options.map((opt, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    <VoteButton pollId={poll.id} optionId={idx} currentAddress={currentAddress} />
                    <span>{opt}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
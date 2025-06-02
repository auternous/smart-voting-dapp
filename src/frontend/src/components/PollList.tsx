import React, { useEffect, useState } from "react";
import VoteButton from "./VoteButton";

type Poll = {
  id: number;
  question: string;
  options: string[];
  end_time: number;          // unix timestamp (в секундах)
  votes?: number[];          // массив результатов (опционально)
};

export default function PollList({ search = "" }: { search?: string }) {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPolls = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_BACKEND_API_URL}/polls`);
        const data = await res.json();

        // 🔍 Фильтруем null/undefined
        const validPolls = Array.isArray(data) ? data.filter((p) => p && p.id !== undefined) : [];
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

  const filtered = polls.filter((poll) =>
    poll.question.toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => b.id - a.id);

  if (loading) return <p>⌛ Загрузка опросов...</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (filtered.length === 0) return <p>🙁 Опросы не найдены</p>;


  return (
    <div className="space-y-4">
      {sorted.map((poll) => {
        const isFinished = Date.now() / 1000 > poll.end_time;

        return (
          <div
            key={poll.id}
            className="border border-typewriter-border p-4 rounded hover:bg-gray-50"
          >
            <h3 className="text-lg font-bold mb-2">🗳️ {poll.question}</h3>

            <p className="text-sm text-gray-600 mb-3">
              ⏰ Завершение:{" "}
              {poll.end_time
                ? new Date(poll.end_time * 1000).toLocaleString()
                : "неизвестно"}
            </p>

            {isFinished ? (
              <div className="bg-gray-100 p-3 rounded text-sm">
                <p className="font-semibold text-green-600 mb-1">📊 Результаты:</p>
                <ul className="space-y-1">
                  {poll.options.map((opt, idx) => (
                    <li key={idx}>
                      ✅ {opt}: <strong>{poll.votes?.[idx] ?? 0}</strong> голосов
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <ul className="space-y-2">
                {poll.options.map((opt, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    <VoteButton pollId={poll.id} optionId={idx} />
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
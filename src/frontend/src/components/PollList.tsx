import React, { useEffect, useState } from "react";
import VoteButton from "./VoteButton";

type Poll = {
  id: number;
  question: string;
  options: string[];
  end_time: number;
};

// ✅ Описываем пропы
export default function PollList({ search = "" }: { search?: string }) {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPolls = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_BACKEND_API_URL}/polls`);
        const data = await res.json();
        setPolls(data);
      } catch (err) {
        setError("Не удалось загрузить опросы");
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

  if (loading) return <p>⌛ Загрузка опросов...</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  if (filtered.length === 0) return <p>🙁 Ни одного опроса не найдено.</p>;

  return (
    <div className="space-y-4">
      {filtered.map((poll) => (
        <div
          key={poll.id}
          className="border border-typewriter-border p-4 transition hover:bg-typewriter-border/25"
        >
          <h3 className="text-lg font-bold mb-2">🗳️ {poll.question}</h3>
          <p className="text-sm mb-2">
            Завершение: {new Date(poll.end_time * 1000).toLocaleString()}
          </p>
          <ul className="space-y-2">
            {poll.options.map((opt, index) => (
              <li key={index}>
                <VoteButton pollId={poll.id} optionId={index} />
                <span className="ml-2">{opt}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
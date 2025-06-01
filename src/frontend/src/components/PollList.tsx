import React, { useEffect, useState } from "react";
import VoteButton from "./VoteButton";

type Poll = {
  id: number;
  question: string;
  options: string[];
  end_time: number;
};

const PollList: React.FC = () => {
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

  if (loading) return <p>Загрузка опросов...</p>;
  if (error) return <p style={{ color: "red" }}>{error}</p>;

  if (polls.length === 0) return <p>Нет активных опросов.</p>;

  return (
    <div>
      {polls.map((poll) => (
        <div key={poll.id} style={{ border: "1px solid #ccc", padding: "16px", marginBottom: "24px" }}>
          <h3>🗳️ Вопрос: {poll.question}</h3>
          <ul>
            {poll.options.map((opt, index) => (
              <li key={index} style={{ marginBottom: "8px" }}>
                <strong>{opt}</strong>
                <br />
                <VoteButton pollId={poll.id} optionId={index} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

export default PollList;
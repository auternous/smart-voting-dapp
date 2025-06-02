import React, { useEffect, useState } from "react";

type Entry = {
  address: string;
  balance: number;
};

export default function Leaderboard() {
  const [topUsers, setTopUsers] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_BACKEND_API_URL}/leaderboard`);
        const data = await res.json();
        setTopUsers(data);
      } catch (err) {
        console.error("Ошибка при получении лидерборда:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, []);

  return (
    <div className="max-w-xl mx-auto p-6 bg-white shadow rounded space-y-4">
      <h2 className="text-2xl font-bold text-center">🏆 Лидерборд POLL</h2>

      {loading ? (
        <p className="text-center">⏳ Загрузка...</p>
      ) : topUsers.length === 0 ? (
        <p className="text-center text-gray-500">😢 Пока никто не попал в таблицу лидеров</p>
      ) : (
        <ol className="space-y-2 list-decimal list-inside">
          {topUsers.map((user, index) => (
            <li
              key={user.address}
              className="flex justify-between text-sm border-b pb-1 last:border-none"
            >
              <span className="font-mono text-gray-700">
                {user.address.slice(0, 6)}...{user.address.slice(-4)}
              </span>
              <span className="font-semibold">{user.balance.toLocaleString()} POLL</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
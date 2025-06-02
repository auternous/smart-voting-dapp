import { useNavigate } from "react-router-dom";
import { useState } from "react";
import PollList from "../components/PollList";

export default function Home() {
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  return (
    <div>
      {/* Кнопка ➕ перехода на create */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">🗳️ Лента опросов</h2>
        <button
          onClick={() => navigate("/create")}
          className="text-xl border border-typewriter-border px-3 py-1 hover:bg-typewriter-border/25"
        >
          ➕
        </button>
      </div>

      <div className="mb-4">
        <label className="block mb-1">🔍 Поиск по вопросу:</label>
        <input
          className="w-full border border-typewriter-border p-2 bg-transparent"
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Введите ключевые слова..."
        />
      </div>

      <PollList search={search} />
    </div>
  );
}
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import HomePage from "./pages/Home";
import CreatePage from "./pages/Create";
import LeaderboardPage from "./pages/Leaderboard";
import InfoPage from "./pages/Info";
import UserPanel from "./components/UserPanel"; // 👈 Новая панель пользователя

export default function App() {
  return (
    <Router>
      <div className="flex h-screen bg-typewriter-bg text-typewriter-text font-mono select-none">
        {/* Левый сайдбар */}
        <aside className="w-52 border-r border-typewriter-border p-4">
          <h1 className="text-xl mb-6">🧮 DApp</h1>
          <nav className="space-y-2 text-lg">
            <Link to="/" className="block hover:underline">🏠 Главная</Link>
            <Link to="/create" className="block hover:underline">➕ Добавить</Link>
            <Link to="/leaderboard" className="block hover:underline">🏆 Лидерборд</Link>
            <Link to="/info" className="block hover:underline">❓ Информация</Link>
          </nav>
        </aside>

        {/* Основной контент */}
        <main className="flex-1 p-6 overflow-y-auto">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/create" element={<CreatePage />} />
            <Route path="/leaderboard" element={<LeaderboardPage />} />
            <Route path="/info" element={<InfoPage />} />
          </Routes>
        </main>

        {/* Правый сайдбар 👇 */}
        <aside className="w-64 border-l border-typewriter-border p-4">
          <UserPanel />
        </aside>
      </div>
    </Router>
  );
}
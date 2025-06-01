import CreatePollForm from "./components/CreatePollForm";
import PollList from "./components/PollList"; // если уже добавлен

export default function App() {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>Smart Voting DApp</h1>

      <CreatePollForm />
      <PollList />
    </div>
  );
}
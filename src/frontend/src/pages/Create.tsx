import CreatePollForm from "../components/CreatePollForm";

export default function Create() {
  return (
    <div>
      <h2 className="text-xl mb-4">Создать новый опрос</h2>
      <CreatePollForm />
    </div>
  );
}
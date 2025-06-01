import React, { useState } from "react";

const CreatePollForm: React.FC = () => {
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState<string[]>(["", ""]);
  const [duration, setDuration] = useState(600); // в секундах (10 мин)
  const [status, setStatus] = useState<string | null>(null);

  const handleOptionChange = (index: number, value: string) => {
    const updated = [...options];
    updated[index] = value;
    setOptions(updated);
  };

  const addOption = () => {
    setOptions([...options, ""]);
  };

  const removeOption = (index: number) => {
    if (options.length <= 2) return;
    const updated = options.filter((_, i) => i !== index);
    setOptions(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("⏳ Создание опроса...");

    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_API_URL}/create-poll`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          options,
          duration,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setStatus(`❌ Ошибка: ${data.detail || "Неизвестная ошибка"}`);
        return;
      }

      setStatus(`✅ Опрос создан! Tx Hash: ${data.tx_hash}`);
      setQuestion("");
      setOptions(["", ""]);
      setDuration(600);
    } catch (err) {
      console.error(err);
      setStatus("❌ Ошибка при отправке запроса");
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ marginTop: "2rem", padding: "1rem", border: "1px solid #ccc" }}>
      <h2>Создать новый опрос</h2>

      <label>📝 Вопрос:</label>
      <input value={question} onChange={(e) => setQuestion(e.target.value)} required />

      <label>🧾 Варианты ответа:</label>
      {options.map((opt, index) => (
        <div key={index} style={{ display: "flex", gap: "0.5rem" }}>
          <input
            value={opt}
            onChange={(e) => handleOptionChange(index, e.target.value)}
            required
          />
          {options.length > 2 && (
            <button type="button" onClick={() => removeOption(index)}>x</button>
          )}
        </div>
      ))}

      <button type="button" onClick={addOption} style={{ marginTop: "0.5rem" }}>
        ➕ Добавить вариант
      </button>

      <label style={{ marginTop: "1rem" }}>⏱️ Длительность (в секундах):</label>
      <input
        type="number"
        value={duration}
        onChange={(e) => setDuration(Number(e.target.value))}
        required
        min={1}
      />

      <button type="submit" style={{ marginTop: "1rem" }}>
        🚀 Создать опрос
      </button>

      {status && <p style={{ marginTop: "1rem" }}>{status}</p>}
    </form>
  );
};

export default CreatePollForm;
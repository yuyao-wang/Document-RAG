"use client";

import { useMemo, useState } from "react";

type Citation = {
  source: string;
  chunk_id: string;
  score?: number;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function Page() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  const send = async () => {
    if (!canSend) return;
    const question = input.trim();
    setInput("");
    setError(null);
    setLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: question }]);

    try {
      const response = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Request failed");
      }

      const data = (await response.json()) as {
        answer: string;
        citations: Citation[];
        query: string;
      };

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer || "(no answer)",
          citations: data.citations || []
        }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <section className="header">
        <span className="kicker">Internal Knowledge</span>
        <h1 className="title">Document RAG Console</h1>
        <p className="subtitle">
          Ask a question against the internal corpus. The assistant will retrieve
          context and show the citation sources.
        </p>
      </section>

      <section className="panel">
        <div className="form">
          <textarea
            className="input"
            rows={4}
            placeholder="Ask about Project Orion, roadmap scope, or ingestion notes..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
          />
          <div className="actions">
            <button className="button" onClick={send} disabled={!canSend}>
              {loading ? "Thinking..." : "Ask"}
            </button>
            <button
              className="button secondary"
              onClick={() => setMessages([])}
              disabled={loading || messages.length === 0}
            >
              Clear
            </button>
          </div>
          {error ? <div className="status">Error: {error}</div> : null}
          {!error && loading ? (
            <div className="status">Retrieving context and drafting an answer...</div>
          ) : null}
        </div>
      </section>

      <section className="chat">
        {messages.length === 0 ? (
          <div className="status">No messages yet. Try asking a question.</div>
        ) : null}
        {messages.map((message, index) => (
          <article
            key={`${message.role}-${index}`}
            className={`message ${message.role}`}
          >
            <span className="label">
              {message.role === "user" ? "User" : "Assistant"}
            </span>
            <div className="message-body">{message.content}</div>
            {message.citations && message.citations.length > 0 ? (
              <div className="citations">
                {message.citations.map((citation, idx) => (
                  <div key={`${citation.source}-${idx}`} className="citation">
                    {citation.source} · {citation.chunk_id}
                  </div>
                ))}
              </div>
            ) : null}
          </article>
        ))}
      </section>
    </main>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMessage, ChatResponse, TOOL_LABEL } from "@/lib/api";
import { Icon } from "./Icon";

type Turn = ChatMessage & { steps?: ChatResponse["steps"]; ai_used?: boolean; blocked?: boolean };

export function ChatBox({
  send,
  suggestions,
  placeholder,
  intro,
}: {
  send: (messages: ChatMessage[]) => Promise<ChatResponse>;
  suggestions: string[];
  placeholder: string;
  intro: string;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (turns.length) endRef.current?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "nearest" });
  }, [turns, busy]);

  async function ask(text: string) {
    if (!text.trim() || busy) return;
    const next: Turn[] = [...turns, { role: "user", content: text.trim() }];
    setTurns(next);
    setInput("");
    setBusy(true);
    setError("");
    try {
      const r = await send(next.map(({ role, content }) => ({ role, content })));
      setTurns([...next, { role: "assistant", content: r.answer, steps: r.steps, ai_used: r.ai_used, blocked: r.blocked }]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-card">
      <div className="space-y-4" role="log" aria-label="Yordamchi bilan suhbat" aria-live="polite" aria-relevant="additions">
        {turns.length === 0 && <div className="chat-greeting"><span className="assistant-symbol mb-4"><Icon name="chat" size={24} /></span><p>{intro}</p></div>}
        {turns.map((t, i) =>
          t.role === "user" ? (
            <div key={i} className="ml-auto max-w-[85%] whitespace-pre-line break-words rounded-2xl rounded-br-sm bg-brand-500 px-4 py-2 text-white">
              {t.content}
            </div>
          ) : (
            <div key={i} className="max-w-[92%] space-y-2">
              <div className={`whitespace-pre-line rounded-2xl rounded-bl-sm px-4 py-3 ${t.blocked ? "bg-amber-50 text-amber-900" : "bg-white ring-1 ring-gray-200"}`}>
                {t.content}
              </div>
              {t.steps && t.steps.length > 0 && (
                <div className="flex flex-wrap gap-1 text-xs text-gray-500">
                  <span>{t.ai_used ? "🤖 AI ishlatgan vositalar:" : "Avtomatik:"}</span>
                  {t.steps.map((s, j) => (
                    <span key={j} className="rounded-full bg-gray-100 px-2 py-0.5" title={s.summary}>
                      {TOOL_LABEL[s.tool] ?? s.tool} · {s.summary}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ),
        )}
        {busy && <div className="loading-notice" role="status"><span className="spinner" />Javob tayyorlanmoqda…</div>}
        <div ref={endRef} />
      </div>
      {error && <p role="alert" className="error-notice mt-3">{error}</p>}
      {turns.length === 0 && (
        <div className="chat-suggestions">
          {suggestions.map((s) => (
            <button key={s} onClick={() => ask(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="chat-compose"
      >
        <input aria-label="Yordamchiga savolingiz" value={input} onChange={(e) => setInput(e.target.value)} placeholder={placeholder} className="text-input" />
        <button disabled={busy || !input.trim()} className="primary-button" aria-label="Savolni yuborish"><Icon name="send" size={20} /><span>Yuborish</span></button>
      </form>
    </div>
  );
}

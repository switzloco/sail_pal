"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CrewMember, Component } from "@/lib/types";
import { Send, Sparkles, User, Bot, Mic, MicOff } from "lucide-react";
import ReactMarkdown from 'react-markdown';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000") + "/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const QUICK_PROMPTS = [
  "A crew member has chest pain and shortness of breath. What should I do?",
  "How do I treat a deep laceration to the forearm at sea?",
  "The main engine cooling water temperature is climbing. What should I check first?",
  "What's the right protocol for suspected heat stroke in the engine room?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [crewContext, setCrewContext] = useState<string>("");
  const [componentContext, setComponentContext] = useState<string>("");
  const [isListening, setIsListening] = useState(false);
  const [succinct, setSuccinct] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;

        recognitionRef.current.onresult = (event: any) => {
          let transcript = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
          }
          setInput(transcript);
        };

        recognitionRef.current.onend = () => {
          setIsListening(false);
        };
      }
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const crew = useQuery({ queryKey: ["crew"], queryFn: () => apiFetch<CrewMember[]>("/crew") });
  const components = useQuery({
    queryKey: ["components"],
    queryFn: () => apiFetch<Component[]>("/components"),
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim() || streaming) return;

    const userMsg: Message = { role: "user", content: text.trim() };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setStreaming(true);

    // Placeholder assistant message that we stream into
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    try {
      const body: Record<string, unknown> = { messages: next, succinct };
      if (crewContext) body.crew_id = crewContext;
      if (componentContext) body.component_id = componentContext;

      const res = await fetch(`${API_BASE}/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE: events separated by \n\n; each starts with "data: "
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const evt of events) {
          const line = evt.trim();
          if (!line.startsWith("data:")) continue;
          const json = line.slice(5).trim();
          try {
            const parsed = JSON.parse(json);
            if (parsed.token) {
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = {
                  role: "assistant",
                  content: copy[copy.length - 1].content + parsed.token,
                };
                return copy;
              });
            }
          } catch {
            // ignore malformed event
          }
        }
      }
    } catch (err) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          role: "assistant",
          content: `[Error: ${(err as Error).message}]`,
        };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  }

  const contextLabel = (() => {
    if (crewContext) {
      const member = crew.data?.find((c) => c.crew_id === crewContext);
      return member ? `${member.full_name} (${member.role})` : null;
    }
    if (componentContext) {
      const comp = components.data?.find((c) => c.component_id === componentContext);
      return comp ? `${comp.name} (${comp.system})` : null;
    }
    return null;
  })();

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)] max-w-3xl">
      <div className="mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="text-ocean-600" size={22} />
          <h1 className="text-2xl font-bold text-slate-900">Ask Gemma</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Powered by <span className="font-semibold">Gemma</span> — Google DeepMind&apos;s open-weights model.
          Ground a question in a specific crew member or component for medical / engineering context.
        </p>
      </div>

      {/* Context selectors */}
      <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
        <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Context:</span>
        <select
          value={crewContext}
          onChange={(e) => {
            setCrewContext(e.target.value);
            if (e.target.value) setComponentContext("");
          }}
          className="text-sm bg-white border border-slate-300 rounded px-2 py-1"
        >
          <option value="">— No crew member —</option>
          {crew.data?.map((c) => (
            <option key={c.crew_id} value={c.crew_id}>
              {c.full_name}
            </option>
          ))}
        </select>
        <select
          value={componentContext}
          onChange={(e) => {
            setComponentContext(e.target.value);
            if (e.target.value) setCrewContext("");
          }}
          className="text-sm bg-white border border-slate-300 rounded px-2 py-1"
        >
          <option value="">— No component —</option>
          {components.data?.map((c) => (
            <option key={c.component_id} value={c.component_id}>
              {c.name}
            </option>
          ))}
        </select>
        {contextLabel && (
          <span className=\"text-xs text-ocean-700 bg-ocean-50 px-2 py-1 rounded\">
            Discussing: {contextLabel}
          </span>
        )}
        <label className=\"flex items-center gap-2 ml-auto cursor-pointer\">
          <input 
            type=\"checkbox\" 
            checked={succinct} 
            onChange={(e) => setSuccinct(e.target.checked)}
            className=\"w-4 h-4 text-ocean-600 rounded border-slate-300 focus:ring-ocean-500\"
          />
          <span className=\"text-xs font-semibold text-slate-600\">Succinct Mode</span>
        </label>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto bg-white rounded-xl border border-slate-200 p-4 space-y-4">
        {messages.length === 0 ? (
          <div>
            <p className="text-sm text-slate-400 mb-3">Try asking:</p>
            <div className="grid gap-2">
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  disabled={streaming}
                  className="text-left text-sm bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg px-3 py-2 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className="flex gap-3">
              <div
                className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  m.role === "user" ? "bg-slate-200 text-slate-600" : "bg-ocean-100 text-ocean-700"
                }`}
              >
                {m.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-500 mb-1">
                  {m.role === "user" ? "You" : "Gemma"}
                </p>
                <div className=\"text-sm text-slate-800 markdown-content\">
                  <ReactMarkdown>
                    {m.content}
                  </ReactMarkdown>
                  {streaming && i === messages.length - 1 && m.role === \"assistant\" && (
                    <span className=\"inline-block w-2 h-4 ml-0.5 bg-ocean-400 animate-pulse\" />
                  )}
                </div>
                {m.role === 'assistant' && m.content.toLowerCase().includes('splint') && (
                  <div className=\"mt-4 p-4 bg-slate-800 rounded-lg border border-blue-500/30\">
                    <p className=\"text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2\">Onboard Visual Aid: Splint Types</p>
                    <img 
                      src={`/api/resource?path=medical_splint_types_1778021722507.png`} 
                      alt=\"Splint Types Diagram\"
                      className=\"rounded border border-slate-700 w-full max-w-md\"
                    />
                    <p className=\"text-xs text-slate-400 mt-2 italic\">Source: Vessel Medical Manual, App. D</p>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage(input);
        }}
        className="mt-4 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder=\"Ask Gemma about a symptom, fault, or decision…\"
          disabled={streaming}
          className=\"flex-1 bg-white border border-slate-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ocean-500\"
          autoCorrect=\"off\"
          spellCheck=\"false\"
          autoComplete=\"off\"
        />
        <button
          type="button"
          onClick={toggleListening}
          className={`px-3 py-2 rounded-lg border transition-colors flex items-center justify-center ${
            isListening 
              ? "bg-red-50 border-red-200 text-red-600 animate-pulse" 
              : "bg-white border-slate-300 text-slate-500 hover:bg-slate-50"
          }`}
          title={isListening ? "Stop listening" : "Start voice-to-text"}
        >
          {isListening ? <MicOff size={18} /> : <Mic size={18} />}
        </button>
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="bg-ocean-600 hover:bg-ocean-700 disabled:bg-slate-300 text-white px-4 py-2 rounded-lg flex items-center gap-1 transition-colors"
        >
          <Send size={16} />
          {streaming ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}

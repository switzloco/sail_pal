"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Gamepad2, User, Bot, Sparkles, Trophy, Anchor, RotateCcw } from "lucide-react";
import ReactMarkdown from 'react-markdown';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000") + "/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function TriviaPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [score, setScore] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Initialize the game
  useEffect(() => {
    if (messages.length === 0) {
      startNewGame();
    }
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function startNewGame() {
    setMessages([]);
    setScore(0);
    await sendMessage("Ahoy Captain Sparky! I'm ready for some trivia. Let's start!", true);
  }

  async function sendMessage(text: string, silent = false) {
    if (!text.trim() || streaming) return;

    const next = silent 
      ? messages 
      : [...messages, { role: "user" as const, content: text.trim() }];
    
    if (!silent) {
      setMessages(next);
      setInput("");
    }
    
    setStreaming(true);

    // Add placeholder for assistant
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    try {
      const res = await fetch(`${API_BASE}/ai/trivia`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next, succinct: false }),
      });

      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

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
                const last = copy[copy.length - 1];
                copy[copy.length - 1] = {
                  ...last,
                  content: last.content + parsed.token,
                };
                return copy;
              });
            }
          } catch { }
        }
      }
    } catch (err) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          role: "assistant",
          content: `[Communication error: ${(err as Error).message}]`,
        };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  }

  // Extract options from the last message if they look like A), B), C), D)
  const lastAssistantMsg = messages.filter(m => m.role === "assistant").pop()?.content ?? "";
  const optionsMatch = lastAssistantMsg.match(/[A-D][\.\)\s]+([^\n]+)/g);
  const options = optionsMatch ? optionsMatch.map(o => o.trim()) : [];

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-6rem)] flex flex-col">
      {/* Header Area */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4 bg-white/40 backdrop-blur-md p-6 rounded-2xl border border-white/20 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-gradient-to-br from-ocean-500 to-ocean-700 rounded-full flex items-center justify-center text-white shadow-lg ring-4 ring-ocean-100 animate-pulse">
            <Gamepad2 size={32} />
          </div>
          <div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight">Trivia Deck</h1>
            <p className="text-sm font-medium text-ocean-700 flex items-center gap-1">
              <Sparkles size={14} />
              With Captain Sparky
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="bg-amber-100 text-amber-800 px-4 py-2 rounded-xl border border-amber-200 flex items-center gap-2 font-bold shadow-sm">
            <Trophy size={18} className="text-amber-600" />
            <span>Bravery Points: {score}</span>
          </div>
          <button 
            onClick={startNewGame}
            className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-500"
            title="Restart Game"
          >
            <RotateCcw size={20} />
          </button>
        </div>
      </div>

      {/* Main Game Area */}
      <div className="flex-1 overflow-hidden flex flex-col bg-slate-900/5 backdrop-blur-sm rounded-3xl border border-slate-200/50 shadow-inner relative">
        {/* Animated Background Elements */}
        <div className="absolute top-10 right-10 opacity-5 pointer-events-none rotate-12">
          <Anchor size={200} />
        </div>
        
        {/* Chat Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((m, i) => (
            <div 
              key={i} 
              className={`flex gap-4 ${m.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div className={`shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center shadow-md ${
                m.role === "user" ? "bg-ocean-600 text-white" : "bg-white text-ocean-600 border border-ocean-100"
              }`}>
                {m.role === "user" ? <User size={20} /> : <Bot size={20} />}
              </div>
              
              <div className={`max-w-[80%] flex flex-col ${m.role === "user" ? "items-end" : ""}`}>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1 px-1">
                  {m.role === "user" ? "Navigator" : "Captain Sparky"}
                </p>
                <div className={`p-4 rounded-2xl shadow-sm text-sm leading-relaxed ${
                  m.role === "user" 
                    ? "bg-ocean-600 text-white rounded-tr-none" 
                    : "bg-white text-slate-800 border border-slate-100 rounded-tl-none"
                }`}>
                  <ReactMarkdown className="prose prose-sm prose-slate max-w-none">
                    {m.content}
                  </ReactMarkdown>
                  {streaming && i === messages.length - 1 && m.role === "assistant" && (
                    <span className="inline-block w-2 h-4 ml-1 bg-ocean-400 animate-bounce align-middle" />
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Interaction Area */}
        <div className="p-6 bg-white/60 backdrop-blur-lg border-t border-slate-200">
          {/* Smart Options */}
          {options.length > 0 && !streaming && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              {options.map((opt, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    const letter = opt.trim()[0];
                    sendMessage(opt);
                    // Basic heuristic for score: if they haven't answered this yet
                    // In a real agent we'd let the agent decide, but we can animate a +10 here if we want
                  }}
                  className="group relative overflow-hidden text-left p-4 bg-white hover:bg-ocean-50 border border-slate-200 hover:border-ocean-300 rounded-2xl transition-all hover:shadow-md active:scale-95"
                >
                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-slate-100 group-hover:bg-ocean-100 text-slate-600 group-hover:text-ocean-600 font-bold mr-3 transition-colors">
                    {opt.trim()[0]}
                  </span>
                  <span className="font-medium text-slate-700 group-hover:text-ocean-800">
                    {opt.substring(2).trim()}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Text Input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage(input);
            }}
            className="flex gap-3"
          >
            <div className="flex-1 relative">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your answer or chat with the Captain..."
                disabled={streaming}
                className="w-full bg-white border border-slate-200 rounded-2xl px-5 py-4 text-sm focus:outline-none focus:ring-4 focus:ring-ocean-500/10 focus:border-ocean-500 transition-all disabled:opacity-50 shadow-sm"
              />
            </div>
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="bg-gradient-to-r from-ocean-600 to-ocean-700 hover:from-ocean-700 hover:to-ocean-800 disabled:from-slate-300 disabled:to-slate-400 text-white px-6 py-4 rounded-2xl flex items-center gap-2 font-bold transition-all shadow-lg hover:shadow-ocean-500/20 active:scale-95"
            >
              <Send size={18} />
              <span className="hidden md:inline">Send</span>
            </button>
          </form>
          
          <div className="mt-4 flex justify-center gap-6">
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
              Captain is Online
            </div>
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
              <Sparkles size={10} />
              Uplifting Facts Enabled
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

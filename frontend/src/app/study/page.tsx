"use client";

import { useEffect, useRef, useState } from "react";
import { Send, GraduationCap, User, Bot, Sparkles, Star, Trophy, Target, ShieldAlert, CheckCircle2, Award } from "lucide-react";
import { getApiKey } from "@/lib/api";
import ReactMarkdown from 'react-markdown';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000") + "/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const MILESTONES = [100, 1000, 5000, 10000, 50000, 100000];

export default function StudyPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [totalPoints, setTotalPoints] = useState(0);
  const [level, setLevel] = useState<"Beginner" | "Intermediate" | "Advanced">("Beginner");
  const [lastScore, setLastScore] = useState<number | null>(null);
  const [showMilestone, setShowMilestone] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load points from local storage
  useEffect(() => {
    const saved = localStorage.getItem("mpic_study_points");
    if (saved) setTotalPoints(parseInt(saved));
  }, []);

  // Save points to local storage
  useEffect(() => {
    localStorage.setItem("mpic_study_points", totalPoints.toString());
    
    // Check milestones
    const reached = MILESTONES.find(m => totalPoints >= m && totalPoints < m + 100); // Heuristic for "just reached"
    if (reached) {
      const acknowledged = localStorage.getItem(`milestone_${reached}`);
      if (!acknowledged) {
        setShowMilestone(reached);
        localStorage.setItem(`milestone_${reached}`, "true");
      }
    }
  }, [totalPoints]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function startSession(selectedLevel: typeof level) {
    setLevel(selectedLevel);
    setMessages([]);
    setLastScore(null);
    await sendMessage(`I'm starting my ${selectedLevel} MPIC study session. Send the first scenario!`, true);
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
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    try {
      const key = getApiKey();
      const res = await fetch(`${API_BASE}/ai/study`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(key ? { "x-api-key": key } : {}) },
        body: JSON.stringify({ messages: next, succinct: false }),
      });

      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";

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
              fullContent += parsed.token;
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

      // Check for score in the response
      const scoreMatch = fullContent.match(/Evaluation:\s*(\d+)\/10/i);
      if (scoreMatch) {
        const score = parseInt(scoreMatch[1]);
        setLastScore(score);
        
        // Multiplier based on level
        const multiplier = level === "Advanced" ? 20 : level === "Intermediate" ? 5 : 1;
        const earned = score * multiplier;
        setTotalPoints(p => p + earned);
      }

    } catch (err) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          role: "assistant",
          content: `[Simulation error: ${(err as Error).message}]`,
        };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto h-[calc(100vh-6rem)] flex flex-col gap-6">
      
      {/* Top HUD */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 bg-slate-900 text-white rounded-3xl p-6 flex items-center justify-between shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl" />
          <div className="relative z-10 flex items-center gap-5">
            <div className="w-16 h-16 bg-gradient-to-tr from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg ring-1 ring-white/20">
              <GraduationCap size={32} />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight">MPIC Simulation Deck</h1>
              <div className="flex gap-2 mt-1">
                {["Beginner", "Intermediate", "Advanced"].map((l) => (
                  <button
                    key={l}
                    onClick={() => startSession(l as any)}
                    disabled={streaming}
                    className={`text-[10px] uppercase tracking-widest font-bold px-3 py-1 rounded-full transition-all ${
                      level === l 
                        ? "bg-white text-indigo-900 shadow-md" 
                        : "bg-white/10 text-white/60 hover:bg-white/20"
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>
          </div>
          
          <div className="relative z-10 text-right">
            <p className="text-[10px] font-bold text-indigo-300 uppercase tracking-widest mb-1">Total Training Points</p>
            <p className="text-4xl font-black text-white tabular-nums flex items-center justify-end gap-2">
              <Star className="text-amber-400 fill-amber-400" size={24} />
              {totalPoints.toLocaleString()}
            </p>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-3xl p-6 flex flex-col justify-center shadow-sm relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-indigo-100 text-indigo-600 rounded-xl">
                <Trophy size={20} />
              </div>
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Next Milestone</p>
            </div>
            {(() => {
              const next = MILESTONES.find(m => m > totalPoints) || 1000000;
              const progress = (totalPoints / next) * 100;
              return (
                <>
                  <div className="flex justify-between items-end mb-2">
                    <p className="text-2xl font-black text-slate-900">{next.toLocaleString()}</p>
                    <p className="text-xs font-bold text-indigo-600">{Math.round(progress)}%</p>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden border border-slate-200 p-0.5">
                    <div 
                      className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full transition-all duration-1000" 
                      style={{ width: `${Math.min(100, progress)}%` }}
                    />
                  </div>
                </>
              )
            })()}
          </div>
        </div>
      </div>

      {/* Main Interface */}
      <div className="flex-1 flex flex-col md:flex-row gap-6 overflow-hidden">
        
        {/* Chat / Simulation Window */}
        <div className="flex-1 flex flex-col bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden relative">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/30">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-10">
                <div className="w-20 h-20 bg-indigo-100 text-indigo-600 rounded-3xl flex items-center justify-center mb-6 animate-bounce">
                  <Target size={40} />
                </div>
                <h2 className="text-2xl font-bold text-slate-800 mb-2">Ready for Duty?</h2>
                <p className="text-slate-500 max-w-sm mb-8">
                  Select your experience level above and start a simulated medical emergency. Your performance will be graded on accuracy and speed.
                </p>
                <div className="flex gap-4">
                  <button onClick={() => startSession("Beginner")} className="px-6 py-3 bg-indigo-600 text-white rounded-2xl font-bold shadow-lg hover:shadow-indigo-500/25 active:scale-95 transition-all">
                    Initialize Simulator
                  </button>
                </div>
              </div>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`flex gap-4 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
                  <div className={`shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center shadow-md ${
                    m.role === "user" ? "bg-slate-800 text-white" : "bg-indigo-600 text-white"
                  }`}>
                    {m.role === "user" ? <User size={20} /> : <Bot size={20} />}
                  </div>
                  <div className={`max-w-[85%] ${m.role === "user" ? "text-right" : ""}`}>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1 px-1">
                      {m.role === "user" ? "MPIC Officer" : "MPIC Mentor"}
                    </p>
                    <div className={`p-5 rounded-3xl text-sm leading-relaxed shadow-sm ${
                      m.role === "user" 
                        ? "bg-slate-800 text-white rounded-tr-none" 
                        : "bg-white text-slate-800 border border-slate-100 rounded-tl-none"
                    }`}>
                    <div className="prose prose-sm prose-slate max-w-none prose-headings:text-indigo-600 prose-headings:mb-2">
                      <ReactMarkdown>
                        {m.content}
                      </ReactMarkdown>
                    </div>
                      {streaming && i === messages.length - 1 && m.role === "assistant" && (
                        <span className="inline-block w-2 h-4 ml-1 bg-indigo-400 animate-pulse align-middle" />
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Input Area */}
          <div className="p-6 bg-white border-t border-slate-100">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendMessage(input);
              }}
              className="flex gap-3"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="State your assessment or medical action..."
                disabled={streaming || messages.length === 0}
                className="flex-1 bg-slate-50 border border-slate-200 rounded-2xl px-6 py-4 text-sm focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={streaming || !input.trim() || messages.length === 0}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white px-8 py-4 rounded-2xl flex items-center gap-2 font-bold transition-all shadow-lg hover:shadow-indigo-500/20 active:scale-95"
              >
                <Send size={18} />
                <span>Submit Action</span>
              </button>
            </form>
          </div>
        </div>

        {/* Sidebar / Stats */}
        <div className="w-full md:w-72 flex flex-col gap-4">
          <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Live Assessment</h3>
            <div className="flex flex-col items-center gap-4 py-4">
              <div className={`w-32 h-32 rounded-full border-8 flex flex-col items-center justify-center transition-all duration-700 ${
                !lastScore ? "border-slate-100 text-slate-200" :
                lastScore >= 8 ? "border-green-500 text-green-600 scale-110" :
                lastScore >= 5 ? "border-amber-400 text-amber-500" :
                "border-red-500 text-red-600 animate-pulse"
              }`}>
                <span className="text-4xl font-black leading-none">{lastScore ?? "--"}</span>
                <span className="text-[10px] font-bold uppercase">Points</span>
              </div>
              <div className="text-center">
                <p className="font-bold text-slate-700">
                  {!lastScore ? "Waiting for assessment..." : 
                   lastScore >= 8 ? "Excellent Work!" : 
                   lastScore >= 5 ? "Room for Improvement" : 
                   "Critical Correction!"}
                </p>
                <p className="text-xs text-slate-400 mt-1">Grade is based on WHO/IMGS standards.</p>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl p-6 text-white shadow-xl flex-1">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Training Tips</h3>
            <div className="space-y-4">
              {[
                { icon: ShieldAlert, text: "Scene safety is always first." },
                { icon: CheckCircle2, text: "Check vitals before administering drugs." },
                { icon: Award, text: "Advanced levels grant 20x points!" }
              ].map((tip, i) => (
                <div key={i} className="flex gap-3 items-start">
                  <tip.icon className="text-indigo-400 shrink-0" size={16} />
                  <p className="text-xs text-slate-300 leading-relaxed">{tip.text}</p>
                </div>
              ))}
            </div>
            <div className="mt-8 pt-8 border-t border-white/5">
               <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Simulation Status</p>
               <div className="flex items-center gap-2">
                 <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                 <p className="text-xs font-bold text-green-500">Real-time Feedback Enabled</p>
               </div>
            </div>
          </div>
        </div>
      </div>

      {/* Milestone Overlay */}
      {showMilestone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-900/80 backdrop-blur-sm animate-in fade-in duration-500">
          <div className="bg-white rounded-[40px] p-10 max-w-sm w-full text-center shadow-2xl relative overflow-hidden animate-in zoom-in-95 duration-300">
            <div className="absolute -top-24 -left-24 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl" />
            <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl" />
            
            <div className="relative z-10">
              <div className="w-24 h-24 bg-gradient-to-tr from-amber-400 to-amber-600 rounded-3xl mx-auto flex items-center justify-center text-white shadow-xl mb-6 -rotate-6">
                <Trophy size={48} />
              </div>
              <h2 className="text-3xl font-black text-slate-900 mb-2">Milestone Reached!</h2>
              <p className="text-slate-500 mb-8 leading-relaxed">
                Outstanding dedication, Officer! You&apos;ve accumulated over <span className="font-bold text-indigo-600">{showMilestone.toLocaleString()}</span> training points. Your proficiency as an MPIC is rising.
              </p>
              <button 
                onClick={() => setShowMilestone(null)}
                className="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold shadow-lg hover:bg-slate-800 transition-all active:scale-95"
              >
                Continue Training
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

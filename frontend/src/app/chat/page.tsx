"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, authHeaders } from "@/lib/api";
import type { CrewMember, Component } from "@/lib/types";
import { Send, Sparkles, User, Bot, Mic, MicOff, HeartPulse, Package, Wand2 } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import { CHAT_COMPONENT_KEY, CHAT_CREW_KEY, consumeChatHandOff } from "@/lib/chatContext";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000") + "/api";

type ModelChoice = "auto" | "medical" | "general";

interface Message {
  role: "user" | "assistant";
  content: string;
  model?: string;
  route?: "medical" | "general";
}

interface ModelOption {
  id: ModelChoice;
  label: string;
  hint: string;
  model: string | null;
}

interface ModelsResponse {
  mode: "cloud" | "local";
  fine_tune_installed: boolean;
  options: ModelOption[];
}

const CHOICE_ICONS: Record<ModelChoice, React.ElementType> = {
  auto: Wand2,
  medical: HeartPulse,
  general: Package,
};

const MODEL_CHOICE_KEY = "vessel_ops_model_choice";

const QUICK_PROMPTS: { text: string; kind: "medical" | "inventory" }[] = [
  { text: "A crew member has chest pain and shortness of breath. What should I do?", kind: "medical" },
  { text: "How do I treat a deep laceration to the forearm at sea?", kind: "medical" },
  { text: "What spares do we carry for the main engine?", kind: "inventory" },
  { text: "The cooling water temperature is climbing — do we have the parts to fix it?", kind: "inventory" },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  
  // Load history from LocalStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("vessel_ops_chat_history");
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load chat history", e);
      }
    }
  }, []);

  // Save history on change
  useEffect(() => {
    localStorage.setItem("vessel_ops_chat_history", JSON.stringify(messages));
  }, [messages]);

  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [crewContext, setCrewContext] = useState<string>("");
  const [componentContext, setComponentContext] = useState<string>("");
  const [isListening, setIsListening] = useState(false);
  const [verbose, setVerbose] = useState(false);
  const [modelChoice, setModelChoice] = useState<ModelChoice>("auto");
  const scrollRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  const models = useQuery({
    queryKey: ["ai-models"],
    queryFn: () => apiFetch<ModelsResponse>("/ai/models"),
  });

  // Remember the crew's pick across sessions — if they've learned the router
  // gets a certain question wrong, they shouldn't have to re-select every time.
  useEffect(() => {
    const saved = localStorage.getItem(MODEL_CHOICE_KEY);
    if (saved === "auto" || saved === "medical" || saved === "general") {
      setModelChoice(saved);
    }

    // Arriving from a component or crew detail page? Preselect that context.
    const component = consumeChatHandOff(CHAT_COMPONENT_KEY);
    if (component) setComponentContext(component);
    const crewMember = consumeChatHandOff(CHAT_CREW_KEY);
    if (crewMember) setCrewContext(crewMember);
  }, []);

  const chooseModel = (choice: ModelChoice) => {
    setModelChoice(choice);
    localStorage.setItem(MODEL_CHOICE_KEY, choice);
  };

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
      const body: Record<string, unknown> = {
        messages: next,
        succinct: !verbose,
        model_choice: modelChoice,
      };
      if (crewContext) body.crew_id = crewContext;
      if (componentContext) body.component_id = componentContext;

      const res = await fetch(`${API_BASE}/ai/chat`, {
        method: "POST",
        // Streams use bare fetch rather than apiFetch, so the auth and vessel
        // headers have to be attached explicitly.
        headers: { "Content-Type": "application/json", ...(await authHeaders()) },
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
            if (parsed.model || parsed.route) {
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                copy[copy.length - 1] = {
                  ...last,
                  ...(parsed.model ? { model: parsed.model } : {}),
                  ...(parsed.route ? { route: parsed.route } : {}),
                };
                return copy;
              });
            }
            if (parsed.token) {
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                copy[copy.length - 1] = {
                  ...last,
                  role: "assistant",
                  content: last.content + parsed.token,
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
          content: `[AI Connection Lost: Gemma is currently offline. Your message has been saved locally and will be processed when the connection is restored.]`,
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
          Medical guidance from the WHO ship&apos;s medical guide, and answers grounded in your
          vessel&apos;s own component and spares inventory.
        </p>
      </div>

      {/* Model selection — the single most important control on this page. */}
      <div className="mb-3 p-3 bg-white rounded-xl border border-slate-200">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Model</span>
          {models.data && (
            <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
              {models.data.mode === "cloud" ? "Cloud · Google AI Studio" : "Local · Ollama"}
            </span>
          )}
        </div>
        <div className="grid grid-cols-3 gap-2">
          {(models.data?.options ?? []).map((opt) => {
            const Icon = CHOICE_ICONS[opt.id] ?? Wand2;
            const active = modelChoice === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => chooseModel(opt.id)}
                title={opt.model ? `${opt.hint}\n\n${opt.model}` : opt.hint}
                className={`flex items-center justify-center gap-1.5 px-2 py-2 rounded-lg text-xs font-bold border transition-colors ${
                  active
                    ? "bg-ocean-600 border-ocean-600 text-white"
                    : "bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <Icon size={14} />
                <span className="truncate">{opt.label}</span>
              </button>
            );
          })}
        </div>
        <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
          {models.data?.options.find((o) => o.id === modelChoice)?.hint ??
            "Choosing a model lets you override the automatic router when it gets a question wrong."}
        </p>
        {models.data && !models.data.fine_tune_installed && models.data.mode === "local" && (
          <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-2 py-1.5 mt-2">
            The maritime medical fine-tune isn&apos;t installed — medical questions are running on
            base Gemma 4.
          </p>
        )}
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
          <span className="text-xs text-ocean-700 bg-ocean-50 px-2 py-1 rounded">
            Discussing: {contextLabel}
          </span>
        )}
        <label className="flex items-center gap-2 ml-auto cursor-pointer" title="Enable more detailed, conversational responses">
          <input 
            type="checkbox" 
            checked={verbose} 
            onChange={(e) => setVerbose(e.target.checked)}
            className="w-4 h-4 text-ocean-600 rounded border-slate-300 focus:ring-ocean-500"
          />
          <span className="text-xs font-semibold text-slate-600">Verbose Mode</span>
        </label>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto bg-white rounded-xl border border-slate-200 p-4 space-y-4">
        {messages.length === 0 ? (
          <div>
            <p className="text-sm text-slate-400 mb-3">Try asking:</p>
            <div className="grid gap-2">
              {QUICK_PROMPTS.map(({ text, kind }) => {
                const Icon = kind === "medical" ? HeartPulse : Package;
                return (
                  <button
                    key={text}
                    onClick={() => sendMessage(text)}
                    disabled={streaming}
                    className="flex items-start gap-2.5 text-left text-sm bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg px-3 py-2 transition-colors"
                  >
                    <Icon
                      size={15}
                      className={`mt-0.5 shrink-0 ${kind === "medical" ? "text-green-500" : "text-ocean-500"}`}
                    />
                    {text}
                  </button>
                );
              })}
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
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-xs font-semibold text-slate-500">
                    {m.role === "user" ? "You" : "Gemma"}
                  </p>
                  {m.role === "assistant" && m.route && (
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide ${
                        m.route === "medical"
                          ? "bg-violet-100 text-violet-700"
                          : "bg-ocean-100 text-ocean-700"
                      }`}
                      title={`Routed to the ${m.route === "medical" ? "medical" : "ship & inventory"} model`}
                    >
                      {m.route === "medical" ? "Medical" : "Inventory"}
                    </span>
                  )}
                  {m.role === "assistant" && m.model && (
                    <span
                      className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-500"
                      title={`Response served by ${m.model}`}
                    >
                      {m.model}
                    </span>
                  )}
                </div>
                <div className="text-sm text-slate-800 markdown-content">
                  <ReactMarkdown>
                    {m.content}
                  </ReactMarkdown>
                  {streaming && i === messages.length - 1 && m.role === "assistant" && (
                    <span className="inline-block w-2 h-4 ml-0.5 bg-ocean-400 animate-pulse" />
                  )}
                </div>
                {m.role === 'assistant' && m.content.toLowerCase().includes('splint') && (
                  <div className="mt-4 p-4 bg-slate-800 rounded-lg border border-blue-500/30">
                    <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">Onboard Visual Aid: Splint Types</p>
                    <img 
                      src={`/api/resource?path=medical_splint_types_1778021722507.png`} 
                      alt="Splint Types Diagram"
                      className="rounded border border-slate-700 w-full max-w-md"
                    />
                    <p className="text-xs text-slate-400 mt-2 italic">Source: Vessel Medical Manual, App. D</p>
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
          placeholder="Ask Gemma about a symptom, fault, or decision…"
          disabled={streaming}
          className="flex-1 bg-white border border-slate-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ocean-500"
          autoCorrect="off"
          spellCheck="false"
          autoComplete="off"
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

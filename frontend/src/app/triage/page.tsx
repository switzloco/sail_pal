"use client";

import { useEffect, useRef, useState } from "react";
import {
  Stethoscope,
  ListChecks,
  User,
  BookOpen,
  ShieldCheck,
  ShieldAlert,
  RotateCcw,
  Save,
  Play,
  Bot,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { apiFetch } from "@/lib/api";
import { CrewMember } from "@/lib/types";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000") + "/api";

const SEVERITIES = ["minor", "moderate", "serious", "critical"] as const;
type Severity = (typeof SEVERITIES)[number];

interface PlanStep {
  tool: string;
  label: string;
}

interface ProtocolSource {
  source: string;
  page: string | number;
}

interface EvalVerdict {
  label: string;
  score: number;
  explanation: string;
  passed: boolean;
}

export default function TriagePage() {
  const [crew, setCrew] = useState<CrewMember[]>([]);
  const [crewId, setCrewId] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [severity, setSeverity] = useState<Severity>("moderate");
  const [autoLog, setAutoLog] = useState(true);
  const [running, setRunning] = useState(false);

  // Agent trace state
  const [plan, setPlan] = useState<PlanStep[]>([]);
  const [patient, setPatient] = useState<string | null>(null);
  const [sources, setSources] = useState<ProtocolSource[]>([]);
  const [guidance, setGuidance] = useState("");
  const [verdict, setVerdict] = useState<EvalVerdict | null>(null);
  const [regenerated, setRegenerated] = useState(false);
  const [eventId, setEventId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const guidanceRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch<CrewMember[]>("/crew")
      .then((list) => {
        setCrew(list);
        if (list.length > 0) setCrewId(list[0].crew_id);
      })
      .catch(() => setCrew([]));
  }, []);

  useEffect(() => {
    guidanceRef.current?.scrollTo({ top: guidanceRef.current.scrollHeight });
  }, [guidance]);

  function reset() {
    setPlan([]);
    setPatient(null);
    setSources([]);
    setGuidance("");
    setVerdict(null);
    setRegenerated(false);
    setEventId(null);
    setError(null);
  }

  async function runAgent() {
    if (!crewId || !symptoms.trim() || running) return;
    reset();
    setRunning(true);

    const symptomList = symptoms
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      const res = await fetch(`${API_BASE}/ai/medical-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          crew_id: crewId,
          symptoms: symptomList,
          severity,
          auto_log: autoLog,
          succinct: true,
        }),
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
          try {
            const p = JSON.parse(line.slice(5).trim());
            handleEvent(p);
          } catch {
            /* ignore partial frames */
          }
        }
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRunning(false);
    }
  }

  function handleEvent(p: Record<string, unknown>) {
    switch (p.type) {
      case "plan":
        setPlan((p.steps as PlanStep[]) ?? []);
        break;
      case "tool_result":
        if (p.tool === "lookup_crew_member") setPatient(p.summary as string);
        if (p.tool === "retrieve_protocol") setSources((p.sources as ProtocolSource[]) ?? []);
        if (p.tool === "log_health_event") setEventId(p.event_id as string);
        break;
      case "assess_start":
        if (p.attempt === 2) setRegenerated(true);
        setGuidance("");
        break;
      case "token":
        setGuidance((g) => g + (p.token as string));
        break;
      case "eval":
        setVerdict({
          label: p.label as string,
          score: p.score as number,
          explanation: p.explanation as string,
          passed: p.passed as boolean,
        });
        break;
      case "error":
        setError(p.message as string);
        break;
      default:
        break;
    }
  }

  return (
    <div className="max-w-6xl mx-auto py-2">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <div className="w-14 h-14 bg-gradient-to-tr from-rose-500 to-rose-700 rounded-2xl flex items-center justify-center text-white shadow-lg">
          <Stethoscope size={28} />
        </div>
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900">Medical Triage Agent</h1>
          <p className="text-sm text-slate-500">
            Plans &amp; executes a full triage mission &mdash; every step traced to Arize.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input panel */}
        <div className="lg:col-span-1 bg-white rounded-3xl border border-slate-200 shadow-sm p-6 space-y-5 h-fit">
          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Patient</label>
            <select
              value={crewId}
              onChange={(e) => setCrewId(e.target.value)}
              disabled={running}
              className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-4 focus:ring-rose-500/10 focus:border-rose-500"
            >
              {crew.length === 0 && <option value="">No crew on file</option>}
              {crew.map((c) => (
                <option key={c.crew_id} value={c.crew_id}>
                  {c.full_name} — {c.role}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Symptoms</label>
            <textarea
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              disabled={running}
              rows={3}
              placeholder="e.g. fever, abdominal pain, vomiting"
              className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-4 focus:ring-rose-500/10 focus:border-rose-500"
            />
            <p className="text-[11px] text-slate-400 mt-1">Comma-separated.</p>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Severity</label>
            <div className="mt-1 grid grid-cols-4 gap-2">
              {SEVERITIES.map((s) => (
                <button
                  key={s}
                  onClick={() => setSeverity(s)}
                  disabled={running}
                  className={`text-[11px] font-bold uppercase py-2 rounded-lg transition-all ${
                    severity === s
                      ? "bg-rose-600 text-white shadow"
                      : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={autoLog}
              onChange={(e) => setAutoLog(e.target.checked)}
              disabled={running}
              className="w-4 h-4 accent-rose-600"
            />
            Log result to health record
          </label>

          <button
            onClick={runAgent}
            disabled={running || !crewId || !symptoms.trim()}
            className="w-full bg-rose-600 hover:bg-rose-700 disabled:bg-slate-200 text-white py-3.5 rounded-2xl flex items-center justify-center gap-2 font-bold transition-all shadow-lg active:scale-95"
          >
            <Play size={18} />
            {running ? "Agent running…" : "Run Triage Agent"}
          </button>

          {error && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl p-3">{error}</p>
          )}
        </div>

        {/* Trace panel */}
        <div className="lg:col-span-2 space-y-4">
          {/* Plan */}
          {plan.length > 0 && (
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <ListChecks size={18} className="text-rose-600" />
                <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Agent Plan</h3>
              </div>
              <div className="space-y-2">
                {plan.map((step, i) => (
                  <div key={step.tool} className="flex items-center gap-3 text-sm">
                    <span className="w-6 h-6 shrink-0 rounded-full bg-rose-100 text-rose-700 text-[11px] font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="text-slate-700">{step.label}</span>
                    <code className="ml-auto text-[10px] text-slate-400">{step.tool}</code>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Patient + sources */}
          {(patient || sources.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {patient && (
                <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <User size={16} className="text-slate-500" />
                    <h3 className="text-[11px] font-black text-slate-500 uppercase tracking-widest">Patient Record</h3>
                  </div>
                  <p className="text-sm font-semibold text-slate-800">{patient}</p>
                </div>
              )}
              {sources.length > 0 && (
                <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <BookOpen size={16} className="text-slate-500" />
                    <h3 className="text-[11px] font-black text-slate-500 uppercase tracking-widest">
                      Retrieved Protocols ({sources.length})
                    </h3>
                  </div>
                  <ul className="space-y-1">
                    {sources.map((s, i) => (
                      <li key={i} className="text-xs text-slate-600">
                        {s.source} — p. {s.page}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Guidance */}
          {(guidance || running) && (
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Bot size={18} className="text-rose-600" />
                <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Assessment</h3>
                {regenerated && (
                  <span className="ml-auto flex items-center gap-1 text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
                    <RotateCcw size={12} /> Regenerated after guardrail
                  </span>
                )}
              </div>
              <div
                ref={guidanceRef}
                className="prose prose-sm prose-slate max-w-none max-h-[40vh] overflow-y-auto"
              >
                <ReactMarkdown>{guidance || "_Thinking…_"}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Eval verdict */}
          {verdict && (
            <div
              className={`rounded-3xl border shadow-sm p-6 ${
                verdict.passed
                  ? "bg-green-50 border-green-200"
                  : "bg-red-50 border-red-200"
              }`}
            >
              <div className="flex items-center gap-3">
                {verdict.passed ? (
                  <ShieldCheck size={22} className="text-green-600" />
                ) : (
                  <ShieldAlert size={22} className="text-red-600" />
                )}
                <div>
                  <h3 className="text-sm font-black text-slate-800">
                    Arize Groundedness Check: {verdict.label}{" "}
                    <span className="tabular-nums">({(verdict.score * 100).toFixed(0)}%)</span>
                  </h3>
                  <p className="text-xs text-slate-600 mt-0.5">{verdict.explanation}</p>
                </div>
              </div>
            </div>
          )}

          {/* Logged */}
          {eventId && (
            <div className="bg-slate-900 text-white rounded-3xl p-5 flex items-center gap-3">
              <Save size={18} className="text-green-400" />
              <p className="text-sm">
                Logged to health record{" "}
                <code className="text-[11px] text-slate-400">{eventId}</code>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

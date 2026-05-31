"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  Bot,
  Anchor,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Send,
  Wrench,
} from "lucide-react";

type EvalLabel = "pass" | "warning" | "fail";

interface Trace {
  id: string;
  vessel_id: string;
  component_name: string;
  diagnosis: string;
  model_name: string;
  recorded_at: string | null;
  upload_status: string;
  phoenix_trace_id: string | null;
}

interface Evaluation {
  id: string;
  trace_id: string;
  evaluation_type: string;
  score: number;
  label: EvalLabel;
  explanation: string;
  flagged: boolean;
  evaluated_at: string | null;
}

interface Patch {
  id: string;
  trace_id: string;
  patch_type: string;
  original_prompt_section: string;
  patched_prompt_section: string;
  rationale: string;
  agent_reasoning: string;
  status: string;
  created_at: string | null;
}

interface SyncReport {
  sync_id: string;
  traces_ingested: number;
  evaluations_run: number;
  patches_generated: number;
  flagged_count: number;
  summary: string;
}

function LabelBadge({ label }: { label: EvalLabel }) {
  if (label === "pass")
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
        <CheckCircle size={11} /> Pass
      </span>
    );
  if (label === "warning")
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
        <AlertTriangle size={11} /> Warning
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-700 bg-red-50 border border-red-200 rounded-full px-2 py-0.5">
      <XCircle size={11} /> Fail
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: "bg-amber-50 text-amber-700 border-amber-200",
    approved: "bg-blue-50 text-blue-700 border-blue-200",
    deployed: "bg-green-50 text-green-700 border-green-200",
    rejected: "bg-slate-50 text-slate-500 border-slate-200",
  };
  return (
    <span
      className={`inline-block text-xs font-semibold border rounded-full px-2 py-0.5 ${map[status] ?? map["pending"]}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.7 ? "bg-green-500" : score >= 0.4 ? "bg-amber-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500 w-8 text-right">{pct}%</span>
    </div>
  );
}

function PatchCard({ patch, onStatusChange }: { patch: Patch; onStatusChange: (id: string, status: string) => void }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Wrench size={14} className="text-slate-400" />
            <span className="text-xs font-mono text-slate-500">{patch.patch_type}</span>
            <StatusBadge status={patch.status} />
          </div>
          <p className="text-sm text-slate-700 font-medium">{patch.rationale}</p>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-slate-400 hover:text-slate-600 p-1"
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {expanded && (
        <div className="space-y-3 pt-2 border-t border-slate-100">
          {patch.original_prompt_section && patch.original_prompt_section !== "N/A — missing instruction" && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Original</p>
              <pre className="text-xs bg-red-50 border border-red-100 rounded p-2 whitespace-pre-wrap text-red-800 font-mono">
                {patch.original_prompt_section}
              </pre>
            </div>
          )}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Patch</p>
            <pre className="text-xs bg-green-50 border border-green-100 rounded p-2 whitespace-pre-wrap text-green-800 font-mono">
              {patch.patched_prompt_section}
            </pre>
          </div>
          {patch.agent_reasoning && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Fleet Mechanic reasoning</p>
              <p className="text-xs text-slate-600 leading-relaxed">{patch.agent_reasoning}</p>
            </div>
          )}
          {patch.status === "pending" && (
            <div className="flex gap-2">
              <button
                onClick={() => onStatusChange(patch.id, "approved")}
                className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 font-medium"
              >
                Approve &amp; Queue to Vessel
              </button>
              <button
                onClick={() => onStatusChange(patch.id, "rejected")}
                className="text-xs bg-slate-100 text-slate-600 px-3 py-1.5 rounded-lg hover:bg-slate-200 font-medium"
              >
                Reject
              </button>
            </div>
          )}
          {patch.status === "approved" && (
            <button
              onClick={() => onStatusChange(patch.id, "deployed")}
              className="text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700 font-medium"
            >
              Mark Deployed to Vessel
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function FleetMechanicPage() {
  const qc = useQueryClient();
  const [lastReport, setLastReport] = useState<SyncReport | null>(null);
  const [syncing, setSyncing] = useState(false);

  const { data: traces = [] } = useQuery<Trace[]>({
    queryKey: ["fm-traces"],
    queryFn: () => apiFetch("/fleet-mechanic/traces"),
  });

  const { data: patches = [] } = useQuery<Patch[]>({
    queryKey: ["fm-patches"],
    queryFn: () => apiFetch("/fleet-mechanic/patches"),
  });

  const { data: evaluations = [] } = useQuery<Evaluation[]>({
    queryKey: ["fm-evaluations"],
    queryFn: () => apiFetch("/fleet-mechanic/evaluations"),
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/fleet-mechanic/patches/${id}/status?status=${status}`, {
        method: "PATCH",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fm-patches"] }),
  });

  async function runDemoSync() {
    setSyncing(true);
    try {
      const report = await apiFetch<SyncReport>(
        "/fleet-mechanic/demo-sync?inject_hallucination=true",
        { method: "POST" }
      );
      setLastReport(report);
      qc.invalidateQueries({ queryKey: ["fm-traces"] });
      qc.invalidateQueries({ queryKey: ["fm-evaluations"] });
      qc.invalidateQueries({ queryKey: ["fm-patches"] });
    } finally {
      setSyncing(false);
    }
  }

  const pendingPatches = patches.filter((p) => p.status === "pending");
  const flaggedEvals = evaluations.filter((e) => e.flagged);

  return (
    <div className="max-w-4xl space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="bg-indigo-600 p-2 rounded-lg">
              <Bot size={20} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Fleet Mechanic</h1>
          </div>
          <p className="text-sm text-slate-500 ml-12">
            Gemini evaluates offline Gemma traces via Arize Phoenix and drafts prompt patches
          </p>
        </div>
        <button
          onClick={runDemoSync}
          disabled={syncing}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-60"
        >
          {syncing ? <Loader2 size={15} className="animate-spin" /> : <Anchor size={15} />}
          {syncing ? "Syncing..." : "Simulate Marina Sync"}
        </button>
      </div>

      {/* Last sync report banner */}
      {lastReport && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className="text-indigo-600" />
            <span className="text-sm font-semibold text-indigo-800">Marina sync complete</span>
          </div>
          <p className="text-sm text-indigo-700">{lastReport.summary}</p>
          <div className="flex gap-6 text-xs text-indigo-600 font-medium">
            <span>{lastReport.traces_ingested} traces ingested</span>
            <span>{lastReport.evaluations_run} evaluations run</span>
            <span>{lastReport.patches_generated} patches drafted</span>
            {lastReport.flagged_count > 0 && (
              <span className="text-amber-600">{lastReport.flagged_count} flagged</span>
            )}
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Traces uploaded", value: traces.length, color: "text-slate-800" },
          { label: "Evaluations run", value: evaluations.length, color: "text-slate-800" },
          {
            label: "Patches pending",
            value: pendingPatches.length,
            color: pendingPatches.length > 0 ? "text-amber-600" : "text-slate-800",
          },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-4 text-center">
            <p className={`text-3xl font-bold ${color}`}>{value}</p>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Architecture callout */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-3">How it works</p>
        <div className="flex flex-wrap gap-2 items-center text-xs text-slate-600">
          {[
            "Gemma (Raspberry Pi, offline)",
            "→ Engine sensor traces",
            "→ Marina sync upload",
            "→ Arize Phoenix ingestion",
            "→ Gemini hallucination eval",
            "→ Gemini correctness eval",
            "→ Prompt patch drafted",
            "→ Push back to vessel",
          ].map((step) => (
            <span
              key={step}
              className={
                step.startsWith("→")
                  ? "text-slate-400"
                  : "bg-white border border-slate-200 rounded px-2 py-1 font-medium"
              }
            >
              {step}
            </span>
          ))}
        </div>
      </div>

      {/* Flagged evaluations */}
      {flaggedEvals.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-slate-800 mb-3">
            Flagged evaluations
            <span className="ml-2 text-xs font-normal text-slate-400">({flaggedEvals.length})</span>
          </h2>
          <div className="space-y-2">
            {flaggedEvals.map((e) => (
              <div
                key={e.id}
                className="bg-white rounded-xl border border-amber-200 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1.5">
                      <LabelBadge label={e.label} />
                      <span className="text-xs text-slate-500 font-mono">{e.evaluation_type}</span>
                    </div>
                    <ScoreBar score={e.score} />
                    <p className="text-sm text-slate-600 mt-2">{e.explanation}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending patches */}
      {pendingPatches.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-slate-800 mb-3">
            Prompt patches awaiting review
            <span className="ml-2 text-xs font-normal text-slate-400">
              — approve to queue for next vessel departure
            </span>
          </h2>
          <div className="space-y-3">
            {pendingPatches.map((p) => (
              <PatchCard
                key={p.id}
                patch={p}
                onStatusChange={(id, status) => patchMutation.mutate({ id, status })}
              />
            ))}
          </div>
        </div>
      )}

      {/* Trace list */}
      <div>
        <h2 className="text-base font-semibold text-slate-800 mb-3">
          Uploaded traces
          <span className="ml-2 text-xs font-normal text-slate-400">({traces.length})</span>
        </h2>
        {traces.length === 0 && (
          <div className="text-center py-12 text-slate-400 bg-white rounded-xl border border-slate-200">
            <Bot size={32} className="mx-auto mb-2 opacity-40" />
            <p className="text-sm">No traces yet. Click &ldquo;Simulate Marina Sync&rdquo; to run a demo.</p>
          </div>
        )}
        <div className="space-y-2">
          {traces.map((t) => (
            <div
              key={t.id}
              className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{t.component_name}</p>
                <p className="text-xs text-slate-500 truncate">{t.diagnosis}</p>
              </div>
              <div className="text-right shrink-0">
                <span
                  className={`inline-block text-xs font-semibold rounded-full px-2 py-0.5 border ${
                    t.upload_status === "evaluated"
                      ? "bg-green-50 text-green-700 border-green-200"
                      : t.upload_status === "uploaded"
                      ? "bg-blue-50 text-blue-700 border-blue-200"
                      : "bg-slate-50 text-slate-500 border-slate-200"
                  }`}
                >
                  {t.upload_status}
                </span>
                <p className="text-[10px] text-slate-400 mt-0.5 font-mono">{t.model_name}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

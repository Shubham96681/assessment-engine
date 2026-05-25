"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileSearch, Bot, ListChecks } from "lucide-react";

type LogStep = {
  step?: number | string;
  attempt?: number;
  question_type?: string;
  difficulty?: string;
  bloom_level?: string;
  count_requested?: number;
  rag_query?: string;
  rag_chunks?: { page_num?: number; score?: number; text_preview?: string }[];
  llm_prompt?: string;
  llm_response?: string;
  questions_parsed?: number;
  question_previews?: string[];
  llm_mode?: string;
  llm_note?: string;
  error?: string;
  agent?: string;
  source?: string;
  questions_applied?: number;
  total_marks?: number;
  note?: string;
};

function isLlmGenerationStep(entry: LogStep): boolean {
  return (
    typeof entry.step === "number" &&
    !!entry.question_type &&
    typeof entry.questions_parsed === "number"
  );
}

function isAppliedRagStep(entry: LogStep): boolean {
  return entry.step === "applied_rag";
}

export default function GenerationTrace({ log }: { log: LogStep[] }) {
  const applied = log?.find(isAppliedRagStep);
  const llmSteps = (log || []).filter(isLlmGenerationStep);
  const [showIntermediate, setShowIntermediate] = useState(!applied);
  const [openStep, setOpenStep] = useState<number | string | null>(
    applied ? "applied_rag" : llmSteps.length ? llmSteps[0].step ?? 0 : null,
  );

  if (!log?.length) {
    return (
      <p className="text-sm text-slate-500">
        No generation trace yet. Generate a new assessment to capture RAG prompts and LLM output.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {applied && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
          <p className="font-medium text-emerald-300 mb-1">
            Final paper: applied from rag_response.txt ({applied.questions_applied ?? "?"} questions
            {applied.total_marks != null ? `, ${applied.total_marks} marks` : ""})
          </p>
          <p className="text-emerald-100/90 text-xs leading-relaxed">{applied.note}</p>
          <p className="text-emerald-200/70 text-xs mt-2">
            The question list below is authoritative. RAG trace steps are intermediate attempts only.
          </p>
        </div>
      )}

      {!applied && llmSteps.length > 0 && (
        <p className="text-xs text-slate-400">
          Intermediate RAG/LLM attempts during generation. Saved questions below are the final paper.
        </p>
      )}

      {applied && (
        <AppliedRagPanel entry={applied} isOpen={openStep === "applied_rag"} onToggle={() => setOpenStep(openStep === "applied_rag" ? null : "applied_rag")} />
      )}

      {applied && llmSteps.length > 0 && (
        <button
          type="button"
          onClick={() => setShowIntermediate((v) => !v)}
          className="text-xs text-slate-400 hover:text-indigo-300 underline"
        >
          {showIntermediate
            ? "Hide failed auto-generation attempts (not the final paper)"
            : `Show ${llmSteps.length} intermediate auto-generation attempt(s)`}
        </button>
      )}

      {(!applied || showIntermediate) &&
        llmSteps.map((entry, idx) => {
        const stepKey = `llm-${entry.step}-${entry.attempt ?? idx}`;
        const isOpen = openStep === stepKey;
        const attemptLabel =
          entry.attempt != null && entry.attempt > 1 ? ` · attempt ${entry.attempt}` : "";
        return (
          <div
            key={stepKey}
            className="border border-[#334155] rounded-xl overflow-hidden bg-[#0f172a]/60"
          >
            <button
              type="button"
              onClick={() => setOpenStep(isOpen ? null : stepKey)}
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[#1e293b]/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                {isOpen ? (
                  <ChevronDown className="w-4 h-4 text-indigo-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                )}
                <span className="text-sm font-medium text-white">
                  RAG step {entry.step}
                  {attemptLabel}: {entry.question_type} · {entry.difficulty} · {entry.bloom_level}
                </span>
              </div>
              <span className="flex items-center gap-2 text-xs text-slate-400">
                {entry.llm_mode === "rag_file_agent" && (
                  <span className="px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
                    RAG file agent
                  </span>
                )}
                {entry.llm_mode === "ollama" && (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Ollama AI
                  </span>
                )}
                {entry.llm_mode === "local" && (
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Local prompt builder
                  </span>
                )}
                parsed {entry.questions_parsed} / {entry.count_requested}
              </span>
            </button>

            {isOpen && <StepBody entry={entry} />}
          </div>
        );
      })}

      {llmSteps.length === 0 && !applied && (
        <p className="text-sm text-slate-500">
          No LLM prompt steps in this log (agents/dedup only). Use the question list below.
        </p>
      )}
    </div>
  );
}

function AppliedRagPanel({
  entry,
  isOpen,
  onToggle,
}: {
  entry: LogStep;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border border-emerald-500/30 rounded-xl overflow-hidden bg-[#0f172a]/60">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-emerald-500/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-emerald-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-emerald-400" />
          )}
          <span className="text-sm font-medium text-emerald-200">Applied rag_response.txt (final)</span>
        </div>
        <span className="text-xs text-emerald-300/80">
          {entry.questions_applied ?? "?"} questions saved
        </span>
      </button>
      {isOpen && entry.note && (
        <div className="px-4 pb-4 border-t border-emerald-500/20 text-sm text-slate-300">{entry.note}</div>
      )}
    </div>
  );
}

function StepBody({ entry }: { entry: LogStep }) {
  return (
    <div className="px-4 pb-4 space-y-4 border-t border-[#334155]">
      {entry.llm_note && (
        <p className="text-sm text-amber-300/90 pt-3 border-l-2 border-amber-500/50 pl-3">{entry.llm_note}</p>
      )}
      {entry.error && <p className="text-sm text-rose-400">{entry.error}</p>}

      <TraceBlock
        icon={<FileSearch className="w-4 h-4 text-teal-400" />}
        title="RAG retrieval query"
        content={entry.rag_query || ""}
      />

      {entry.rag_chunks && entry.rag_chunks.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">
            Retrieved PDF chunks ({entry.rag_chunks.length})
          </h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {entry.rag_chunks.map((chunk, i) => (
              <div
                key={i}
                className="text-xs text-slate-300 bg-[#1e293b] border border-[#334155] rounded-lg p-3"
              >
                <span className="text-indigo-400 font-medium">
                  Page {chunk.page_num ?? "?"}
                  {chunk.score != null ? ` · score ${chunk.score}` : ""}
                </span>
                <p className="mt-1 whitespace-pre-wrap">{chunk.text_preview}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <TraceBlock
        icon={<Bot className="w-4 h-4 text-indigo-400" />}
        title="LLM prompt (RAG context + instructions)"
        content={entry.llm_prompt || ""}
        maxHeight="max-h-64"
      />

      <TraceBlock
        icon={<ListChecks className="w-4 h-4 text-pink-400" />}
        title="LLM raw response"
        content={entry.llm_response || ""}
        maxHeight="max-h-64"
      />

      {entry.question_previews && entry.question_previews.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-emerald-400 uppercase mb-2">Questions parsed from this step</h4>
          <ol className="list-decimal list-inside space-y-1 text-sm text-slate-300">
            {entry.question_previews.map((preview, i) => (
              <li key={i}>{preview}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function TraceBlock({
  icon,
  title,
  content,
  maxHeight = "max-h-48",
}: {
  icon: React.ReactNode;
  title: string;
  content: string;
  maxHeight?: string;
}) {
  if (!content) return null;
  return (
    <div>
      <h4 className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase mb-2">
        {icon}
        {title}
      </h4>
      <pre
        className={`text-xs text-slate-300 bg-[#1e293b] border border-[#334155] rounded-lg p-3 overflow-auto whitespace-pre-wrap ${maxHeight}`}
      >
        {content}
      </pre>
    </div>
  );
}

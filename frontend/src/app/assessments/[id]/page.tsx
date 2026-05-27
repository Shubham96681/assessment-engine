"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getAssessment,
  getAssessmentStatus,
  submitFeedback,
  getApiBaseUrl,
  applyRagResponse,
  regenerateExport,
  getRagPending,
  formatApiError,
} from "@/lib/api";
import { useParams } from "next/navigation";
import { Download, ArrowLeft, Star, FileCheck, HelpCircle, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import GenerationTrace from "@/components/GenerationTrace";
import { AnswerContent, QuestionContent } from "@/lib/questionText";

function isAxiosTimeout(err: unknown): boolean {
  return (
    !!err &&
    typeof err === "object" &&
    ("code" in err && (err as { code?: string }).code === "ECONNABORTED")
  );
}

function is404(err: unknown): boolean {
  return (
    !!err &&
    typeof err === "object" &&
    "response" in err &&
    (err as { response?: { status?: number } }).response?.status === 404
  );
}

/** Changes when questions are replaced so PDFs/figures bypass browser cache. */
function exportCacheKey(assessment: { questions?: { id?: string }[] } | null): string {
  const ids = (assessment?.questions ?? []).map((q) => q.id).filter(Boolean).join(",");
  return ids || "0";
}

function ExportActions({
  assessment,
  cacheKey,
  exportingPdf,
  onRegenerateExport,
  variant = "inline",
}: {
  assessment: {
    pdf_url?: string | null;
    answer_key_url?: string | null;
    questions?: unknown[];
    status?: string;
  };
  cacheKey: string;
  exportingPdf: boolean;
  onRegenerateExport: () => void;
  variant?: "inline" | "card";
}) {
  const base = getApiBaseUrl();
  const hasQuestions = (assessment.questions?.length ?? 0) > 0;
  const canBuildPdf = hasQuestions && assessment.status !== "generating";
  if (!canBuildPdf && !assessment.pdf_url && !assessment.answer_key_url) {
    return null;
  }

  const btn =
    variant === "card"
      ? "flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all"
      : "flex-1 md:flex-none flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl font-medium transition-all";

  const controls = (
    <>
      {assessment.pdf_url ? (
        <a
          href={`${base}${assessment.pdf_url}?v=${cacheKey}`}
          target="_blank"
          rel="noopener noreferrer"
          download
          className={`${btn} bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20`}
        >
          <Download className="w-4 h-4" /> Question Paper
        </a>
      ) : canBuildPdf ? (
        <button
          type="button"
          onClick={onRegenerateExport}
          disabled={exportingPdf}
          className={`${btn} bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white shadow-lg shadow-indigo-500/20`}
        >
          <Download className="w-4 h-4" />
          {exportingPdf ? "Creating PDF…" : "Create PDF download"}
        </button>
      ) : null}
      {assessment.answer_key_url && (
        <a
          href={`${base}${assessment.answer_key_url}?v=${cacheKey}`}
          target="_blank"
          rel="noopener noreferrer"
          download
          className={`${btn} bg-[#1e293b] hover:bg-indigo-500/20 border border-[#334155] hover:border-indigo-500/30 text-white`}
        >
          <FileCheck className="w-4 h-4" /> Answer Key
        </a>
      )}
    </>
  );

  if (variant === "card") {
    return (
      <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white">Download question paper</h2>
          <p className="text-sm text-slate-400">
            {assessment.pdf_url
              ? "PDF ready — open or save to your device."
              : "Create PDFs from the generated questions below."}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">{controls}</div>
      </div>
    );
  }

  return <div className="flex flex-wrap gap-3 w-full md:w-auto">{controls}</div>;
}

export default function AssessmentDetails() {
  const params = useParams();
  const id = params.id as string;
  const [assessment, setAssessment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [pollNote, setPollNote] = useState("");
  const [notFoundConfirmed, setNotFoundConfirmed] = useState(false);
  const [applyingRag, setApplyingRag] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [ragPending, setRagPending] = useState(false);
  const [regenSlot, setRegenSlot] = useState<number | null>(null);
  const [awaitingRegenApply, setAwaitingRegenApply] = useState(false);

  const loadFullAssessment = useCallback(async () => {
    const data = await getAssessment(id);
    setAssessment(data);
    setLoading(false);
    setPollNote("");
  }, [id]);

  useEffect(() => {
    if (!id) return;
    setAssessment(null);
    setLoading(true);
    setNotFoundConfirmed(false);
    setPollNote("");
    setRagPending(false);
    let cancelled = false;
    let notFoundRetries = 0;
    let autoApplyDone = false;

    const tryAutoApplyRag = async (rag: {
      pending?: boolean;
      ready_for_apply?: boolean;
    }) => {
      if (autoApplyDone) return false;
      if (rag.pending || !rag.ready_for_apply) return false;
      autoApplyDone = true;
      setApplyingRag(true);
      try {
        const applied = await applyRagResponse(id, true);
        setAssessment(applied);
        setLoading(false);
        setPollNote("");
        setAwaitingRegenApply(false);
        return applied?.status === "ready";
      } catch {
        autoApplyDone = false;
        return false;
      } finally {
        setApplyingRag(false);
      }
    };

    const poll = async () => {
      if (cancelled) return;
      try {
        const status = await getAssessmentStatus(id);
        if (cancelled) return;

        if (status.status === "generating") {
          setAssessment((prev: any) => ({
            ...(prev?.id === status.id ? prev : {}),
            id: status.id,
            title: status.title,
            status: "generating",
            total_marks: status.total_marks,
            questions: prev?.id === status.id ? prev?.questions || [] : [],
          }));
          setLoading(true);
          setNotFoundConfirmed(false);
          try {
            const rag = await getRagPending();
            setRagPending(!!rag.pending);
            setRegenSlot(rag.regen_slot ?? null);
            if (rag.regen_slot) setAwaitingRegenApply(true);
            if (await tryAutoApplyRag(rag)) return;
            setPollNote(
              rag.pending
                ? "Waiting for Cursor capture — say go capture in Agent chat; this page updates automatically."
                : rag.ready_for_apply
                  ? "Applying your paper automatically…"
                  : "Generation in progress. This page will update automatically."
            );
          } catch {
            setPollNote(
              "Generation in progress (RAG may take up to 5 minutes). This page will update automatically."
            );
          }
          window.setTimeout(poll, 3000);
          return;
        }

        setAssessment((prev: any) =>
          prev?.id === status.id
            ? {
                ...prev,
                status: status.status,
                title: status.title ?? prev.title,
                total_marks: status.total_marks ?? prev.total_marks,
                pdf_url: status.pdf_url ?? prev.pdf_url,
                answer_key_url: status.answer_key_url ?? prev.answer_key_url,
              }
            : prev
        );

        const full = await getAssessment(id);
        if (cancelled) return;
        setAssessment({
          ...full,
          pdf_url: full.pdf_url || status.pdf_url,
          answer_key_url: full.answer_key_url || status.answer_key_url,
          total_marks: full.total_marks ?? status.total_marks,
        });

        if (full.status === "failed" && !(full.questions && full.questions.length > 0)) {
          try {
            const rag = await getRagPending();
            setRagPending(!!rag.pending);
            if (await tryAutoApplyRag(rag)) return;
          } catch {
            /* ignore */
          }
          setLoading(false);
          setPollNote("");
          return;
        }

        setLoading(false);
        setPollNote("");
        try {
          const rag = await getRagPending();
          setRagPending(!!rag.pending);
          setRegenSlot(rag.regen_slot ?? null);
          if (rag.regen_slot) setAwaitingRegenApply(true);
          if (
            awaitingRegenApply &&
            rag.regen_slot &&
            !rag.pending &&
            full.status === "ready"
          ) {
            setAwaitingRegenApply(false);
            const applied = await applyRagResponse(id, true);
            setAssessment(applied);
          } else if (full.status === "ready" && (rag.pending || awaitingRegenApply)) {
            window.setTimeout(poll, 3000);
          }
        } catch {
          /* ignore */
        }
      } catch (err) {
        if (cancelled) return;
        console.error(err);

        if (is404(err) && notFoundRetries < 20) {
          notFoundRetries += 1;
          setPollNote("Waiting for assessment to be saved…");
          window.setTimeout(poll, 500);
          return;
        }

        if (is404(err)) {
          setNotFoundConfirmed(true);
          setLoading(false);
          return;
        }

        if (isAxiosTimeout(err)) {
          setPollNote(
            "Request timed out — backend may still be generating. Retrying…"
          );
          window.setTimeout(poll, 4000);
          return;
        }

        setPollNote(formatApiError(err));
        window.setTimeout(poll, 5000);
      }
    };

    poll();
    return () => {
      cancelled = true;
    };
  }, [id, loadFullAssessment, awaitingRegenApply]);

  const handleApplyRagResponse = async () => {
    setApplyingRag(true);
    try {
      const data = await applyRagResponse(id, true);
      if (data?.questions?.length) {
        setAssessment(data);
      } else {
        await loadFullAssessment();
      }
      setLoading(false);
      setPollNote("");
      setAwaitingRegenApply(false);
    } catch (e: unknown) {
      const msg =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      alert(msg || "Could not apply rag_response.txt. Ensure the file exists at project root.");
    } finally {
      setApplyingRag(false);
    }
  };

  const handleRegenerateExport = async () => {
    setExportingPdf(true);
    try {
      const data = await regenerateExport(id);
      setAssessment(data);
    } catch (e: unknown) {
      alert(formatApiError(e) || "Could not create PDF. Check backend logs.");
    } finally {
      setExportingPdf(false);
    }
  };

  if (loading || (assessment && assessment.status === "generating")) {
    return (
      <div className="flex flex-col h-[80vh] items-center justify-center space-y-6 px-4">
        <div className="relative w-24 h-24">
          <div className="absolute inset-0 border-4 border-indigo-500/20 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <div className="text-center max-w-lg">
          <h2 className="text-2xl font-bold text-white mb-2">Generating Assessment</h2>
          {assessment?.title && (
            <p className="text-slate-300 text-sm mb-2">{assessment.title}</p>
          )}
          <p className="text-slate-400 mb-2">
            {ragPending ? (
              <>
                <strong className="text-amber-200">Say go capture</strong> in Cursor Agent for this repo
                (Hooks enabled). The agent writes <code className="text-indigo-300">rag_response.txt</code>;
                verification and apply run automatically — no extra clicks.
              </>
            ) : (
              <>
                Applying or finishing your paper automatically when{" "}
                <code className="text-indigo-300">rag_response.txt</code> is valid.
              </>
            )}
          </p>
          {pollNote && (
            <p className="text-amber-200/90 text-sm mb-4">{pollNote}</p>
          )}
          <button
            type="button"
            onClick={handleApplyRagResponse}
            disabled={applyingRag}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-xl font-medium"
          >
            {applyingRag ? "Applying…" : "I filled rag_response.txt — finish now"}
          </button>
          <p className="text-slate-500 text-xs mt-4">
            <Link href="/assessments" className="text-indigo-400 underline">
              Open Assessments list
            </Link>{" "}
            if this page stays blank for several minutes.
          </p>
        </div>
      </div>
    );
  }

  if (notFoundConfirmed || !assessment) {
    return (
      <div className="text-center mt-20 space-y-4 px-4">
        <p className="text-white text-lg">Assessment not found.</p>
        <p className="text-slate-400 text-sm max-w-md mx-auto">
          The quiz was not saved (check backend + Postgres on port 5433), or the link is wrong. Open{" "}
          <Link href="/assessments" className="text-indigo-400 underline">
            Assessments
          </Link>{" "}
          for the latest quiz.
        </p>
        <Link
          href="/generate"
          className="inline-block bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-xl font-medium"
        >
          Back to Generate
        </Link>
      </div>
    );
  }

  if (
    assessment.status === "failed" &&
    !(assessment.questions && assessment.questions.length > 0)
  ) {
    const failureDetail =
      (assessment.config?.failure_detail as string) ||
      "Generation did not produce any questions.";
    const needed =
      (assessment.config?.total_questions as number) ||
      (assessment.config?.delivery_count as number) ||
      5;
    const topic = (assessment.config?.topic_focus as string) || "this chapter";
    return (
      <div className="flex flex-col h-[80vh] items-center justify-center space-y-6 px-4">
        <div className="w-16 h-16 rounded-full bg-rose-500/15 border border-rose-500/30 flex items-center justify-center">
          <span className="text-rose-400 text-2xl font-bold">!</span>
        </div>
        <div className="text-center max-w-lg">
          <h2 className="text-2xl font-bold text-white mb-2">Generation failed</h2>
          <p className="text-rose-300/90 text-sm mb-3 font-medium">{failureDetail}</p>
          <p className="text-slate-400 text-sm mb-4">
            Put a JSON array with ids &quot;1&quot; through &quot;{needed}&quot; (or more for
            oversample) in <code className="text-slate-300">rag_response.txt</code> at the project
            root for <strong className="text-slate-300">{topic}</strong>, then apply it here.
            The file must match the chapter you generated — trigonometry items will not load a
            Circles paper.
          </p>
          <button
            type="button"
            onClick={handleApplyRagResponse}
            disabled={applyingRag}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-xl font-medium"
          >
            {applyingRag ? "Applying…" : `Apply rag_response.txt (${needed} questions)`}
          </button>
          <p className="text-slate-500 text-xs mt-4">
            <Link href="/generate" className="text-indigo-400 underline">
              Back to Generate
            </Link>
            {" · "}
            <Link href="/assessments" className="text-indigo-400 underline">
              All assessments
            </Link>
          </p>
        </div>
      </div>
    );
  }

  const getBaseUrl = getApiBaseUrl;
  const cacheKey = exportCacheKey(assessment);
  const shortId = assessment.id?.slice(0, 8);

  const getDifficultyColor = (diff: string) => {
    switch (diff.toLowerCase()) {
      case "easy":
        return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
      case "medium":
        return "text-amber-400 bg-amber-400/10 border-amber-400/20";
      case "hard":
        return "text-rose-400 bg-rose-400/10 border-rose-400/20";
      default:
        return "text-slate-400 bg-slate-400/10 border-slate-400/20";
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-20">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-4">
          <Link
            href="/assessments"
            className="p-2 bg-[#1e293b] rounded-xl border border-[#334155] text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">{assessment.title}</h1>
            <p className="text-xs text-slate-500 font-mono mb-1" title={assessment.id}>
              Assessment {shortId}…
              {assessment.created_at
                ? ` · ${new Date(assessment.created_at).toLocaleString()}`
                : ""}
            </p>
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span className="flex items-center gap-1">
                <HelpCircle className="w-4 h-4" />{" "}
                {assessment.questions?.length ||
                  (assessment.config?.total_questions as number) ||
                  0}{" "}
                Questions
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> {assessment.total_marks} Marks
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 w-full md:w-auto">
          {assessment.status === "ready" && (
            <button
              type="button"
              onClick={handleApplyRagResponse}
              disabled={applyingRag}
              className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl font-medium transition-all"
            >
              {applyingRag
                ? "Applying…"
                : regenSlot
                  ? `Apply slot ${regenSlot} from rag_response.txt`
                  : "Apply rag_response.txt updates"}
            </button>
          )}
          <ExportActions
            assessment={assessment}
            cacheKey={cacheKey}
            exportingPdf={exportingPdf}
            onRegenerateExport={handleRegenerateExport}
            variant="inline"
          />
        </div>
      </header>

      <ExportActions
        assessment={assessment}
        cacheKey={cacheKey}
        exportingPdf={exportingPdf}
        onRegenerateExport={handleRegenerateExport}
        variant="card"
      />

      {assessment.generation_log && assessment.generation_log.length > 0 && (
        <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl">
          <h2 className="text-lg font-bold text-white mb-2">RAG → LLM generation trace</h2>
          <p className="text-sm text-slate-400 mb-4">
            Shows intermediate RAG/LLM attempts during auto-generation. If the paper was fixed via{" "}
            <code className="text-indigo-300">rag_response.txt</code>, use the{" "}
            <strong className="text-slate-300">Generated questions</strong> section below as the
            final paper (not old trace previews).
          </p>
          <GenerationTrace log={assessment.generation_log} />
          {assessment.generation_log?.some(
            (s: { step?: string }) => s.step === "applied_rag"
          ) && (
            <p className="text-xs text-emerald-400/90 mt-3">
              Look for step <strong>applied_rag</strong> above — questions below match the last
              successful apply from <code className="text-indigo-300">rag_response.txt</code>.
            </p>
          )}
        </div>
      )}

      <div>
        <h2 className="text-lg font-bold text-white mb-4">Generated questions</h2>
      </div>

      <div className="space-y-6">
        {assessment.questions?.length === 0 && (
          <p className="text-slate-400 text-center py-8">No questions in this assessment yet.</p>
        )}
        {assessment.questions?.map((q: any, idx: number) => (
          <div
            key={q.id}
            className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl relative overflow-hidden group"
          >
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-indigo-500 to-pink-500 opacity-50"></div>

            <div className="flex flex-wrap justify-between items-start gap-4 mb-4">
              <div className="flex items-center gap-3">
                <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#0f172a] border border-[#334155] font-bold text-indigo-400">
                  {idx + 1}
                </span>
                <span className="text-sm font-medium text-slate-300 bg-[#0f172a] px-3 py-1 rounded-full border border-[#334155]">
                  {(q.question_type || "Question").replace(/([A-Z])/g, " $1").trim()}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full border ${getDifficultyColor(q.difficulty)} uppercase`}
                >
                  {q.difficulty}
                </span>
                <span className="text-xs font-medium text-slate-300 bg-[#0f172a] px-2.5 py-1 rounded-full border border-[#334155]">
                  {q.bloom_level}
                </span>
                <span className="text-xs font-bold text-indigo-300 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
                  {q.marks} Mark{q.marks > 1 ? "s" : ""}
                </span>
              </div>
            </div>

            <div className="text-white mb-6 text-left max-w-full">
              <QuestionContent text={q.content} />
            </div>

            {q.figure_url && (
              <div className="mb-6 rounded-xl overflow-hidden border border-[#334155] inline-block bg-[#0f172a] p-4">
                <img
                  src={`${getBaseUrl()}${q.figure_url}?v=${q.id}`}
                  alt="Generated Figure"
                  className="max-w-full max-h-[300px] object-contain"
                />
              </div>
            )}

            {Array.isArray(q.options) && q.options.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
                {q.options.map((opt: any, i: number) => (
                  <div
                    key={i}
                    className={`p-4 rounded-xl border flex gap-3 ${opt.is_correct ? "bg-emerald-500/10 border-emerald-500/30" : "bg-[#0f172a] border-[#334155]"}`}
                  >
                    <span
                      className={`font-bold ${opt.is_correct ? "text-emerald-400" : "text-indigo-400"}`}
                    >
                      {opt.label}.
                    </span>
                    <span className="text-slate-300">{opt.text}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="bg-[#0f172a]/50 rounded-xl border border-[#334155] p-5 mt-6">
              <h4 className="text-sm font-bold text-emerald-400 mb-2 uppercase tracking-wider">
                Correct Answer & Explanation
              </h4>
              {q.question_type !== "MCQ" && q.correct_answer && (
                <div className="text-white mb-3 font-medium max-w-full">
                  <AnswerContent text={q.correct_answer} />
                </div>
              )}
              {q.explanation && (
                <div className="text-sm text-slate-400 italic border-l-2 border-slate-600 pl-3 max-w-full">
                  <QuestionContent text={q.explanation} className="text-sm" />
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <FeedbackWidget questionId={q.id} assessmentId={assessment.id} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FeedbackWidget({
  questionId,
  assessmentId,
}: {
  questionId: string;
  assessmentId: string;
}) {
  const [rating, setRating] = useState(0);
  const [submitted, setSubmitted] = useState(false);

  const handleRate = async (value: number) => {
    setRating(value);
    try {
      await submitFeedback({
        question_id: questionId,
        assessment_id: assessmentId,
        rating: value,
      });
      setSubmitted(true);
    } catch (err) {
      console.error(err);
    }
  };

  if (submitted)
    return (
      <span className="text-xs text-emerald-400 flex items-center gap-1">
        <CheckCircle2 className="w-3 h-3" /> Feedback saved. AI will learn from this.
      </span>
    );

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 mr-2">Rate quality:</span>
      {[1, 2, 3, 4, 5].map((v) => (
        <button key={v} onClick={() => handleRate(v)} className="hover:scale-110 transition-transform">
          <Star
            className={`w-4 h-4 ${rating >= v ? "fill-amber-400 text-amber-400" : "text-slate-600 hover:text-amber-400"}`}
          />
        </button>
      ))}
    </div>
  );
}

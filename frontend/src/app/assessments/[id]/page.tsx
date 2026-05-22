"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getAssessment,
  getAssessmentStatus,
  submitFeedback,
  getApiBaseUrl,
  applyRagResponse,
  formatApiError,
} from "@/lib/api";
import { useParams } from "next/navigation";
import { Download, ArrowLeft, Star, FileCheck, HelpCircle, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import GenerationTrace from "@/components/GenerationTrace";
import { QuestionContent } from "@/lib/questionText";

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

export default function AssessmentDetails() {
  const params = useParams();
  const id = params.id as string;
  const [assessment, setAssessment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [pollNote, setPollNote] = useState("");
  const [notFoundConfirmed, setNotFoundConfirmed] = useState(false);
  const [applyingRag, setApplyingRag] = useState(false);

  const loadFullAssessment = useCallback(async () => {
    const data = await getAssessment(id);
    setAssessment(data);
    setLoading(false);
    setPollNote("");
  }, [id]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let notFoundRetries = 0;

    const poll = async () => {
      if (cancelled) return;
      try {
        const status = await getAssessmentStatus(id);
        if (cancelled) return;

        if (status.status === "generating") {
          setAssessment((prev: any) => ({
            ...(prev || {}),
            id: status.id,
            title: status.title,
            status: "generating",
            total_marks: status.total_marks,
            questions: prev?.questions || [],
          }));
          setLoading(true);
          setNotFoundConfirmed(false);
          setPollNote(
            "Generation in progress (RAG may take up to 3 minutes). This page will update automatically."
          );
          window.setTimeout(poll, 3000);
          return;
        }

        await loadFullAssessment();
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
  }, [id, loadFullAssessment]);

  const handleApplyRagResponse = async () => {
    setApplyingRag(true);
    try {
      const data = await applyRagResponse(id);
      setAssessment(data);
      setLoading(false);
      setPollNote("");
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
            Save <code className="text-indigo-300">rag_response.txt</code> at the project root after{" "}
            <code className="text-indigo-300">rag_query.txt</code> updates (once per quiz).
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

  if (assessment.status === "failed") {
    const hint =
      (assessment.config && assessment.config.failure_hint) ||
      "No questions were saved. Common fixes: restart backend, ensure rag_response.txt is filled, then use the button below.";
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center space-y-4 px-4">
        <h2 className="text-2xl font-bold text-rose-400">Generation failed</h2>
        <p className="text-slate-400 text-sm">{hint}</p>
        <button
          type="button"
          onClick={handleApplyRagResponse}
          disabled={applyingRag}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-xl font-medium"
        >
          {applyingRag ? "Applying…" : "Apply rag_response.txt now"}
        </button>
        <Link href="/generate" className="inline-block text-indigo-400 underline">
          Back to Generate
        </Link>
      </div>
    );
  }

  const getBaseUrl = getApiBaseUrl;

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
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
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
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span className="flex items-center gap-1">
                <HelpCircle className="w-4 h-4" /> {assessment.questions?.length || 0} Questions
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> {assessment.total_marks} Marks
              </span>
            </div>
          </div>
        </div>

        <div className="flex gap-3 w-full md:w-auto">
          {assessment.pdf_url && (
            <a
              href={`${getBaseUrl()}${assessment.pdf_url}`}
              target="_blank"
              className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-xl font-medium shadow-lg shadow-indigo-500/20 transition-all"
            >
              <Download className="w-4 h-4" /> Question Paper
            </a>
          )}
          {assessment.answer_key_url && (
            <a
              href={`${getBaseUrl()}${assessment.answer_key_url}`}
              target="_blank"
              className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-[#1e293b] hover:bg-indigo-500/20 border border-[#334155] hover:border-indigo-500/30 text-white px-6 py-2.5 rounded-xl font-medium transition-all"
            >
              <FileCheck className="w-4 h-4" /> Answer Key
            </a>
          )}
        </div>
      </header>

      {assessment.generation_log && assessment.generation_log.length > 0 && (
        <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl">
          <h2 className="text-lg font-bold text-white mb-2">RAG → LLM generation trace</h2>
          <p className="text-sm text-slate-400 mb-4">
            Each step shows the PDF chunks retrieved, the full prompt built from RAG, the output for
            that prompt, and the quiz questions below.
          </p>
          <GenerationTrace log={assessment.generation_log} />
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
                  {q.question_type.replace(/([A-Z])/g, " $1").trim()}
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

            <p className="text-lg text-white mb-6 leading-relaxed whitespace-pre-wrap">
              <QuestionContent text={q.content} />
            </p>

            {q.figure_url && (
              <div className="mb-6 rounded-xl overflow-hidden border border-[#334155] inline-block bg-[#0f172a] p-4">
                <img
                  src={`${getBaseUrl()}${q.figure_url}`}
                  alt="Generated Figure"
                  className="max-w-full max-h-[300px] object-contain"
                />
              </div>
            )}

            {q.options && q.options.length > 0 && (
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
                <div className="text-white mb-3 font-medium">
                  <QuestionContent text={q.correct_answer} />
                </div>
              )}
              {q.explanation && (
                <div className="text-sm text-slate-400 leading-relaxed italic border-l-2 border-slate-600 pl-3">
                  {q.explanation}
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

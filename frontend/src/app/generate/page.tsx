"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import {
  getDocuments,
  getDocumentTopicProfile,
  generateAssessment,
  getAssessments,
  checkBackendHealth,
  formatApiError,
  type TopicProfile,
} from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { Settings2, Layers, BookOpen, BrainCircuit, Loader2, RefreshCw } from "lucide-react";

function statusLabel(status: string) {
  switch (status) {
    case "ready":
      return "Ready";
    case "processing":
      return "Processing…";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

function GeneratePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedDoc = searchParams.get("doc");

  const [documents, setDocuments] = useState<any[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [docsError, setDocsError] = useState("");
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);

  const [docId, setDocId] = useState("");
  const [title, setTitle] = useState("");
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [topicFocus, setTopicFocus] = useState("");
  const [examLevel, setExamLevel] = useState("");
  const [instructions, setInstructions] = useState("");
  const [weakIn, setWeakIn] = useState("");
  const [strongIn, setStrongIn] = useState("");
  const [language, setLanguage] = useState("English");
  const [topicProfile, setTopicProfile] = useState<TopicProfile | null>(null);
  const [topicLoading, setTopicLoading] = useState(false);
  const [topicError, setTopicError] = useState("");

  const allTypes = [
    "MCQ",
    "ShortAnswer",
    "LongAnswer",
    "FigureBased",
    "TrueFalse",
    "FillBlank",
    "AssertionReason",
    "MatchColumn",
    "CaseStudy",
  ];
  const [selectedTypes, setSelectedTypes] = useState<string[]>(["MCQ", "ShortAnswer"]);

  const [easy, setEasy] = useState(10);
  const [medium, setMedium] = useState(30);
  const [hard, setHard] = useState(60);

  const loadDocuments = useCallback(async (silent = false) => {
    if (!silent) setDocsLoading(true);
    setDocsError("");
    try {
      const data = await getDocuments();
      setDocuments(data);
      if (data.length > 0) {
        setDocId((current) => {
          if (current && data.some((d: { id: string }) => d.id === current)) {
            return current;
          }
          if (preselectedDoc && data.some((d: { id: string }) => d.id === preselectedDoc)) {
            return preselectedDoc;
          }
          return data[0].id;
        });
      }
    } catch (err) {
      console.error(err);
      setDocsError(formatApiError(err));
      setBackendUp(false);
    } finally {
      setDocsLoading(false);
    }
  }, [preselectedDoc]);

  useEffect(() => {
    checkBackendHealth().then(setBackendUp);
    loadDocuments();
  }, [loadDocuments]);

  // Poll while any document is still processing (e.g. after upload)
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === "processing");
    if (!hasProcessing) return;
    const timer = setInterval(() => loadDocuments(true), 5000);
    return () => clearInterval(timer);
  }, [documents, loadDocuments]);

  useEffect(() => {
    if (preselectedDoc) setDocId(preselectedDoc);
  }, [preselectedDoc]);

  const selectedDoc = documents.find((d) => d.id === docId);

  useEffect(() => {
    if (!docId || selectedDoc?.status !== "ready") {
      setTopicProfile(null);
      setTopicError("");
      return;
    }
    let cancelled = false;
    const load = async () => {
      setTopicLoading(true);
      setTopicError("");
      try {
        const profile = await getDocumentTopicProfile(docId, topicFocus || undefined);
        if (!cancelled) setTopicProfile(profile);
      } catch (err) {
        if (!cancelled) {
          setTopicProfile(null);
          setTopicError(formatApiError(err));
        }
      } finally {
        if (!cancelled) setTopicLoading(false);
      }
    };
    const timer = setTimeout(load, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [docId, topicFocus, documents, selectedDoc?.status]);

  const handleTypeToggle = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleGenerate = async () => {
    if (!docId) return alert("Please select a document first");
    if (selectedDoc?.status === "processing") {
      return alert("Document is still processing. Wait until status is Ready.");
    }
    if (selectedDoc?.status === "failed") {
      return alert("This document failed to process. Upload it again.");
    }
    setLoading(true);

    const config = {
      document_id: docId,
      title: title || "New Assessment",
      total_questions: totalQuestions,
      question_types: selectedTypes,
      difficulty_distribution: { easy, medium, hard },
      bloom_levels: ["Remember", "Understand", "Apply", "Analyze"],
      figure_types: ["flowchart", "bar_graph", "labeled_diagram"],
      topic_focus: topicFocus || undefined,
      subject: selectedDoc?.subject || undefined,
      class_level: examLevel || selectedDoc?.class_level || undefined,
      language,
      weak_in: weakIn
        ? weakIn.split(/[,;]+/).map((s) => s.trim()).filter(Boolean)
        : undefined,
      strong_in: strongIn
        ? strongIn.split(/[,;]+/).map((s) => s.trim()).filter(Boolean)
        : undefined,
      instructions:
        instructions ||
        (examLevel ? `Exam level: ${examLevel}` : undefined),
    };

    try {
      const res = await generateAssessment(config);
      if (res?.id) {
        router.push(`/assessments/${res.id}`);
        return;
      }
      alert("Generate returned no assessment id. Check backend logs.");
    } catch (err: unknown) {
      console.error(err);
      const ax = err as { code?: string; response?: { data?: { detail?: string } } };
      if (ax.code === "ECONNABORTED") {
        try {
          const list = await getAssessments();
          const latest = list?.find(
            (a: { title?: string; status?: string }) =>
              a.title === (title || "New Assessment") && a.status === "generating"
          );
          if (latest?.id) {
            router.push(`/assessments/${latest.id}`);
            return;
          }
        } catch {
          /* ignore */
        }
        alert(
          "Create request timed out, but the quiz may still exist. Open Assessments in the sidebar and refresh."
        );
      } else {
        alert(formatApiError(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">Configure Generation</h1>
        <p className="text-slate-400">
          Questions follow CBSE Class 10 Maths Standard PYQ style (see CBSE_PYQ_REFERENCE.md). Upload your chapter PDF for content; PYQ PDFs are style reference only.
        </p>
      </header>

      {backendUp === false && (
        <div role="alert" className="bg-rose-500/10 border border-rose-500/30 text-rose-200 px-4 py-3 rounded-xl text-sm">
          <strong className="text-rose-300">Backend offline.</strong> Start Docker Desktop, then run{' '}
          <code className="text-indigo-300">docker compose up -d</code> in <code className="text-indigo-300">docker/</code>, then start the API on port 8000 (see SETUP_GUIDE.md).
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-indigo-400" />
              Source Material
            </h2>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-300">Select Document</label>
                  <button
                    type="button"
                    onClick={() => loadDocuments(false)}
                    disabled={docsLoading}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3 h-3 ${docsLoading ? "animate-spin" : ""}`} />
                    Refresh
                  </button>
                </div>
                <select
                  value={docId}
                  onChange={(e) => setDocId(e.target.value)}
                  disabled={docsLoading || documents.length === 0}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
                >
                  <option value="" disabled>
                    {docsLoading ? "Loading documents…" : "-- Select a document --"}
                  </option>
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.filename} ({statusLabel(d.status)})
                    </option>
                  ))}
                </select>
                {docsError && (
                  <p className="text-rose-400 text-xs mt-2">{docsError}</p>
                )}
                {!docsError && !docsLoading && documents.length === 0 && (
                  <p className="text-rose-400 text-xs mt-2">
                    No documents found.{" "}
                    <a href="/upload" className="underline text-indigo-400">
                      Upload one first
                    </a>
                    .
                  </p>
                )}
                {selectedDoc?.status === "ready" && (
                  <p className="text-slate-400 text-xs mt-2">
                    Questions use this PDF only (RAG). Set <strong className="text-slate-300">Topic focus</strong> to narrow the chapter — RD Sharma / RS Aggarwal exercise depth.
                  </p>
                )}
                {selectedDoc?.status === "ready" && (
                  <div className="mt-3 rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 text-sm">
                    <p className="text-indigo-300 font-medium mb-2">Extracted topics (from PDF)</p>
                    {topicLoading && (
                      <p className="text-slate-400 text-xs flex items-center gap-2">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Analyzing indexed chunks…
                      </p>
                    )}
                    {topicError && !topicLoading && (
                      <div className="text-amber-400 text-xs space-y-1">
                        <p>{topicError}</p>
                        {(topicError.toLowerCase().includes("not found") ||
                          topicError.includes("404")) && (
                          <p className="text-slate-500">
                            Restart the backend after pulling latest code (needs{" "}
                            <code className="text-indigo-300">GET /documents/…/topic-profile</code>
                            ). Or check Docker + Qdrant are running.
                          </p>
                        )}
                      </div>
                    )}
                    {topicProfile && !topicLoading && (
                      <div className="space-y-2 text-slate-300">
                        {topicProfile.chunk_count_used === 0 &&
                          (topicProfile.total_chunks_db ?? 0) > 0 && (
                            <p className="text-amber-400 text-xs">
                              PDF is indexed in DB ({topicProfile.total_chunks_db} chunks) but
                              Qdrant returned 0 chunks — start Qdrant (
                              <code className="text-indigo-300">docker compose up -d</code>
                              ) and re-upload, or check QDRANT_URL.
                            </p>
                          )}
                        {topicProfile.chunk_count_used === 0 &&
                          (topicProfile.total_chunks_db ?? 0) === 0 && (
                            <p className="text-amber-400 text-xs">
                              No text chunks stored — re-upload the PDF or wait for indexing to
                              finish.
                            </p>
                          )}
                        <p>
                          <span className="text-slate-500">Primary:</span>{" "}
                          <strong className="text-white">{topicProfile.primary_topic}</strong>
                          <span className="text-slate-500 ml-2">
                            (chapter: {topicProfile.locked_chapter})
                          </span>
                        </p>
                        {topicProfile.retrieval_confidence != null && (
                          <p className="text-xs text-slate-400">
                            Retrieval confidence:{" "}
                            <strong
                              className={
                                topicProfile.retrieval_confidence >= 0.45
                                  ? "text-emerald-400"
                                  : "text-amber-400"
                              }
                            >
                              {(topicProfile.retrieval_confidence * 100).toFixed(0)}%
                            </strong>
                            {" · "}
                            Mode: {topicProfile.generation_mode === "pdf_rich" ? "PDF-rich" : "Curriculum archetypes"}
                          </p>
                        )}
                        {topicProfile.required_theorems && topicProfile.required_theorems.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs text-slate-500 mb-1">Theorem coverage plan:</p>
                            <ul className="list-disc list-inside text-xs text-slate-400 max-h-24 overflow-y-auto">
                              {topicProfile.required_theorems.map((t) => (
                                <li key={t.id}>
                                  {t.label || t.id}
                                  <span className="text-slate-600">
                                    {t.importance ? ` · ${t.importance}` : ""}
                                    {t.difficulty ? ` · ${t.difficulty}` : ""}
                                    {t.cognitive_type ? ` · ${t.cognitive_type}` : ""}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {topicProfile.subtopics?.length > 0 ? (
                          <div className="mt-2">
                            <p className="text-xs text-slate-500 mb-1">Subtopics:</p>
                            <ul className="list-disc list-inside text-xs text-slate-400 max-h-24 overflow-y-auto">
                              {topicProfile.subtopics.map((s) => (
                                <li key={s}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500">
                            No subtopics from PDF text yet — chapter locked from filename (
                            {topicProfile.locked_chapter}). Add Topic focus or re-index with Qdrant
                            running.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {selectedDoc?.status === "processing" && (
                  <p className="text-amber-400 text-xs mt-2">
                    Indexing in background (usually 1–3 min). You can refresh — the list updates without blocking.
                    Use Upload → page range for faster indexing.
                  </p>
                )}
                {selectedDoc?.status === "failed" && selectedDoc?.error_message && (
                  <p className="text-rose-400 text-xs mt-2">{selectedDoc.error_message}</p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-slate-300 block mb-2">Assessment Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Midterm Biology Exam"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-300 block mb-2">
                  Topic focus (optional)
                </label>
                <input
                  type="text"
                  value={topicFocus}
                  onChange={(e) => setTopicFocus(e.target.value)}
                  placeholder="e.g. tangents to a circle, Chapter 10"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Narrows RAG to this topic — retrieval query is built from this + the PDF filename and content.
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-300 block mb-2">
                  Question language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="English">English</option>
                  <option value="Hindi">Hindi</option>
                  <option value="Tamil">Tamil</option>
                  <option value="Telugu">Telugu</option>
                  <option value="Marathi">Marathi</option>
                  <option value="Bengali">Bengali</option>
                  <option value="Kannada">Kannada</option>
                  <option value="Malayalam">Malayalam</option>
                  <option value="Gujarati">Gujarati</option>
                  <option value="Urdu">Urdu</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-300 block mb-2">
                  Exam / class level
                </label>
                <select
                  value={examLevel}
                  onChange={(e) => setExamLevel(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">From document (auto)</option>
                  <option value="Class 6">Class 6</option>
                  <option value="Class 7">Class 7</option>
                  <option value="Class 8">Class 8</option>
                  <option value="Class 9">Class 9</option>
                  <option value="Class 10">Class 10</option>
                  <option value="Class 11">Class 11</option>
                  <option value="Class 12">Class 12</option>
                  <option value="JEE Main">JEE Main</option>
                  <option value="JEE Advanced">JEE Advanced</option>
                  <option value="NEET">NEET</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-300 block mb-2">
                  Weak areas (optional, adaptive)
                </label>
                <input
                  type="text"
                  value={weakIn}
                  onChange={(e) => setWeakIn(e.target.value)}
                  placeholder="e.g. proof, cyclic quadrilateral, discriminant"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <p className="text-xs text-slate-500 mt-1">
                  More questions reinforcing these skills (comma-separated).
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-300 block mb-2">
                  Strong areas (optional, light touch)
                </label>
                <input
                  type="text"
                  value={strongIn}
                  onChange={(e) => setStrongIn(e.target.value)}
                  placeholder="e.g. basic angle chase, MCQ recall"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-300 block mb-2">
                  Extra instructions (optional)
                </label>
                <input
                  type="text"
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="e.g. numericals only, previous year pattern"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Layers className="w-5 h-5 text-pink-400" />
              Question Types
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {allTypes.map((type) => {
                const isSelected = selectedTypes.includes(type);
                return (
                  <div
                    key={type}
                    onClick={() => handleTypeToggle(type)}
                    className={`cursor-pointer border rounded-xl px-4 py-3 transition-all ${
                      isSelected
                        ? "bg-indigo-500/10 border-indigo-500 text-indigo-400"
                        : "bg-[#0f172a] border-[#334155] text-slate-400 hover:border-slate-500"
                    }`}
                  >
                    <div className="font-medium text-sm text-center">
                      {type.replace(/([A-Z])/g, " $1").trim()}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-teal-400" />
              Parameters
            </h2>

            <div className="space-y-6">
              <div>
                <label className="text-sm font-medium text-slate-300 flex justify-between mb-2">
                  <span>Total Questions</span>
                  <span className="text-indigo-400 font-bold">{totalQuestions}</span>
                </label>
                <input
                  type="range"
                  min="5"
                  max="50"
                  step="5"
                  value={totalQuestions}
                  onChange={(e) => setTotalQuestions(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div className="space-y-4 pt-4 border-t border-[#334155]">
                <h3 className="text-sm font-medium text-white">Difficulty Split (%)</h3>
                <p className="text-xs text-slate-500">
                  Default targets RD Sharma / RS Aggarwal exercise depth (60% hard). Even &quot;easy&quot; items need 2–3 steps.
                </p>

                <div>
                  <label className="text-xs text-slate-400 flex justify-between mb-1">
                    <span>Easy</span>
                    <span>{easy}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={easy}
                    onChange={(e) => setEasy(Number(e.target.value))}
                    className="w-full accent-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 flex justify-between mb-1">
                    <span>Medium</span>
                    <span>{medium}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={medium}
                    onChange={(e) => setMedium(Number(e.target.value))}
                    className="w-full accent-amber-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 flex justify-between mb-1">
                    <span>Hard</span>
                    <span>{hard}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={hard}
                    onChange={(e) => setHard(Number(e.target.value))}
                    className="w-full accent-rose-500"
                  />
                </div>
                <div className="text-xs text-center p-2 rounded-lg bg-[#0f172a] border border-[#334155]">
                  Total:{" "}
                  <span className={easy + medium + hard === 100 ? "text-emerald-400" : "text-rose-400"}>
                    {easy + medium + hard}%
                  </span>
                  {easy + medium + hard !== 100 && " (Must equal 100%)"}
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={
              loading ||
              !docId ||
              selectedDoc?.status !== "ready" ||
              easy + medium + hard !== 100 ||
              selectedTypes.length === 0
            }
            className="w-full bg-gradient-to-r from-indigo-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-4 rounded-2xl font-bold shadow-lg shadow-indigo-500/25 transition-all flex items-center justify-center gap-2 text-lg"
          >
            {loading ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" /> Generating...
              </>
            ) : (
              <>
                <BrainCircuit className="w-6 h-6" /> Generate Now
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function GeneratePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-[60vh] items-center justify-center">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
        </div>
      }
    >
      <GeneratePageContent />
    </Suspense>
  );
}

"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import {
  getDocuments,
  getDocumentTopicProfile,
  getChapters,
  getChapterProfile,
  generateAssessment,
  getAssessments,
  checkBackendHealth,
  formatApiError,
  type TopicProfile,
  type ChapterOption,
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
  const [useChapterPdf, setUseChapterPdf] = useState(false);
  const [chapters, setChapters] = useState<ChapterOption[]>([]);
  const [chaptersLoading, setChaptersLoading] = useState(true);
  const [selectedChapter, setSelectedChapter] = useState("");
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

  const [selectedTypes, setSelectedTypes] = useState<string[]>([
    "FigureBased",
    "ShortAnswer",
    "LongAnswer",
  ]);
  const [availableTypes, setAvailableTypes] = useState<string[]>([
    "MCQ",
    "ShortAnswer",
    "LongAnswer",
    "FigureBased",
    "TrueFalse",
    "FillBlank",
    "AssertionReason",
    "MatchColumn",
    "CaseStudy",
  ]);

  const [easy, setEasy] = useState(0);
  const [medium, setMedium] = useState(0);
  const [hard, setHard] = useState(100);

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
    (async () => {
      setChaptersLoading(true);
      try {
        const data = await getChapters();
        setChapters(data.chapters || []);
        if (data.chapters?.length) {
          setSelectedChapter((cur) => cur || data.chapters[0].chapter_key);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setChaptersLoading(false);
      }
    })();
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

  const selectedChapterMeta = chapters.find((c) => c.chapter_key === selectedChapter);

  useEffect(() => {
    if (!selectedChapterMeta) return;
    const relevant = selectedChapterMeta.relevant_question_types;
    setAvailableTypes(relevant);
    setSelectedTypes((prev) => {
      const kept = prev.filter((t) => relevant.includes(t));
      const base =
        kept.length > 0 ? kept : relevant.slice(0, Math.min(3, relevant.length));
      const maxFig = selectedChapterMeta.max_figure_based ?? 0;
      if (
        maxFig >= 2 &&
        relevant.includes("FigureBased") &&
        !base.includes("FigureBased")
      ) {
        return ["FigureBased", ...base].slice(0, Math.max(3, base.length + 1));
      }
      return base;
    });
  }, [selectedChapter, selectedChapterMeta?.chapter_key]);

  useEffect(() => {
    if (!selectedChapter) {
      setTopicProfile(null);
      setTopicError("");
      return;
    }
    const usePdf = useChapterPdf && docId && selectedDoc?.status === "ready";
    if (docId && selectedDoc?.status !== "ready") {
      if (!usePdf) {
        setTopicProfile(null);
      }
      if (selectedDoc?.status === "processing" || selectedDoc?.status === "failed") {
        return;
      }
    }
    let cancelled = false;
    const load = async () => {
      setTopicLoading(true);
      setTopicError("");
      try {
        let profile: TopicProfile;
        if (usePdf) {
          profile = await getDocumentTopicProfile(docId, topicFocus || undefined);
          if (selectedChapter) {
            profile = {
              ...profile,
              locked_chapter: selectedChapter,
              primary_topic:
                selectedChapterMeta?.display_title || profile.primary_topic,
            };
          }
        } else {
          profile = await getChapterProfile(selectedChapter, {
            topicFocus: topicFocus || undefined,
            classLevel: examLevel || undefined,
          });
        }
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
  }, [
    docId,
    topicFocus,
    examLevel,
    documents,
    selectedDoc?.status,
    selectedChapter,
    selectedChapterMeta?.display_title,
    useChapterPdf,
  ]);

  useEffect(() => {
    if (!docId || selectedDoc?.status !== "ready") {
      setUseChapterPdf(false);
    }
  }, [docId, selectedDoc?.status]);

  const handleTypeToggle = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleGenerate = async () => {
    if (!selectedChapter) return alert("Please select a topic first");
    if (useChapterPdf && docId && selectedDoc?.status === "processing") {
      return alert("Document is still processing. Wait until status is Ready.");
    }
    if (useChapterPdf && docId && selectedDoc?.status === "failed") {
      return alert("This document failed to process. Upload it again.");
    }
    setLoading(true);

    const chapterTitle = selectedChapterMeta?.display_title || selectedChapter;
    const config: Record<string, unknown> = {
      document_id: docId || undefined,
      use_chapter_pdf: useChapterPdf && !!docId,
      locked_chapter: selectedChapter,
      title: title || `${chapterTitle} Assessment`,
      total_questions: totalQuestions,
      question_types: selectedTypes,
      difficulty_distribution: { easy, medium, hard },
      bloom_levels: ["Remember", "Understand", "Apply", "Analyze"],
      figure_types: ["flowchart", "bar_graph", "labeled_diagram"],
      topic_focus: topicFocus || chapterTitle,
      subject: selectedDoc?.subject || "Mathematics",
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
          Select a topic from ingested CBSE papers, or add your chapter PDF for richer RAG. Question types shown match the selected topic.
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
                <label className="text-sm font-medium text-slate-300 block mb-2">
                  Select Topic <span className="text-rose-400">*</span>
                </label>
                <select
                  value={selectedChapter}
                  onChange={(e) => setSelectedChapter(e.target.value)}
                  disabled={chaptersLoading || chapters.length === 0}
                  className="w-full bg-[#0f172a] border border-indigo-500/40 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
                >
                  <option value="" disabled>
                    {chaptersLoading ? "Loading topics…" : "-- Select a topic --"}
                  </option>
                  {chapters.map((ch) => (
                    <option key={ch.chapter_key} value={ch.chapter_key}>
                      {ch.display_title}
                      {ch.cbse_stem_count > 0 ? ` (${ch.cbse_stem_count} CBSE stems)` : ""}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  Topics come from CBSE_QuestionPapers ingestion. Generate without a PDF uses board-style exemplars only.
                </p>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-300">
                    Chapter PDF <span className="text-slate-500 font-normal">(optional)</span>
                  </label>
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
                  disabled={docsLoading}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
                >
                  <option value="">
                    {docsLoading ? "Loading documents…" : "— No PDF (CBSE topic only) —"}
                  </option>
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.filename} ({statusLabel(d.status)})
                    </option>
                  ))}
                </select>
                <label
                  className={`mt-3 flex items-start gap-3 rounded-xl border px-4 py-3 cursor-pointer transition-colors ${
                    docId && selectedDoc?.status === "ready"
                      ? "border-indigo-500/40 bg-indigo-500/5 hover:bg-indigo-500/10"
                      : "border-[#334155] bg-[#0f172a]/50 opacity-60 cursor-not-allowed"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={useChapterPdf}
                    onChange={(e) => setUseChapterPdf(e.target.checked)}
                    disabled={!docId || selectedDoc?.status !== "ready"}
                    className="mt-1 h-4 w-4 rounded border-[#334155] text-indigo-500 focus:ring-indigo-500"
                  />
                  <span className="text-sm text-slate-300">
                    <span className="font-medium text-white">Use chapter PDF</span>
                    <span className="block text-xs text-slate-500 mt-0.5">
                      {docId && selectedDoc?.status === "ready"
                        ? "Checked: RAG pulls from your uploaded PDF plus CBSE board style for the selected topic."
                        : "Select a ready PDF above to enable textbook RAG. Unchecked uses CBSE topic exemplars only."}
                    </span>
                  </span>
                </label>
                {docsError && (
                  <p className="text-rose-400 text-xs mt-2">{docsError}</p>
                )}
                {!docsError && !docsLoading && documents.length === 0 && (
                  <p className="text-slate-500 text-xs mt-2">
                    No PDF uploaded — generation uses CBSE board stems for the selected topic.{" "}
                    <a href="/upload" className="underline text-indigo-400">
                      Upload a chapter PDF
                    </a>{" "}
                    for textbook RAG.
                  </p>
                )}
                {useChapterPdf && selectedDoc?.status === "ready" && (
                  <p className="text-slate-400 text-xs mt-2">
                    PDF + selected topic: RAG from your PDF, style from CBSE index for{" "}
                    <strong className="text-slate-300">{selectedChapterMeta?.display_title}</strong>.
                  </p>
                )}
                {docId && !useChapterPdf && selectedChapter && (
                  <p className="text-slate-400 text-xs mt-2">
                    PDF selected but not used — generation uses CBSE board stems for{" "}
                    <strong className="text-slate-300">{selectedChapterMeta?.display_title}</strong> only.
                  </p>
                )}
                {selectedChapter && (
                  <div className="mt-3 rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 text-sm">
                    <p className="text-indigo-300 font-medium mb-2">
                      {useChapterPdf && docId && selectedDoc?.status === "ready"
                        ? "Topic + PDF profile"
                        : "CBSE topic profile"}
                    </p>
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
                            ). Or restart the backend (FAISS index loads from backend/data/faiss).
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
                              FAISS returned 0 chunks — re-upload the PDF or restart the backend
                              so indexing writes to{" "}
                              <code className="text-indigo-300">backend/data/faiss/documents</code>.
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
                            {topicProfile.locked_chapter}). Add Topic focus or re-upload the PDF
                            to rebuild the local FAISS index.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {docId && selectedDoc?.status === "processing" && (
                  <p className="text-amber-400 text-xs mt-2">
                    Indexing in background (usually 1–3 min). You can refresh — the list updates without blocking.
                    Use Upload → page range for faster indexing.
                  </p>
                )}
                {docId && selectedDoc?.status === "failed" && selectedDoc?.error_message && (
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
            {selectedChapter && (
              <p className="text-xs text-slate-500 mb-3">
                Showing types relevant to{" "}
                <strong className="text-slate-400">{selectedChapterMeta?.display_title}</strong>
                {selectedChapterMeta?.relevant_question_types?.includes("FigureBased") &&
                  selectedChapterMeta.max_figure_based > 0 &&
                  ` (up to ${selectedChapterMeta.max_figure_based} figure-based)`}
                .
              </p>
            )}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {availableTypes.map((type) => {
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
                  Default is <strong className="text-rose-300">100% hard</strong> (full-hard / L5 every slot, GATE floors when enabled).
                  Lower hard % only if you want a mixed paper.
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
              !selectedChapter ||
              (!!docId && selectedDoc?.status !== "ready") ||
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

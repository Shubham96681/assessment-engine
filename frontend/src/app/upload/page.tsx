"use client";

import { useState, useRef } from "react";
import { uploadDocument } from "@/lib/api";
import { UploadCloud, File, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { useRouter } from "next/navigation";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [subject, setSubject] = useState("");
  const [classLevel, setClassLevel] = useState("");
  const [pageStart, setPageStart] = useState("");
  const [pageEnd, setPageEnd] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf") {
        setFile(droppedFile);
      } else {
        setErrorMessage("Please upload a PDF file.");
        setStatus("error");
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setStatus("idle");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    
    try {
      const ps = pageStart ? parseInt(pageStart, 10) : undefined;
      const pe = pageEnd ? parseInt(pageEnd, 10) : undefined;
      const doc = await uploadDocument(file, subject, classLevel, ps, pe);
      setStatus("success");
      setTimeout(() => {
        router.push(`/generate?doc=${doc.id}`);
      }, 1500);
    } catch (error: any) {
      console.error(error);
      const detail = error.response?.data?.detail;
      const isNetwork =
        error.code === "ERR_NETWORK" || error.message === "Network Error";
      const detailText =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(", ")
            : "";
      setErrorMessage(
        detailText ||
          (isNetwork
            ? "Cannot reach the API server. Start the backend (port 8000) and Postgres (docker compose up -d postgres)."
            : `Failed to upload document (${error.response?.status || "unknown error"}).`)
      );
      setStatus("error");
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">Upload Curriculum</h1>
        <p className="text-slate-400">
          Upload a PDF for the RAG engine. Use page range to index only one chapter (much faster than a full book).
        </p>
      </header>

      <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-8 shadow-xl">
        <div 
          className={`border-2 border-dashed rounded-xl p-12 flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${
            file ? 'border-indigo-500 bg-indigo-500/5' : 'border-[#334155] hover:border-indigo-400 hover:bg-[#334155]/30'
          }`}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileSelect} 
            accept="application/pdf" 
            className="hidden" 
          />
          
          {file ? (
            <div className="space-y-4">
              <div className="w-16 h-16 bg-indigo-500/20 rounded-full flex items-center justify-center mx-auto text-indigo-400">
                <File className="w-8 h-8" />
              </div>
              <div>
                <p className="text-white font-medium">{file.name}</p>
                <p className="text-sm text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="w-16 h-16 bg-[#0f172a] rounded-full flex items-center justify-center mx-auto shadow-inner border border-[#334155]">
                <UploadCloud className="w-8 h-8 text-slate-400" />
              </div>
              <div>
                <p className="text-white font-medium">Click to upload or drag and drop</p>
                <p className="text-sm text-slate-400">PDF files only (Max 50MB)</p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-8 grid grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Subject / Course</label>
            <input 
              type="text" 
              placeholder="e.g. Biology, Grade 10" 
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Class / Target Audience</label>
            <input 
              type="text" 
              placeholder="e.g. High School" 
              value={classLevel}
              onChange={(e) => setClassLevel(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
            />
          </div>
        </div>

        <div className="mt-6 p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-sm text-slate-300">
          <strong className="text-indigo-300">Speed tip:</strong> Set page range to index one chapter only (e.g. 145–165).
          Quiz generation uses ~6 matching sections, not every page.
        </div>

        <div className="mt-6 grid grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">From page (optional)</label>
            <input
              type="number"
              min={1}
              placeholder="e.g. 145"
              value={pageStart}
              onChange={(e) => setPageStart(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">To page (optional)</label>
            <input
              type="number"
              min={1}
              placeholder="e.g. 165"
              value={pageEnd}
              onChange={(e) => setPageEnd(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        {status === "error" && (
          <div className="mt-6 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center gap-3 text-rose-400">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p className="text-sm">{errorMessage}</p>
          </div>
        )}

        {status === "success" && (
          <div className="mt-6 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-3 text-emerald-400">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <p className="text-sm">Document uploaded and processed successfully! Redirecting...</p>
          </div>
        )}

        <div className="mt-8 flex justify-end">
          <button 
            onClick={handleUpload}
            disabled={!file || status === "uploading" || status === "success"}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-medium shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-2"
          >
            {status === "uploading" ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Processing...
              </>
            ) : (
              "Upload & Analyze Document"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

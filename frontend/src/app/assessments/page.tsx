"use client";

import { useEffect, useState } from "react";
import { getAssessments, deleteAssessment, getApiBaseUrl } from "@/lib/api";
import Link from "next/link";
import { FileText, Download, Trash2, ExternalLink, Calendar, CheckCircle2, Clock, XCircle } from "lucide-react";

export default function AssessmentsList() {
  const [assessments, setAssessments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const fetchAssessments = () => {
    setLoading(true);
    setLoadError(null);
    getAssessments()
      .then(data => {
        setAssessments(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        const isTimeout =
          err.code === 'ECONNABORTED' ||
          String(err.message || '').includes('timeout');
        setLoadError(
          isTimeout
            ? 'Request timed out — backend is busy indexing or not running. Restart backend, wait 30s, then Retry.'
            : 'Cannot reach the API. Start the backend on port 8000.'
        );
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchAssessments();
    const poll = setInterval(() => {
      setAssessments(prev => {
        if (prev.some(a => a.status === 'generating')) fetchAssessments();
        return prev;
      });
    }, 5000);
    return () => clearInterval(poll);
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this assessment?")) return;
    try {
      await deleteAssessment(id);
      fetchAssessments();
    } catch (err) {
      console.error(err);
      alert("Failed to delete assessment");
    }
  };

  if (loading) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
        <div className="w-16 h-16 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
        <p className="text-slate-400 text-sm max-w-md text-center">
          Loading assessments… If this takes more than 20s, the backend may be busy generating
          questions — check that port 8000 is running and refresh.
        </p>
      </div>
    );
  }

  const StatusBadge = ({ status }: { status: string }) => {
    switch (status) {
      case "ready":
        return <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20"><CheckCircle2 className="w-3.5 h-3.5" /> Ready</span>;
      case "generating":
        return <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 text-xs font-medium border border-amber-500/20"><Clock className="w-3.5 h-3.5 animate-pulse" /> Generating</span>;
      default:
        return <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 text-xs font-medium border border-rose-500/20"><XCircle className="w-3.5 h-3.5" /> Failed</span>;
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">My Assessments</h1>
          <p className="text-slate-400">View, download, and manage your generated question papers.</p>
        </div>
        <Link href="/generate" className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-xl font-medium shadow-lg shadow-indigo-500/20 transition-all">
          Generate New
        </Link>
      </header>

      {loadError && (
        <div role="alert" className="bg-rose-500/10 border border-rose-500/30 text-rose-300 px-4 py-3 rounded-xl text-sm flex justify-between items-center">
          <span>{loadError}</span>
          <button type="button" onClick={fetchAssessments} className="text-white underline ml-4">Retry</button>
        </div>
      )}

      {assessments.length === 0 && !loadError ? (
        <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-16 text-center shadow-xl">
          <div className="w-20 h-20 bg-[#0f172a] rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner border border-[#334155]">
            <FileText className="w-10 h-10 text-slate-500" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">No Assessments Yet</h2>
          <p className="text-slate-400 mb-8 max-w-md mx-auto">You haven't generated any assessments yet. Upload a document and let our AI create one for you.</p>
          <Link href="/upload" className="bg-white text-slate-900 px-8 py-3 rounded-xl font-bold hover:bg-indigo-50 transition-colors">
            Get Started
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {assessments.map(item => (
            <div key={item.id} className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl flex flex-col group hover:border-indigo-500/50 transition-colors">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20 text-indigo-400">
                  <FileText className="w-6 h-6" />
                </div>
                <StatusBadge status={item.status} />
              </div>
              
              <h3 className="text-lg font-bold text-white mb-2 line-clamp-2" title={item.title}>
                {item.title}
              </h3>
              
              <div className="space-y-2 mb-6 flex-1">
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Calendar className="w-4 h-4" />
                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <span className="font-medium text-slate-300">Marks:</span> {item.total_marks}
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <span className="font-medium text-slate-300">Gen #:</span> {item.generation_num}
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3 pt-4 border-t border-[#334155]">
                <Link 
                  href={`/assessments/${item.id}`}
                  className="flex items-center justify-center gap-2 bg-[#0f172a] hover:bg-indigo-500/10 border border-[#334155] hover:border-indigo-500/30 text-white py-2 rounded-xl text-sm font-medium transition-colors"
                >
                  <ExternalLink className="w-4 h-4" /> View Details
                </Link>
                
                {item.pdf_url ? (
                  <a 
                    href={`${getApiBaseUrl()}${item.pdf_url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-xl text-sm font-medium transition-colors"
                  >
                    <Download className="w-4 h-4" /> PDF
                  </a>
                ) : item.status === "ready" ? (
                  <Link
                    href={`/assessments/${item.id}`}
                    className="flex items-center justify-center gap-2 bg-indigo-600/80 hover:bg-indigo-500 text-white py-2 rounded-xl text-sm font-medium transition-colors"
                  >
                    <Download className="w-4 h-4" /> Export
                  </Link>
                ) : (
                  <button className="flex items-center justify-center gap-2 bg-[#0f172a] border border-[#334155] text-slate-500 py-2 rounded-xl text-sm font-medium cursor-not-allowed">
                    <Download className="w-4 h-4" /> Unavailable
                  </button>
                )}
              </div>
              
              <button 
                onClick={() => handleDelete(item.id)}
                className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 p-2 text-slate-400 hover:text-rose-400 bg-[#0f172a]/80 backdrop-blur rounded-lg transition-all"
                title="Delete Assessment"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { getDashboardStats, getApiBaseUrl } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from "recharts";
import { FileText, Sparkles, Target, Activity } from "lucide-react";
import Link from "next/link";

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setStats({
          total_documents: 0,
          total_assessments: 0,
          total_questions_generated: 0,
          avg_quality_score: 0,
          bloom_distribution: {},
          difficulty_distribution: {},
          question_type_distribution: {},
          recent_assessments: [],
        });
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="w-16 h-16 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  const bloomData = stats ? Object.entries(stats.bloom_distribution).map(([name, value]) => ({ name, value })) : [];
  const typeData = stats ? Object.entries(stats.question_type_distribution).map(([name, value]) => ({ name, value })) : [];

  const COLORS = ['#6366f1', '#ec4899', '#14b8a6', '#f59e0b', '#8b5cf6', '#06b6d4'];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Welcome back, Teacher</h1>
          <p className="text-slate-400">Here's an overview of your assessment generations.</p>
        </div>
        <Link href="/generate" className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-xl font-medium shadow-lg shadow-indigo-500/20 transition-all">
          + New Assessment
        </Link>
      </header>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="Total Documents" 
          value={stats?.total_documents || 0} 
          icon={<FileText className="w-6 h-6 text-indigo-400" />} 
          trend="+2 this week" 
        />
        <MetricCard 
          title="Assessments Created" 
          value={stats?.total_assessments || 0} 
          icon={<Sparkles className="w-6 h-6 text-pink-400" />} 
          trend="+5 this week" 
        />
        <MetricCard 
          title="Questions Generated" 
          value={stats?.total_questions_generated || 0} 
          icon={<Target className="w-6 h-6 text-teal-400" />} 
          trend="+120 this week" 
        />
        <MetricCard 
          title="Avg. Quality Score" 
          value={`${(stats?.avg_quality_score * 100 || 0).toFixed(1)}%`} 
          icon={<Activity className="w-6 h-6 text-amber-400" />} 
          trend="+2.4% vs last week" 
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl">
          <h2 className="text-lg font-bold text-white mb-6">Cognitive Level Distribution (Bloom's)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bloomData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip 
                  cursor={{ fill: '#334155', opacity: 0.4 }}
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }} 
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {bloomData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl">
          <h2 className="text-lg font-bold text-white mb-6">Question Types Generated</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={typeData} layout="vertical" margin={{ top: 0, right: 0, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} width={80} axisLine={false} tickLine={false} />
                <Tooltip 
                  cursor={{ fill: '#334155', opacity: 0.4 }}
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }} 
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {typeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {stats?.recent_assessments?.length > 0 && (
        <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl">
          <h2 className="text-lg font-bold text-white mb-4">Recent assessments & questions</h2>
          <p className="text-sm text-slate-400 mb-4">
            Board-style questions from your PDF. Download the question paper when status is Ready.
          </p>
          <div className="space-y-4">
            {stats.recent_assessments.map((a: any) => (
              <div key={a.id} className="p-4 rounded-xl bg-[#0f172a] border border-[#334155]">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <Link href={`/assessments/${a.id}`} className="font-medium text-white hover:text-indigo-300">
                    {a.title || "Untitled"}
                  </Link>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">{a.question_count ?? 0} Q · {a.status}</span>
                    {a.status === "ready" && a.pdf_url && (
                      <a
                        href={`${getApiBaseUrl()}${a.pdf_url}?v=${a.id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded-lg"
                      >
                        Download PDF
                      </a>
                    )}
                  </div>
                </div>
                {a.sample_questions?.length > 0 ? (
                  <ul className="space-y-3">
                    {a.sample_questions.map((q: any) => (
                      <li key={q.id} className="text-sm border-l-2 border-indigo-500/40 pl-3">
                        <p className="text-slate-300 line-clamp-2">{q.content}</p>
                        {q.figure_url && (
                          <img
                            src={`${getApiBaseUrl()}${q.figure_url}`}
                            alt="Figure"
                            className="mt-2 max-h-32 rounded-lg border border-[#334155] bg-white"
                          />
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-500">No questions yet.</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value, icon, trend }: { title: string, value: string | number, icon: React.ReactNode, trend: string }) {
  return (
    <div className="bg-[#1e293b]/50 backdrop-blur-md border border-[#334155] rounded-2xl p-6 shadow-xl transition-transform hover:-translate-y-1 duration-300">
      <div className="flex justify-between items-start mb-4">
        <div className="p-3 bg-[#0f172a] rounded-xl border border-[#334155] shadow-inner">
          {icon}
        </div>
        <span className="text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-full">{trend}</span>
      </div>
      <div>
        <h3 className="text-slate-400 font-medium text-sm mb-1">{title}</h3>
        <div className="text-3xl font-bold text-white">{value}</div>
      </div>
    </div>
  );
}

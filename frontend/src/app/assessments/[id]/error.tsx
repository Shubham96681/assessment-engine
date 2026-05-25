"use client";

import Link from "next/link";

export default function AssessmentError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="max-w-lg mx-auto mt-16 px-4 text-center space-y-4">
      <h2 className="text-xl font-bold text-white">Could not load this assessment</h2>
      <p className="text-slate-400 text-sm break-words">{error.message}</p>
      <div className="flex gap-3 justify-center flex-wrap">
        <button
          type="button"
          onClick={() => reset()}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-xl"
        >
          Try again
        </button>
        <Link
          href="/assessments"
          className="bg-[#1e293b] border border-[#334155] text-white px-5 py-2 rounded-xl"
        >
          All assessments
        </Link>
      </div>
    </div>
  );
}

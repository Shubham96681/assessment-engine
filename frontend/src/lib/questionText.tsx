import React from "react";

const BOLD_MD = /\*\*([^*]+)\*\*/g;

/** Render question stems that use **OR** / **bold** markdown from the generator. */
export function QuestionContent({ text }: { text: string }) {
  if (!text) return null;
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(BOLD_MD)) {
    const idx = m.index ?? 0;
    if (idx > last) {
      nodes.push(<span key={key++}>{text.slice(last, idx)}</span>);
    }
    nodes.push(
      <strong key={key++} className="font-semibold text-white">
        {m[1]}
      </strong>,
    );
    last = idx + m[0].length;
  }
  if (last < text.length) {
    nodes.push(<span key={key++}>{text.slice(last)}</span>);
  }
  return <>{nodes.length ? nodes : text}</>;
}

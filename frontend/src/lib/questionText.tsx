"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  formatListLikeAnswer,
  segmentExamMath,
  segmentWithBoldParts,
  splitAnswerSubparts,
  type Segment,
} from "@/lib/mathDisplay";

type KatexModule = typeof import("katex");

function useKatex() {
  const [katex, setKatex] = useState<KatexModule["default"] | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void import("katex/dist/katex.min.css");
    void import("katex").then((mod) => {
      if (!cancelled) {
        setKatex(mod.default);
        setReady(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return { katex, ready };
}

function renderKatex(katex: KatexModule["default"], latex: string, display: boolean): string {
  try {
    return katex.renderToString(latex, {
      throwOnError: false,
      displayMode: display,
      strict: "ignore",
      trust: false,
      output: "html",
    });
  } catch {
    return latex.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
}

function MathBlock({
  latex,
  display,
  katex,
}: {
  latex: string;
  display: boolean;
  katex: KatexModule["default"];
}) {
  const html = useMemo(() => renderKatex(katex, latex, display), [katex, latex, display]);
  if (display) {
    return (
      <div
        className="exam-math-display my-2 w-full overflow-x-auto text-center"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }
  return (
    <span
      className="exam-math-inline inline-block align-middle mx-0.5"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function TextSpan({ value }: { value: string }) {
  return (
    <span className="whitespace-pre-wrap break-words [word-spacing:normal]">
      {value}
    </span>
  );
}

function PlainFallback({ text }: { text: string }) {
  return (
    <div className="exam-question-content leading-relaxed whitespace-pre-wrap break-words">
      {text}
    </div>
  );
}

function SegmentList({
  segments,
  katex,
}: {
  segments: Segment[];
  katex: KatexModule["default"];
}) {
  return (
    <>
      {segments.map((seg, i) =>
        seg.kind === "text" ? (
          <TextSpan key={i} value={seg.value} />
        ) : (
          <MathBlock key={i} latex={seg.latex} display={seg.display} katex={katex} />
        ),
      )}
    </>
  );
}

function ExamContent({
  text,
  className,
  katex,
  ready,
}: {
  text: string;
  className?: string;
  katex: KatexModule["default"] | null;
  ready: boolean;
}) {
  const plain = text || "";
  const parts = useMemo(() => {
    try {
      return segmentWithBoldParts(plain);
    } catch {
      return [{ bold: false, segments: [{ kind: "text" as const, value: plain }] }];
    }
  }, [plain]);

  if (!plain) return null;
  if (!ready || !katex || plain.length > 4000) {
    return <PlainFallback text={formatListLikeAnswer(plain)} />;
  }

  return (
    <div
      className={
        className
          ? `${className} exam-question-content leading-relaxed`
          : "exam-question-content leading-relaxed"
      }
    >
      {parts.map((part, i) =>
        part.bold ? (
          <strong key={i} className="font-semibold text-white">
            <SegmentList segments={part.segments} katex={katex} />
          </strong>
        ) : (
          <span key={i} className="inline">
            <SegmentList segments={part.segments} katex={katex} />
          </span>
        ),
      )}
    </div>
  );
}

/** Exam math (KaTeX) — client-only to avoid SSR/hydration blank page. */
export function QuestionContent({ text, className }: { text: string; className?: string }) {
  const { katex, ready } = useKatex();
  return <ExamContent text={text} className={className} katex={katex} ready={ready} />;
}

/** Model answers: block layout per (i)(ii)(iii) + KaTeX on each part. */
export function AnswerContent({ text, className }: { text: string; className?: string }) {
  const { katex, ready } = useKatex();
  const subparts = useMemo(() => splitAnswerSubparts(text), [text]);

  if (!text) return null;

  if (!ready || !katex) {
    return (
      <PlainFallback text={formatListLikeAnswer(text)} />
    );
  }

  if (subparts.length >= 2) {
    return (
      <div
        className={
          className
            ? `${className} answer-content`
            : "answer-content"
        }
      >
        {subparts.map((part, i) => (
          <div key={i} className="answer-part">
            {part.label ? (
              <span className="part-label">{part.label}</span>
            ) : null}
            <div className="part-body exam-question-content">
              <SegmentList
                segments={segmentExamMath(part.body)}
                katex={katex}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return <ExamContent text={text} className={className} katex={katex} ready={ready} />;
}

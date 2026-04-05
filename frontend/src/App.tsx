import { useCallback, useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL ?? "";

type ScoreBreakdown = {
  keyword_score: number;
  relevance_score: number;
  impact_score: number;
  clarity_score: number;
};

type FixItem = { fix: string; impact: number };

export type AnalyzeResponse = {
  summary: string;
  total_score: number;
  interview_probability: number;
  missing_skills: string[];
  weak_points: string[];
  improved_points: string[];
  fix_priority: FixItem[];
  score_breakdown: ScoreBreakdown;
  demo_mode?: boolean;
};

type HistoryItem = {
  id: number;
  user_id: string | null;
  total_score: number;
  created_at: string;
  summary: { missing_skills: string[]; total_score?: number };
};

function pctLabel(n: number) {
  return `${Math.round(n)}%`;
}

function ProgressBar({ value, accent }: { value: number; accent: string }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className="h-3 w-full rounded-full bg-elevio-border overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700 ease-out"
        style={{ width: `${v}%`, background: accent }}
      />
    </div>
  );
}

function fixTier(impact: number): "critical" | "medium" | "optional" {
  if (impact >= 16) return "critical";
  if (impact >= 11) return "medium";
  return "optional";
}

const tierStyle: Record<string, { dot: string; label: string }> = {
  critical: { dot: "bg-red-400", label: "High impact" },
  medium: { dot: "bg-amber-400", label: "Medium" },
  optional: { dot: "bg-emerald-400", label: "Nice to have" },
};

export default function App() {
  const [jobText, setJobText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [copyMsg, setCopyMsg] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const loadingBoxRef = useRef<HTMLDivElement | null>(null);
  const resultsBoxRef = useRef<HTMLDivElement | null>(null);

  type BreakdownKey = "keyword" | "relevance" | "impact" | "clarity";
  const [openBreakdownExplain, setOpenBreakdownExplain] = useState<BreakdownKey | null>(null);
  const breakdownExplainWrapRef = useRef<HTMLDivElement | null>(null);

  const breakdownExplain: Record<BreakdownKey, { title: string; body: string }> = {
    keyword: {
      title: "Keywords (40% max)",
      body:
        "Measures how many important skills or keywords from the job description appear in your resume.\n\nLow score → your resume may be missing key terms recruiters or ATS look for.\nHigh score → your resume likely matches those key terms recruiters or ATS look for.",
    },
    relevance: {
      title: "Relevance (30% max)",
      body:
        "Measures how well your experience matches the job role overall.\n\nHigh score → your past roles and responsibilities are closely aligned with what the job requires.\nLow score → your experience may not closely match the job’s responsibilities or domain.",
    },
    impact: {
      title: "Impact (20% max)",
      body:
        "Measures how much quantified results or achievements you show.\n\nHigh score → you clearly highlight measurable accomplishments (e.g., “cut processing time by 35%”).\nLow score → mostly vague or unquantified descriptions.",
    },
    clarity: {
      title: "Clarity (10% max)",
      body:
        "Measures how clear, concise, and easy to understand your resume is.\n\nHigh score → strong formatting, action verbs, and readable bullets.\nLow score → vague, wordy, or confusing bullets.",
    },
  };

  useEffect(() => {
    if (!loading) return;
    // Scroll to the loading box so users immediately see that the analysis started.
    loadingBoxRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [loading]);

  useEffect(() => {
    if (!result) return;
    // When results appear (especially on portrait screens), bring them into view.
    resultsBoxRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
   
  }, [result]);

  useEffect(() => {
    if (!openBreakdownExplain) return;
    function onDocMouseDown(e: MouseEvent) {
      const el = breakdownExplainWrapRef.current;
      if (!el) return;
      if (!el.contains(e.target as Node)) setOpenBreakdownExplain(null);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [openBreakdownExplain]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/history?limit=5`);
      if (!r.ok) return;
      const data = await r.json();
      setHistory(data.items ?? []);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  async function onAnalyze(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!file) {
      setError("Please choose a PDF resume.");
      return;
    }
    if (jobText.trim().length < 30) {
      setError("Paste a fuller job description (at least a few sentences).");
      return;
    }
    setLoading(true);
    setOpenBreakdownExplain(null);
    try {
      let userId = localStorage.getItem("user_id"); // check if exists
      if (!userId) {                               // if not, create
        userId = crypto.randomUUID();
        localStorage.setItem("user_id", userId);   // save for future
      }
      
      const fd = new FormData();
      fd.append("resume_pdf", file);
      fd.append("job_text", jobText);
      fd.append("user_id", userId);
      const r = await fetch(`${API}/api/analyze`, { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        // if (![400, 429, 502].includes(r.status)) {
        //   setError("Error! please contact yanteng.chen11@gmail.com");
        // } 
       
        if (r.status === 429) {
          setError("Too many requests. Please wait a moment and try again.");
        }
        else {
          setError(
            typeof data.detail === "string"
              ? data.detail
              : "Analysis failed."
          );
        }
        return;
      }
      setResult(data as AnalyzeResponse);

      await fetch(`${API}/api/upload_history`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          resume_text: "(stored from session)",
          job_text: jobText.slice(0, 2000),
          total_score: data.total_score,
          ai_output: { ...data, missing_skills: data.missing_skills },
        }),
      }).catch(() => {});
      fetchHistory();
    } catch {
      setError("Network error — is the API running on port 8000?");
    } finally {
      setLoading(false);
    }
  }

  async function copyImproved() {
    if (!result?.improved_points?.length) return;
    const text = result.improved_points.join("\n\n");
    await navigator.clipboard.writeText(text);
    setCopyMsg("Copied improved bullets");
    setTimeout(() => setCopyMsg(null), 2000);
  }

  return (
    <div className="min-h-screen bg-[#050508] text-zinc-100">
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-40">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-elevio-purple/30 blur-3xl" />
        <div className="absolute top-1/2 -left-40 h-80 w-80 rounded-full bg-elevio-blue/20 blur-3xl" />
      </div>

      <header className="relative border-b border-elevio-border/80 bg-elevio-dark/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4 md:px-6">
          <div className="flex items-center gap-3">
            <img
              src="/logo.png"
              alt="Elevio Career"
              className="h-11 w-auto object-contain"
            />
            <div className="leading-tight">
              <p className="text-lg font-semibold text-elevio-blue">Elevio Career</p>
              <p className="text-sm text-elevio-muted">Free Resume Analysis Tool for Job Matching</p>
            </div>
          </div>
          <p className="max-w-md text-sm text-elevio-muted">
            Upload your resume and a job description. Get match insight, missing skills, and
            ranked fixes.
          </p>
        </div>
      </header>

      <main
        id="analyze"
        className="relative mx-auto max-w-6xl scroll-mt-24 px-4 py-10 md:px-6"
      >
        <section className="grid gap-10 md:grid-cols-2">
          {/* LEFT SIDE OF THE PAGE */}
          <form
            onSubmit={onAnalyze}
            className="space-y-6 rounded-2xl border border-elevio-border bg-elevio-surface/60 p-6 shadow-xl shadow-black/40"
          >
            <h2 className="text-lg font-semibold text-white">Analyze</h2>
            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-300">
                Resume (PDF)
              </label>
              <input
                type="file"
                accept="application/pdf"
                className="block w-full text-sm text-zinc-300 file:mr-4 file:rounded-lg file:border-0 file:bg-elevio-blue/20 file:px-4 file:py-2 file:text-sm file:font-medium file:text-elevio-blue hover:file:bg-elevio-blue/30"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-300">
                Job description
              </label>
              <textarea
                value={jobText}
                onChange={(e) => setJobText(e.target.value)}
                rows={14}
                placeholder="Paste the full job posting here…"
                className="w-full resize-y rounded-xl border border-elevio-border bg-[#0c0c12] px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-elevio-blue/50 focus:outline-none focus:ring-2 focus:ring-elevio-blue/20"
              />
            </div>
            {error && (
              <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-gradient-to-r from-elevio-purple to-elevio-blue px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-elevio-blue/25 transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Analyzing…" : "Analyze"}
            </button>
            {result?.demo_mode && (
              <p className="text-xs text-amber-200/90">
                Demo mode: set <code className="text-zinc-400">GROQ_API_KEY</code> in{" "}
                <code className="text-zinc-400">backend/.env</code> for live AI.
              </p>
            )}
          </form>

          {/* RIGHT SIDE OF THE PAGE */}
          <div className="space-y-6">
            {!result && !loading && (
              <div className="rounded-2xl border border-dashed border-elevio-border/80 bg-elevio-surface/30 p-8 text-center text-elevio-muted">
                <p className="text-sm">
                  Results will show your match score, interview probability estimate, missing
                  skills, weak bullets, and prioritized fixes.
                </p>
              </div>
            )}

            {loading && (
              <div
                ref={loadingBoxRef}
                className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-elevio-border bg-elevio-surface/40 p-12"
              >
                <div className="h-10 w-10 animate-spin rounded-full border-2 border-elevio-blue border-t-transparent" />
                <p className="text-sm text-elevio-muted">Extracting PDF and running analysis…</p>
              </div>
            )}

            {result && (
              <div
                ref={resultsBoxRef}
                className="space-y-6 rounded-2xl border border-elevio-border bg-elevio-surface/60 p-6 shadow-xl"
              >
                <h2 className="text-lg font-semibold text-white">Results</h2>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-elevio-muted">Match score</span>
                    <span className="font-semibold text-elevio-blue">
                      {pctLabel(result.total_score)}
                    </span>
                  </div>
                  <ProgressBar value={result.total_score} accent="linear-gradient(90deg,#6B4EE6,#2F7CF6)" />
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-elevio-muted">Interview probability (estimate)</span>
                    <span className="font-semibold text-pink-300">
                      {pctLabel(result.interview_probability)}
                    </span>
                  </div>
                  <ProgressBar value={result.interview_probability} accent="linear-gradient(90deg,#E94FA8,#2F7CF6)" />
                </div>

                <div className="grid gap-3 rounded-xl border border-elevio-border/80 bg-[#0c0c12] p-4 text-xs md:grid-cols-1">
                  <div ref={breakdownExplainWrapRef}>
                    <p className="text-elevio-muted mb-1">Score breakdown</p>
                    <ul className="space-y-1 text-zinc-300">
                      <li className="relative flex items-start justify-between gap-3">
                        <span>
                          {breakdownExplain.keyword.title}: {result.score_breakdown.keyword_score}
                        </span>
                        <button
                          type="button"
                          aria-label="Explain keyword score"
                          onClick={() =>
                            setOpenBreakdownExplain((v) => (v === "keyword" ? null : "keyword"))
                          }
                          className="rounded-md p-1.5 text-zinc-400 hover:bg-white/5 hover:text-white"
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              d="M10.5 18C14.6421 18 18 14.6421 18 10.5C18 6.35786 14.6421 3 10.5 3C6.35786 3 3 6.35786 3 10.5C3 14.6421 6.35786 18 10.5 18Z"
                              stroke="currentColor"
                              strokeWidth="2"
                            />
                            <path
                              d="M21 21L16.65 16.65"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                            />
                          </svg>
                        </button>
                        {openBreakdownExplain === "keyword" && (
                          <div className="absolute right-0 z-20 mt-8 w-72 max-w-[90vw] rounded-xl border border-elevio-border bg-elevio-surface/95 p-3 text-[11px] text-zinc-200 shadow-xl">
                            <p className="mb-1 font-medium text-white">Keywords (40% max): {result.score_breakdown.keyword_score}</p>
                            {breakdownExplain.keyword.body.split("\n").map((line, idx) => {
  const trimmed = line.trim();

  if (!trimmed) {
    return <p key={idx} className="h-1">&nbsp;</p>;
  }

  return (
    <p key={idx} className="leading-relaxed">
      {trimmed
        .replace("Low score →", "__LOW__")
        .replace("High score →", "__HIGH__")
        .split(/(__LOW__|__HIGH__)/g)
        .map((part, i) => {
          if (part === "__LOW__") return <strong key={i}>Low score →</strong>;
          if (part === "__HIGH__") return <strong key={i}>High score →</strong>;
          return <span key={i}>{part}</span>;
        })}
    </p>
  );
})}
                          </div>
                        )}
                      </li>

                      <li className="relative flex items-start justify-between gap-3">
                        <span>
                          {breakdownExplain.relevance.title}: {result.score_breakdown.relevance_score}
                        </span>
                        <button
                          type="button"
                          aria-label="Explain relevance score"
                          onClick={() =>
                            setOpenBreakdownExplain((v) => (v === "relevance" ? null : "relevance"))
                          }
                          className="rounded-md p-1.5 text-zinc-400 hover:bg-white/5 hover:text-white"
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              d="M10.5 18C14.6421 18 18 14.6421 18 10.5C18 6.35786 14.6421 3 10.5 3C6.35786 3 3 6.35786 3 10.5C3 14.6421 6.35786 18 10.5 18Z"
                              stroke="currentColor"
                              strokeWidth="2"
                            />
                            <path
                              d="M21 21L16.65 16.65"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                            />
                          </svg>
                        </button>
                        {openBreakdownExplain === "relevance" && (
                          <div className="absolute right-0 z-20 mt-8 w-72 max-w-[90vw] rounded-xl border border-elevio-border bg-elevio-surface/95 p-3 text-[11px] text-zinc-200 shadow-xl">
                            <p className="mb-1 font-medium text-white">Relevance (30% max): {result.score_breakdown.relevance_score}</p>
                            {breakdownExplain.relevance.body.split("\n").map((line, idx) => {
  const trimmed = line.trim();

  if (!trimmed) {
    return <p key={idx} className="h-1">&nbsp;</p>;
  }

  return (
    <p key={idx} className="leading-relaxed">
      {trimmed
        .replace("Low score →", "__LOW__")
        .replace("High score →", "__HIGH__")
        .split(/(__LOW__|__HIGH__)/g)
        .map((part, i) => {
          if (part === "__LOW__") return <strong key={i}>Low score →</strong>;
          if (part === "__HIGH__") return <strong key={i}>High score →</strong>;
          return <span key={i}>{part}</span>;
        })}
    </p>
  );
})}
                          </div>
                        )}
                      </li>

                      <li className="relative flex items-start justify-between gap-3">
                        <span>
                          {breakdownExplain.impact.title}: {result.score_breakdown.impact_score}
                        </span>
                        <button
                          type="button"
                          aria-label="Explain impact score"
                          onClick={() =>
                            setOpenBreakdownExplain((v) => (v === "impact" ? null : "impact"))
                          }
                          className="rounded-md p-1.5 text-zinc-400 hover:bg-white/5 hover:text-white"
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              d="M10.5 18C14.6421 18 18 14.6421 18 10.5C18 6.35786 14.6421 3 10.5 3C6.35786 3 3 6.35786 3 10.5C3 14.6421 6.35786 18 10.5 18Z"
                              stroke="currentColor"
                              strokeWidth="2"
                            />
                            <path
                              d="M21 21L16.65 16.65"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                            />
                          </svg>
                        </button>
                        {openBreakdownExplain === "impact" && (
                          <div className="absolute right-0 z-20 mt-8 w-72 max-w-[90vw] rounded-xl border border-elevio-border bg-elevio-surface/95 p-3 text-[11px] text-zinc-200 shadow-xl">
                            <p className="mb-1 font-medium text-white">Impact (20% max): {result.score_breakdown.impact_score}</p>
                            {breakdownExplain.impact.body.split("\n").map((line, idx) => {
  const trimmed = line.trim();

  if (!trimmed) {
    return <p key={idx} className="h-1">&nbsp;</p>;
  }

  return (
    <p key={idx} className="leading-relaxed">
      {trimmed
        .replace("Low score →", "__LOW__")
        .replace("High score →", "__HIGH__")
        .split(/(__LOW__|__HIGH__)/g)
        .map((part, i) => {
          if (part === "__LOW__") return <strong key={i}>Low score →</strong>;
          if (part === "__HIGH__") return <strong key={i}>High score →</strong>;
          return <span key={i}>{part}</span>;
        })}
    </p>
  );
})}
                          </div>
                        )}
                      </li>

                      <li className="relative flex items-start justify-between gap-3">
                        <span>
                          {breakdownExplain.clarity.title}: {result.score_breakdown.clarity_score}
                        </span>
                        <button
                          type="button"
                          aria-label="Explain clarity score"
                          onClick={() =>
                            setOpenBreakdownExplain((v) => (v === "clarity" ? null : "clarity"))
                          }
                          className="rounded-md p-1.5 text-zinc-400 hover:bg-white/5 hover:text-white"
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              d="M10.5 18C14.6421 18 18 14.6421 18 10.5C18 6.35786 14.6421 3 10.5 3C6.35786 3 3 6.35786 3 10.5C3 14.6421 6.35786 18 10.5 18Z"
                              stroke="currentColor"
                              strokeWidth="2"
                            />
                            <path
                              d="M21 21L16.65 16.65"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                            />
                          </svg>
                        </button>
                        {openBreakdownExplain === "clarity" && (
                          <div className="absolute right-0 z-20 mt-8 w-72 max-w-[90vw] rounded-xl border border-elevio-border bg-elevio-surface/95 p-3 text-[11px] text-zinc-200 shadow-xl">
                            <p className="mb-1 font-medium text-white">Clarity (10% max): {result.score_breakdown.clarity_score}</p>
                            {breakdownExplain.clarity.body.split("\n").map((line, idx) => {
  const trimmed = line.trim();

  if (!trimmed) {
    return <p key={idx} className="h-1">&nbsp;</p>;
  }

  return (
    <p key={idx} className="leading-relaxed">
      {trimmed
        .replace("Low score →", "__LOW__")
        .replace("High score →", "__HIGH__")
        .split(/(__LOW__|__HIGH__)/g)
        .map((part, i) => {
          if (part === "__LOW__") return <strong key={i}>Low score →</strong>;
          if (part === "__HIGH__") return <strong key={i}>High score →</strong>;
          return <span key={i}>{part}</span>;
        })}
    </p>
  );
})}
                          </div>
                        )}
                      </li>
                    </ul>
                  </div>
                </div>

                <div>
                  <h3 className="mb-2 text-sm font-medium text-zinc-200">Summary</h3>
                  <p className="text-sm text-zinc-400">{result.summary}</p>
                </div>

              
                <div>
                  <h3 className="mb-2 text-sm font-medium text-zinc-200">Missing skills</h3>
                  <ul className="list-inside list-disc space-y-1 text-sm text-zinc-400">
                    {result.missing_skills.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>

                

                <div>
                  <h3 className="mb-2 text-sm font-medium text-zinc-200">Weak points</h3>
                  <ul className="space-y-2 text-sm text-zinc-400">
                    {result.weak_points.map((s) => (
                      <li
                        key={s}
                        className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2"
                      >
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-medium text-zinc-200">Fix priority</h3>
                  </div>
                  <ol className="space-y-3">
                    {result.fix_priority.map((f, i) => {
                      const tier = fixTier(f.impact);
                      const st = tierStyle[tier];
                      return (
                        <li
                          key={`${f.fix}-${i}`}
                          className="flex gap-3 rounded-xl border border-elevio-border/80 bg-[#0c0c12] p-3"
                        >
                          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-zinc-300">
                            {i + 1}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm text-zinc-200">{f.fix}</p>
                            <p className="mt-1 flex items-center gap-2 text-xs text-elevio-muted">
                              <span className={`inline-block h-2 w-2 rounded-full ${st.dot}`} />
                              {st.label} · +{f.impact} pts est.
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                </div>

                <div>
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-medium text-zinc-200">Improved bullet ideas</h3>
                    <button
                      type="button"
                      onClick={copyImproved}
                      className="rounded-lg border border-elevio-border px-3 py-1.5 text-xs font-medium text-elevio-blue hover:bg-elevio-blue/10"
                    >
                      Copy all
                    </button>
                  </div>
                  {copyMsg && <p className="mb-2 text-xs text-emerald-400">{copyMsg}</p>}
                  <ul className="space-y-2 text-sm text-zinc-300">
                    {result.improved_points.map((s) => (
                      <li
                        key={s}
                        className="rounded-lg border border-elevio-blue/25 bg-elevio-blue/5 px-3 py-2"
                      >
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {history.length > 0 && (
              <div className="rounded-2xl border border-elevio-border bg-elevio-surface/40 p-6">
                <h3 className="mb-3 text-sm font-semibold text-zinc-200">Recent analyses</h3>
                <ul className="space-y-2 text-xs text-elevio-muted">
                  {history.map((h) => (
                    <li
                      key={h.id}
                      className="flex justify-between gap-2 border-b border-elevio-border/50 pb-2 last:border-0"
                    >
                      <span>
                        Score {h.total_score?.toFixed?.(0) ?? h.total_score} ·{" "}
                        {(h.summary.missing_skills ?? []).slice(0, 2).join(", ") || "—"}
                      </span>
                      <span className="shrink-0 text-zinc-500">
                        {new Date(h.created_at).toLocaleString()}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      </main>

      {/* SEO copy stays in the DOM (still indexable). Collapsed by default so the analyzer stays primary. */}
      <section
        aria-label="About Elevio Career — free resume analysis and job matching"
        className="mx-auto max-w-4xl border-t border-elevio-border/40 px-4 pb-6 pt-4 text-elevio-muted md:px-6"
      >
        <details className="group rounded-2xl border border-elevio-border/70 bg-elevio-surface/40">
          <summary className="cursor-pointer list-none px-4 py-4 md:px-5 md:py-4 [&::-webkit-details-marker]:hidden">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-white">About Elevio Career</p>
                <p className="mt-1 text-xs text-elevio-muted md:text-sm">
                  Free resume analysis tool for job matching, ATS keywords, and resume-to-job fit.
                  <span className="text-elevio-muted/80"> Tap to read more.</span>
                </p>
              </div>
              <span
                className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-elevio-border/80 bg-[#0c0c12] text-xs text-zinc-300 transition-transform group-open:rotate-180"
                aria-hidden
              >
                ▼
              </span>
            </div>
          </summary>
          <div className="border-t border-elevio-border/50 px-4 pb-5 pt-2 md:px-5">
            <h1 className="mb-4 text-2xl font-bold text-white md:text-3xl">
              Free Resume Analysis Tool for Job Matching
            </h1>

            <p className="mb-4">
              Elevio Career is an AI-powered resume analysis tool that helps you compare your resume
              with any job description. Instantly discover missing skills, improve keyword relevance,
              and increase your chances of passing ATS systems.
            </p>

            <h2 className="mb-2 mt-6 text-xl font-semibold text-zinc-100">How it works</h2>
            <ul className="ml-6 list-disc space-y-1">
              <li>Upload your resume (PDF)</li>
              <li>Paste a job description</li>
              <li>Get AI-powered insights and improvement suggestions</li>
              <li>Free to use with up to 3 analyses per day</li>
            </ul>

            <h2 className="mb-2 mt-6 text-xl font-semibold text-zinc-100">Why use Elevio Career?</h2>
            <ul className="ml-6 list-disc space-y-1">
              <li>ATS-friendly resume optimization</li>
              <li>Real job-to-resume matching</li>
              <li>No signup required</li>
              <li>It is Free</li>
            </ul>
            <p className="mt-5 text-xs text-elevio-muted">
              <a href="#analyze" className="text-elevio-blue hover:underline">
                Jump to upload &amp; analyze
              </a>
            </p>
          </div>
        </details>
      </section>

      <footer className="relative border-t border-elevio-border/60 py-6 text-center text-xs text-zinc-600">
        Elevio Career · Resume × Job fit analysis
      </footer>
    </div>
  );
}

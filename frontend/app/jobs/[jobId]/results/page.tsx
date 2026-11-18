"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
type Clip = {
  id: string; title: string; start: number; end: number; duration: number;
  score: number; grade: "S" | "A" | "B" | "C"; breakdown: Record<string, number>;
  reason: string; hashtags: string[]; preview_url: string; download_url: string; srt_url: string;
};
const CRITERIA: Record<string, string> = {
  hook_strength: "Hook", emotional_impact: "Emotion", value_or_insight: "Value",
  standalone_clarity: "Clarity", pacing_energy: "Pacing", trend_shareability: "Shareability",
};
const GRADE_STYLE: Record<string, string> = {
  S: "border-lime/30 bg-lime/10 text-lime", A: "border-violet/30 bg-violet/10 text-violet-200",
  B: "border-sky-300/30 bg-sky-300/10 text-sky-200", C: "border-orange-300/30 bg-orange-300/10 text-orange-200",
};
function timecode(seconds: number) {
  const whole = Math.floor(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export default function ResultsPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const [clips, setClips] = useState<Clip[]>([]);
  const [grade, setGrade] = useState("All grades");
  const [sort, setSort] = useState("score");
  const [error, setError] = useState("");
  useEffect(() => {
    fetch(`${API_URL}/api/jobs/${jobId}/clips`, { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Could not load clips.");
        setClips(data);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load clips."));
  }, [jobId]);

  const filtered = useMemo(() => clips
    .filter((clip) => grade === "All grades" || clip.grade === grade)
    .sort((a, b) => sort === "length" ? b.duration - a.duration : b.score - a.score), [clips, grade, sort]);

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-5 py-6 sm:px-8">
      <header className="flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 text-sm font-bold"><span className="grid h-8 w-8 place-items-center rounded-lg bg-lime text-ink">C</span>ClipForge</Link>
        <Link href={`/jobs/${jobId}`} className="text-xs text-white/45 hover:text-white">← Job status</Link>
      </header>
      <section className="pb-10 pt-12">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-semibold tracking-[.2em] text-violet">YOUR CLIPS · {clips.length} MOMENTS</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">The highlights.</h1>
            <p className="mt-2 text-white/50">Ranked by their potential to stop the scroll.</p>
          </div>
          {clips.length > 0 && <a href={`${API_URL}/api/jobs/${jobId}/download-all`} className="inline-flex w-fit items-center gap-2 rounded-xl bg-lime px-5 py-3 text-sm font-semibold text-ink hover:bg-[#d5ff9b]">↓ Download all (ZIP)</a>}
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <select aria-label="Filter by grade" value={grade} onChange={(event) => setGrade(event.target.value)} className="rounded-lg border border-white/10 bg-panel px-3 py-2 text-sm">
            {["All grades", "S", "A", "B", "C"].map((value) => <option key={value}>{value}</option>)}
          </select>
          <select aria-label="Sort clips" value={sort} onChange={(event) => setSort(event.target.value)} className="rounded-lg border border-white/10 bg-panel px-3 py-2 text-sm">
            <option value="score">Highest score</option><option value="length">Longest first</option>
          </select>
        </div>
      </section>
      {error && <p role="alert" className="rounded-xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-200">{error}</p>}
      {!error && clips.length === 0 && <p className="text-sm text-white/50">No clips are available yet. Check the job status or try again.</p>}
      <section className="grid gap-5 pb-16 sm:grid-cols-2 xl:grid-cols-3">
        {filtered.map((clip, index) => (
          <article key={clip.id} className="overflow-hidden rounded-2xl border border-white/10 bg-panel">
            <div className="relative mx-auto aspect-[9/16] max-h-[460px] bg-black sm:max-h-[520px]">
              <video controls playsInline preload="metadata" src={`${API_URL}${clip.preview_url}`} className="h-full w-full object-contain" />
              <span className="absolute left-3 top-3 rounded-full border border-white/15 bg-black/65 px-2.5 py-1 text-[11px] text-white/80">#{String(index + 1).padStart(2, "0")}</span>
              <span className={`absolute right-3 top-3 rounded-full border px-2.5 py-1 text-xs font-bold ${GRADE_STYLE[clip.grade]}`}>{clip.grade} · {Math.round(clip.score)}</span>
            </div>
            <div className="p-5">
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-lg font-semibold leading-snug">{clip.title}</h2>
                <span className="shrink-0 rounded-md bg-white/[.06] px-2 py-1 text-[11px] text-white/55">{timecode(clip.start)}–{timecode(clip.end)}</span>
              </div>
              <div className="mt-4 space-y-2.5">
                {Object.entries(CRITERIA).map(([key, label]) => {
                  const value = clip.breakdown[key] ?? 0;
                  return <div key={key} className="flex items-center gap-2 text-[10px] text-white/45">
                    <span className="w-[76px]">{label}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-violet" style={{ width: `${value}%` }} /></div>
                    <span className="w-6 text-right">{value}</span>
                  </div>;
                })}
              </div>
              <p className="mt-4 border-l-2 border-lime/70 pl-3 text-xs leading-5 text-white/65">{clip.reason}</p>
              <p className="mt-3 text-xs leading-5 text-violet-200/75">{clip.hashtags.map((tag) => tag.startsWith("#") ? tag : `#${tag}`).join(" ")}</p>
              <div className="mt-5 grid grid-cols-2 gap-2">
                <a href={`${API_URL}${clip.download_url}`} className="rounded-lg bg-white px-3 py-2.5 text-center text-xs font-semibold text-ink hover:bg-lime">↓ Download MP4</a>
                <a href={`${API_URL}${clip.srt_url}`} className="rounded-lg border border-white/10 px-3 py-2.5 text-center text-xs font-semibold text-white/80 hover:bg-white/5">↓ Download SRT</a>
              </div>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}

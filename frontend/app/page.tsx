"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [numClips, setNumClips] = useState(8);
  const [minLength, setMinLength] = useState(20);
  const [maxLength, setMaxLength] = useState(60);
  const [style, setStyle] = useState("bold");
  const [language, setLanguage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url, num_clips: numClips, min_len: minLength, max_len: maxLength,
          caption_style: style, language: language || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail = data.detail;
        throw new Error(typeof detail === "string" ? detail : "Check the YouTube link and clip settings.");
      }
      router.push(`/jobs/${data.job_id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not connect to ClipForge. Is the backend running?");
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col px-5 pb-12 pt-6 sm:px-8">
      <header className="flex items-center justify-between">
        <a href="/" className="flex items-center gap-2 text-sm font-bold tracking-tight">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-lime text-ink">C</span>
          ClipForge
        </a>
        <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-white/50">AI VIDEO STUDIO</span>
      </header>

      <section className="mx-auto grid w-full flex-1 items-center gap-12 py-16 lg:grid-cols-[1.05fr_.95fr] lg:py-20">
        <div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet/30 bg-violet/10 px-3 py-1.5 text-xs text-violet-200">
            <span className="h-1.5 w-1.5 rounded-full bg-lime" /> YOUR LONG-FORM VIDEO, REFORGED
          </div>
          <h1 className="max-w-2xl text-5xl font-semibold leading-[1.04] tracking-[-.055em] sm:text-7xl">
            The best parts deserve <span className="text-violet">their own</span> spotlight.
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-white/55 sm:text-lg">
            Find the moments people will actually watch. ClipForge scores, crops, and captions your video into ready-to-post shorts.
          </p>
          <div className="mt-9 flex flex-wrap gap-3 text-xs text-white/55">
            {["Smart moment detection", "9:16 auto-crop", "Burned-in captions"].map((item) => (
              <span key={item} className="rounded-full border border-white/10 bg-white/[.03] px-3 py-2">✦ {item}</span>
            ))}
          </div>
        </div>

        <form onSubmit={submit} className="glass rounded-3xl border border-white/10 p-5 shadow-2xl shadow-violet/5 sm:p-7">
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h2 className="text-xl font-semibold">Create your clips</h2>
              <p className="mt-1 text-sm text-white/45">Paste a public YouTube video link to get started.</p>
            </div>
            <span className="rounded-lg bg-white/[.06] px-2.5 py-1.5 text-xs text-white/55">01 / INPUT</span>
          </div>
          <label htmlFor="video-url" className="mb-2 block text-xs font-medium text-white/65">YOUTUBE VIDEO URL</label>
          <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 px-4 focus-within:border-violet/70">
            <span className="text-red-400">▶</span>
            <input id="video-url" type="url" required value={url} onChange={(event) => setUrl(event.target.value)}
              placeholder="https://youtube.com/watch?v=..." className="h-12 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-white/25" />
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4">
            <label className="text-xs text-white/60">NUMBER OF CLIPS
              <select value={numClips} onChange={(event) => setNumClips(Number(event.target.value))}
                className="mt-2 block h-11 w-full rounded-xl border border-white/10 bg-[#151823] px-3 text-sm text-white outline-none focus:border-violet">
                {[4, 6, 8, 10, 12, 16, 20].map((value) => <option key={value} value={value}>{value} clips</option>)}
              </select>
            </label>
            <label className="text-xs text-white/60">CAPTION STYLE
              <select value={style} onChange={(event) => setStyle(event.target.value)}
                className="mt-2 block h-11 w-full rounded-xl border border-white/10 bg-[#151823] px-3 text-sm text-white outline-none focus:border-violet">
                <option value="bold">Bold pop</option><option value="classic">Classic</option><option value="minimal">Minimal</option>
              </select>
            </label>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-4">
            <label className="text-xs text-white/60">MIN CLIP LENGTH
              <select value={minLength} onChange={(event) => setMinLength(Number(event.target.value))}
                className="mt-2 block h-11 w-full rounded-xl border border-white/10 bg-[#151823] px-3 text-sm text-white outline-none focus:border-violet">
                {[10, 15, 20, 25, 30, 40].filter((value) => value < maxLength).map((value) => <option key={value} value={value}>{value} sec</option>)}
              </select>
            </label>
            <label className="text-xs text-white/60">MAX CLIP LENGTH
              <select value={maxLength} onChange={(event) => setMaxLength(Number(event.target.value))}
                className="mt-2 block h-11 w-full rounded-xl border border-white/10 bg-[#151823] px-3 text-sm text-white outline-none focus:border-violet">
                {[30, 40, 45, 60, 75, 90, 120].filter((value) => value > minLength).map((value) => <option key={value} value={value}>{value} sec</option>)}
              </select>
            </label>
          </div>

          <details className="group mt-5">
            <summary className="cursor-pointer list-none text-xs text-white/50 hover:text-white/80">
              <span className="mr-2 inline-block transition group-open:rotate-90">›</span>More options
            </summary>
            <label className="mt-4 block text-xs text-white/60">LANGUAGE
              <input value={language} onChange={(event) => setLanguage(event.target.value)}
                placeholder="Auto-detect (or enter a code, e.g. en)" className="mt-2 h-11 w-full rounded-xl border border-white/10 bg-black/20 px-3 text-sm text-white outline-none placeholder:text-white/25 focus:border-violet" />
            </label>
          </details>

          {error && <p role="alert" className="mt-5 rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">{error}</p>}
          <button type="submit" disabled={submitting}
            className="mt-6 flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-lime font-semibold text-ink transition hover:bg-[#d5ff9b] disabled:cursor-wait disabled:opacity-60">
            {submitting ? "Starting your job…" : "Generate clips"} <span aria-hidden>↗</span>
          </button>
          <p className="mt-3 text-center text-[11px] leading-5 text-white/35">Only process videos you have permission to use.</p>
        </form>
      </section>
      <footer className="flex justify-between border-t border-white/[.07] pt-5 text-[11px] text-white/35">
        <span>ClipForge © 2025</span><span>Cut the scroll. Keep the story.</span>
      </footer>
    </main>
  );
}

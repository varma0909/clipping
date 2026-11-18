"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const STEPS = ["Downloading", "Transcribing", "Finding best moments", "Grading", "Cropping to 9:16", "Adding captions", "Done"];
type JobStatus = { status: string; progress: number; step: string; error: string | null };

export default function JobPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const response = await fetch(`${API_URL}/api/jobs/${jobId}`, { cache: "no-store" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Could not load this job.");
        if (!active) return;
        setJob(data);
        if (data.status === "done" || data.status === "failed") return;
        timer = setTimeout(poll, 2000);
      } catch (reason) {
        if (!active) return;
        setError(reason instanceof TypeError ? "Backend connection lost. Retrying status updates…" :
          reason instanceof Error ? reason.message : "Could not connect to the backend.");
        timer = setTimeout(poll, 4000);
      }
    };
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId]);

  const activeStep = job?.status === "done" ? STEPS.length - 1 : Math.max(
    0, STEPS.findIndex((step) => (job?.step ?? "").startsWith(step)),
  );
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col px-5 py-6 sm:px-8">
      <Link href="/" className="flex w-fit items-center gap-2 text-sm font-bold"><span className="grid h-8 w-8 place-items-center rounded-lg bg-lime text-ink">C</span>ClipForge</Link>
      <section className="my-auto py-16">
        <p className="text-xs font-semibold tracking-[.2em] text-violet">CLIP JOB · {jobId.slice(0, 8).toUpperCase()}</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
          {job?.status === "done" ? "Your clips are ready." : job?.status === "failed" ? "We hit a snag." : "Finding your moments."}
        </h1>
        <p className="mt-3 text-white/50">{job?.status === "failed" ? job.error : error || "This can take a few minutes depending on video length."}</p>

        {job?.status !== "failed" && (
          <div className="mt-10 rounded-3xl border border-white/10 bg-panel p-5 sm:p-8">
            <div className="mb-3 flex justify-between text-xs text-white/45"><span>{job?.step || "Connecting…"}</span><span>{job?.progress ?? 0}%</span></div>
            <div className="h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-lime transition-all duration-700" style={{ width: `${job?.progress ?? 3}%` }} /></div>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {STEPS.map((step, index) => {
                const complete = job?.status === "done" || index < activeStep;
                const current = job?.status !== "done" && index === activeStep;
                return <div key={step} className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm ${current ? "bg-violet/10 text-violet-100" : "text-white/40"}`}>
                  <span className={`grid h-6 w-6 place-items-center rounded-full text-xs ${complete ? "bg-lime text-ink" : current ? "border border-violet text-violet" : "border border-white/15"}`}>{complete ? "✓" : index + 1}</span>
                  {step}{current && job?.status === "processing" && <span className="ml-auto h-1.5 w-1.5 animate-pulse rounded-full bg-lime" />}
                </div>;
              })}
            </div>
          </div>
        )}
        {job?.status === "done" && <Link href={`/jobs/${jobId}/results`} className="mt-7 inline-flex rounded-xl bg-lime px-6 py-3 font-semibold text-ink hover:bg-[#d5ff9b]">View your clips →</Link>}
        {job?.status === "failed" && <div className="mt-7 flex flex-wrap gap-3">
          <Link href="/" className="inline-flex rounded-xl border border-white/15 px-6 py-3 font-semibold hover:bg-white/5">Try another video</Link>
          <Link href={`/jobs/${jobId}/results`} className="inline-flex rounded-xl bg-lime px-6 py-3 font-semibold text-ink hover:bg-[#d5ff9b]">View any finished clips →</Link>
        </div>}
      </section>
    </main>
  );
}

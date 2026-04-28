import React, { useEffect, useMemo, useRef, useState } from "react";
import "@/App.css";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import {
  ScanLine,
  Cpu,
  FileCheck2,
  Download,
  ExternalLink,
  Loader2,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUS_STEPS = [
  "Analyzing job description...",
  "Rewriting resume with Claude...",
  "Converting to LaTeX...",
  "Compiling PDF on Overleaf...",
  "Done!",
];

const fadeUp = {
  initial: { y: 20, opacity: 0 },
  animate: { y: 0, opacity: 1 },
  transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] },
};

function Nav({ onCta }) {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 bg-black/60 backdrop-blur-xl border-b border-white/5"
      data-testid="app-nav"
    >
      <div className="flex items-center justify-between h-20 max-w-7xl mx-auto px-6 md:px-12">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="font-heading text-lg font-semibold tracking-tight text-white">
            ATS Resume Tailor
          </span>
        </div>
        <button
          onClick={onCta}
          data-testid="nav-generate-btn"
          className="px-5 py-2.5 bg-white text-black font-medium rounded-full hover:bg-zinc-200 active:scale-[0.98] transition-all text-sm"
        >
          Generate Resume
        </button>
      </div>
    </nav>
  );
}

function Hero({ onCta }) {
  return (
    <section className="relative pt-40 pb-20 md:pt-48 md:pb-32 overflow-hidden">
      <div className="absolute inset-0 hero-radial pointer-events-none" />
      <div className="absolute inset-0 bg-grid mask-radial pointer-events-none" />
      <div className="relative max-w-7xl mx-auto px-6 md:px-12 flex flex-col items-center text-center">
        <motion.div
          {...fadeUp}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-xs font-medium tracking-[0.15em] uppercase mb-8"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Powered by Claude Sonnet 4.5
        </motion.div>

        <motion.h1
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.1 }}
          className="font-heading text-5xl md:text-7xl font-semibold tracking-tighter text-white leading-[0.95] mb-6 max-w-4xl"
        >
          Beat the ATS.
          <br />
          <span className="bg-gradient-to-br from-white via-indigo-200 to-indigo-500 bg-clip-text text-transparent">
            Land the interview.
          </span>
        </motion.h1>

        <motion.p
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.2 }}
          className="text-lg md:text-xl text-zinc-400 max-w-2xl mb-10 leading-relaxed"
        >
          Paste your resume and a job description. Get a perfectly tailored,
          keyword-optimized, recruiter-ready PDF in under a minute.
        </motion.p>

        <motion.button
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.3 }}
          onClick={onCta}
          data-testid="hero-cta-btn"
          className="group relative px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-base rounded-full shadow-[0_0_40px_rgba(79,70,229,0.3)] hover:shadow-[0_0_70px_rgba(79,70,229,0.55)] transition-all hover:-translate-y-0.5 active:scale-[0.98] flex items-center gap-2"
        >
          Tailor My Resume
          <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
        </motion.button>
      </div>
    </section>
  );
}

const STEPS = [
  {
    icon: ScanLine,
    title: "Paste your resume & the JD",
    description:
      "Drop your current resume and the target job description into two fields. No accounts, no uploads.",
  },
  {
    icon: Cpu,
    title: "Claude rewrites & optimizes",
    description:
      "Our Sonnet 4.5 pipeline extracts facts, maps keywords, and reconstructs every bullet for ATS impact.",
  },
  {
    icon: FileCheck2,
    title: "Download your tailored PDF",
    description:
      "We render it through Overleaf with a clean, recruiter-friendly LaTeX template. Ready to send.",
  },
];

function HowItWorks() {
  return (
    <section className="py-24 md:py-32 relative z-10">
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div className="flex flex-col items-start md:items-center md:text-center mb-16 gap-3">
          <span className="text-xs font-semibold uppercase tracking-[0.25em] text-indigo-400">
            How it works
          </span>
          <h2 className="font-heading text-3xl md:text-5xl font-semibold tracking-tighter text-white max-w-2xl">
            Three steps to a resume built for the bot — and the human.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {STEPS.map((step, idx) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.title}
                initial={{ y: 30, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.7, delay: idx * 0.1, ease: [0.16, 1, 0.3, 1] }}
                className="group relative p-8 rounded-3xl bg-[#0A0A0A] border border-white/5 hover:border-indigo-500/30 transition-all duration-500 overflow-hidden"
                data-testid={`how-it-works-card-${idx + 1}`}
              >
                <div className="absolute -top-24 -right-24 w-48 h-48 rounded-full bg-indigo-600/0 group-hover:bg-indigo-600/10 blur-3xl transition-all duration-700" />
                <div className="flex items-center justify-between mb-6">
                  <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-110 group-hover:bg-indigo-500/20 transition-all duration-500">
                    <Icon className="w-6 h-6" strokeWidth={1.5} />
                  </div>
                  <span className="font-mono text-xs text-zinc-600">
                    0{idx + 1}
                  </span>
                </div>
                <h3 className="text-xl font-heading font-medium text-white mb-3">
                  {step.title}
                </h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  {step.description}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Generator({ formRef }) {
  const [jobDescription, setJobDescription] = useState("");
  const [currentResume, setCurrentResume] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusIndex, setStatusIndex] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const statusTimerRef = useRef(null);

  const canSubmit = useMemo(
    () => jobDescription.trim().length > 0 && currentResume.trim().length > 0 && !loading,
    [jobDescription, currentResume, loading]
  );

  useEffect(() => {
    return () => {
      if (statusTimerRef.current) clearInterval(statusTimerRef.current);
    };
  }, []);

  const startStatusAdvance = () => {
    setStatusIndex(0);
    let idx = 0;
    // Advance one step every ~6s, stop before the final "Done!" message
    statusTimerRef.current = setInterval(() => {
      idx = Math.min(idx + 1, STATUS_STEPS.length - 2);
      setStatusIndex(idx);
    }, 6000);
  };

  const stopStatusAdvance = () => {
    if (statusTimerRef.current) {
      clearInterval(statusTimerRef.current);
      statusTimerRef.current = null;
    }
  };

  const handleGenerate = async () => {
    setError(null);
    setResult(null);
    setLoading(true);
    startStatusAdvance();

    try {
      const { data } = await axios.post(`${API}/generate`, {
        jobDescription,
        currentResume,
      });
      stopStatusAdvance();

      if (data.status === "success") {
        setStatusIndex(STATUS_STEPS.length - 1);
        setResult(data);
      } else {
        setError(data.message || "Something went wrong. Please try again.");
      }
    } catch (err) {
      stopStatusAdvance();
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Request failed.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result?.pdfBase64) return;
    const bytes = Uint8Array.from(atob(result.pdfBase64), (c) => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "tailored_resume.pdf";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleRetry = () => {
    setError(null);
    setResult(null);
    setStatusIndex(0);
  };

  return (
    <section
      ref={formRef}
      id="generator"
      className="py-24 md:py-32 relative z-10 scroll-mt-24"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div className="flex flex-col items-start md:items-center md:text-center mb-12 gap-3">
          <span className="text-xs font-semibold uppercase tracking-[0.25em] text-indigo-400">
            The Generator
          </span>
          <h2 className="font-heading text-3xl md:text-5xl font-semibold tracking-tighter text-white max-w-2xl">
            Paste. Generate. Download.
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
          <div className="flex flex-col gap-3">
            <label
              htmlFor="jd"
              className="text-sm font-medium text-zinc-300 flex items-center justify-between"
            >
              <span>Job Description</span>
              <span className="font-mono text-xs text-zinc-600">
                {jobDescription.length} chars
              </span>
            </label>
            <textarea
              id="jd"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here..."
              data-testid="job-description-input"
              className="w-full min-h-[320px] p-6 bg-[#0A0A0A] border border-white/10 rounded-2xl text-zinc-200 font-mono text-sm leading-relaxed focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all resize-y placeholder:text-zinc-700"
            />
          </div>

          <div className="flex flex-col gap-3">
            <label
              htmlFor="resume"
              className="text-sm font-medium text-zinc-300 flex items-center justify-between"
            >
              <span>Your Current Resume</span>
              <span className="font-mono text-xs text-zinc-600">
                {currentResume.length} chars
              </span>
            </label>
            <textarea
              id="resume"
              value={currentResume}
              onChange={(e) => setCurrentResume(e.target.value)}
              placeholder="Paste your current resume text here..."
              data-testid="resume-input"
              className="w-full min-h-[320px] p-6 bg-[#0A0A0A] border border-white/10 rounded-2xl text-zinc-200 font-mono text-sm leading-relaxed focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all resize-y placeholder:text-zinc-700"
            />
          </div>
        </div>

        <div className="mt-12 flex flex-col items-center justify-center">
          <button
            onClick={handleGenerate}
            disabled={!canSubmit}
            data-testid="generate-button"
            className="relative px-10 py-5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-lg rounded-full shadow-[0_0_40px_rgba(79,70,229,0.3)] hover:shadow-[0_0_70px_rgba(79,70,229,0.55)] transition-all hover:-translate-y-0.5 active:scale-[0.98] flex items-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                Generate ATS Resume
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>

          <div
            className="mt-6 h-6 text-sm font-mono text-indigo-400 flex items-center gap-2"
            data-testid="status-text"
          >
            <AnimatePresence mode="wait">
              {(loading || result) && (
                <motion.span
                  key={statusIndex}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25 }}
                  className="flex items-center gap-2"
                >
                  {statusIndex < STATUS_STEPS.length - 1 && (
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                  )}
                  {STATUS_STEPS[statusIndex]}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </div>

        <AnimatePresence>
          {result && (
            <motion.div
              key="result"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="mt-12 w-full max-w-2xl mx-auto p-8 md:p-12 bg-[#0F0F11] border border-indigo-500/20 rounded-3xl relative overflow-hidden flex flex-col items-center text-center"
              data-testid="result-card"
            >
              <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-64 h-64 rounded-full bg-indigo-600/20 blur-3xl pointer-events-none" />
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-6 relative">
                <CheckCircle2 className="w-8 h-8" strokeWidth={1.5} />
              </div>
              <h3 className="text-2xl font-heading font-medium text-white mb-2">
                Your tailored resume is ready.
              </h3>
              <p className="text-zinc-400 mb-8">
                Download the PDF or open the project in Overleaf to edit further.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
                <button
                  onClick={handleDownload}
                  data-testid="download-pdf-button"
                  className="px-8 py-4 bg-white text-black font-medium rounded-full hover:bg-zinc-200 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download PDF
                </button>
                <a
                  href={result.projectUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="overleaf-link"
                  className="px-8 py-4 bg-transparent border border-white/20 text-white font-medium rounded-full hover:bg-white/5 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                >
                  Open project in Overleaf
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.div
              key="error"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.4 }}
              className="mt-12 w-full max-w-lg mx-auto p-6 bg-red-500/10 border border-red-500/20 rounded-2xl flex flex-col items-center text-center"
              data-testid="error-card"
            >
              <AlertCircle className="w-8 h-8 text-red-400 mb-3" strokeWidth={1.5} />
              <div className="text-red-400 font-medium mb-1">
                Something went wrong
              </div>
              <div className="text-sm text-red-300/80" data-testid="error-message">
                {error}
              </div>
              <button
                onClick={handleRetry}
                data-testid="retry-button"
                className="mt-4 px-6 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded-full text-sm font-medium transition-colors"
              >
                Try again
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="py-12 border-t border-white/5 mt-20">
      <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="text-sm text-zinc-600">
          (c) {new Date().getFullYear()} ATS Resume Tailor.
        </div>
        <div className="text-sm text-zinc-600">
          Your resume and JD are processed in-memory and never stored.
        </div>
      </div>
    </footer>
  );
}

export default function App() {
  const formRef = useRef(null);

  const scrollToForm = () => {
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="App min-h-screen text-white antialiased">
      <Nav onCta={scrollToForm} />
      <main className="relative">
        <Hero onCta={scrollToForm} />
        <HowItWorks />
        <Generator formRef={formRef} />
      </main>
      <Footer />
    </div>
  );
}

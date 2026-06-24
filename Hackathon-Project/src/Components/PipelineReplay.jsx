import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

function buildStages(plan, meta, filterSummary) {
  const intent = (plan?.intent || meta?.intent || "research").toUpperCase();
  const keywords = (plan?.keywords || []).slice(0, 4).join(", ") || "—";
  const totalRaw = meta?.total_raw ?? "?";
  const totalRanked = meta?.total_ranked ?? "?";
  const removed = filterSummary
    ? (filterSummary.total_input || 0) - (filterSummary.total_output || 0)
    : 0;
  const timing = meta?.timing_ms || {};
  const sourcesUsed = (meta?.sources_used || []).join(", ") || "all sources";

  return [
    {
      icon: "🧠",
      label: "Understand",
      title: "Question Analysis",
      detail: `Detected intent: ${intent} · Keywords: ${keywords}`,
      ms: timing.plan_ms,
      color: "#818cf8",
    },
    {
      icon: "🔍",
      label: "Fetch",
      title: "Source Retrieval",
      detail: `Queried ${sourcesUsed} · Retrieved ${totalRaw} raw results`,
      ms: timing.fetch_ms,
      color: "#38bdf8",
    },
    {
      icon: "🧹",
      label: "Filter",
      title: "Noise Removal",
      detail: `Removed ${removed} duplicates & irrelevant results · ${filterSummary?.total_output ?? "?"} clean sources kept`,
      ms: timing.filter_ms,
      color: "#fb923c",
    },
    {
      icon: "📊",
      label: "Score",
      title: "Relevance Ranking",
      detail: `Ranked by semantic similarity, authority & engagement · Top ${totalRanked} selected`,
      ms: timing.score_ms,
      color: "#fbbf24",
    },
    {
      icon: "⚖️",
      label: "Debate",
      title: "Conflict Detection",
      detail: "Analyzed sources for contradictions · Identified pro/con perspectives",
      ms: timing.debate_ms,
      color: "#f472b6",
    },
    {
      icon: "🗺️",
      label: "Graph",
      title: "Knowledge Mapping",
      detail: "Extracted entities & relationships · Built concept network",
      ms: timing.graph_ms,
      color: "#34d399",
    },
    {
      icon: "✨",
      label: "Synthesize",
      title: "AI Synthesis",
      detail: `Generated ${intent.toLowerCase()}-mode response with inline citations`,
      ms: timing.llm_ms,
      color: "#fb923c",
    },
  ];
}

export default function PipelineReplay({ plan, meta, filterSummary }) {
  const [open, setOpen] = useState(false);
  const [activeStep, setActiveStep] = useState(-1);

  const stages = buildStages(plan, meta, filterSummary);

  useEffect(() => {
    if (!open) { setActiveStep(-1); return; }
    let i = 0;
    const tick = () => {
      setActiveStep(i);
      i++;
      if (i < stages.length) setTimeout(tick, 320);
    };
    setTimeout(tick, 100);
  }, [open]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.6 }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-sm font-medium transition-all"
        style={{ color: open ? "#fb923c" : "#64748b" }}
        onMouseEnter={(e) => (e.currentTarget.style.color = "#fb923c")}
        onMouseLeave={(e) => (e.currentTarget.style.color = open ? "#fb923c" : "#64748b")}
      >
        <span>{open ? "▲" : "▼"}</span>
        How did we research this?
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div
              className="mt-4 rounded-3xl p-6"
              style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <p className="text-xs text-slate-600 mb-5 uppercase tracking-widest">7-Stage Intelligence Pipeline</p>

              <div className="relative">
                {/* Vertical line */}
                <div
                  className="absolute left-5 top-0 w-px"
                  style={{
                    height: "100%",
                    background: "rgba(255,255,255,0.06)",
                  }}
                />

                <div className="space-y-1">
                  {stages.map((stage, i) => {
                    const done = i <= activeStep;
                    const active = i === activeStep;
                    return (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -8 }}
                        animate={done ? { opacity: 1, x: 0 } : { opacity: 0.2, x: 0 }}
                        transition={{ duration: 0.25 }}
                        className="flex items-start gap-4 py-2.5 pl-0"
                      >
                        {/* Icon */}
                        <div
                          className="relative z-10 w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0 transition-all duration-300"
                          style={{
                            background: done ? stage.color + "18" : "rgba(255,255,255,0.03)",
                            border: `1px solid ${done ? stage.color + "44" : "rgba(255,255,255,0.06)"}`,
                            boxShadow: active ? `0 0 16px ${stage.color}33` : "none",
                          }}
                        >
                          {stage.icon}
                        </div>

                        {/* Text */}
                        <div className="flex-1 min-w-0 pt-1">
                          <div className="flex items-center gap-2">
                            <span
                              className="text-sm font-semibold"
                              style={{ color: done ? "white" : "rgba(255,255,255,0.25)" }}
                            >
                              {stage.title}
                            </span>
                            {stage.ms != null && done && (
                              <span
                                className="text-[10px] px-1.5 py-0.5 rounded-full font-mono"
                                style={{
                                  background: stage.color + "12",
                                  color: stage.color + "aa",
                                }}
                              >
                                {stage.ms}ms
                              </span>
                            )}
                          </div>
                          {done && (
                            <motion.p
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              className="text-xs text-slate-500 mt-0.5 leading-5"
                            >
                              {stage.detail}
                            </motion.p>
                          )}
                        </div>

                        {/* Step label */}
                        <span
                          className="text-[10px] font-mono pt-2 flex-shrink-0"
                          style={{ color: done ? stage.color + "88" : "rgba(255,255,255,0.1)" }}
                        >
                          {i + 1}/{stages.length}
                        </span>
                      </motion.div>
                    );
                  })}
                </div>
              </div>

              {activeStep >= stages.length - 1 && meta?.timing_ms?.total_ms && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="mt-5 pt-4 border-t border-white/5 flex items-center justify-between text-xs"
                >
                  <span className="text-slate-500">Total pipeline time</span>
                  <span className="font-mono text-orange-400 font-semibold">
                    {(meta.timing_ms.total_ms / 1000).toFixed(1)}s
                  </span>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const STAGES = [
  { label: "Understanding your question",     icon: "🧠", ms: 0    },
  { label: "Searching across sources",         icon: "🔍", ms: 900  },
  { label: "Filtering & removing duplicates",  icon: "🧹", ms: 2000 },
  { label: "Ranking by relevance & authority", icon: "📊", ms: 3000 },
  { label: "Analyzing debate perspectives",    icon: "⚖️", ms: 4000 },
  { label: "Building knowledge map",           icon: "🗺️", ms: 5200 },
  { label: "Synthesizing insights with AI",    icon: "✨", ms: 6200 },
];

export default function PipelineProgress({ active }) {
  const [done, setDone] = useState([]);
  const [current, setCurrent] = useState(-1);

  useEffect(() => {
    if (!active) {
      setDone([]);
      setCurrent(-1);
      return;
    }

    const timers = STAGES.map((stage, i) =>
      setTimeout(() => {
        setCurrent(i);
        setDone((prev) => [...prev, i - 1]);
      }, stage.ms)
    );

    return () => timers.forEach(clearTimeout);
  }, [active]);

  return (
    <div className="mt-16 max-w-sm mx-auto space-y-4">
      {STAGES.map((stage, i) => {
        const isDone    = done.includes(i);
        const isActive  = current === i;
        const isPending = !isDone && !isActive;

        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: isPending ? 0.25 : 1, x: 0 }}
            transition={{ delay: i * 0.05, duration: 0.4 }}
            className="flex items-center gap-3"
          >
            <span className="text-xl w-7 text-center">{stage.icon}</span>

            <span
              className={`text-sm font-medium flex-1 ${
                isDone   ? "text-orange-300" :
                isActive ? "text-white"      :
                           "text-slate-600"
              }`}
            >
              {stage.label}
            </span>

            <div className="w-5 flex items-center justify-center">
              {isDone && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="text-green-400 text-sm font-bold"
                >
                  ✓
                </motion.span>
              )}
              {isActive && (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                  className="w-3.5 h-3.5 border-2 border-orange-400 border-t-transparent rounded-full"
                />
              )}
            </div>
          </motion.div>
        );
      })}

      <motion.div
        className="mt-6 h-1 rounded-full overflow-hidden"
        style={{ background: "rgba(255,255,255,0.06)" }}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: "linear-gradient(90deg, #c2410c, #fb923c)" }}
          animate={{ width: `${((done.length + (current >= 0 ? 1 : 0)) / STAGES.length) * 100}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </motion.div>
    </div>
  );
}

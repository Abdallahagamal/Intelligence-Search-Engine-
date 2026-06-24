import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

function tokenize(text) {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9 ]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 3)
  );
}

function bestSource(sentence, sources) {
  const sentWords = tokenize(sentence);
  let bestIdx = -1;
  let bestScore = 0;

  sources.forEach((src, i) => {
    const srcWords = tokenize(`${src.title} ${src.snippet || ""}`);
    let score = 0;
    sentWords.forEach((w) => { if (srcWords.has(w)) score++; });
    if (score > bestScore) { bestScore = score; bestIdx = i; }
  });

  return bestScore >= 2 ? bestIdx : -1;
}

function splitSentences(text) {
  return text
    .replace(/([.!?])\s+/g, "$1\x00")
    .split("\x00")
    .map((s) => s.trim())
    .filter(Boolean);
}

function Tooltip({ source, index, onClose }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.95 }}
      transition={{ duration: 0.15 }}
      className="absolute z-50 w-72 rounded-2xl p-4 shadow-2xl"
      style={{
        bottom: "calc(100% + 8px)",
        left: "50%",
        transform: "translateX(-50%)",
        background: "rgba(12,8,4,0.97)",
        border: "1px solid rgba(249,115,22,0.25)",
        boxShadow: "0 16px 48px rgba(0,0,0,0.8), 0 0 24px rgba(249,115,22,0.08)",
      }}
    >
      <div className="flex items-start gap-3">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5"
          style={{ background: "rgba(249,115,22,0.2)", color: "#fb923c" }}
        >
          {index + 1}
        </div>
        <div className="min-w-0">
          <p className="text-white text-xs font-semibold leading-5 line-clamp-2">{source.title}</p>
          {source.snippet && (
            <p className="text-slate-400 text-xs mt-1 leading-4 line-clamp-3">{source.snippet}</p>
          )}
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs text-orange-400 font-medium">{source.platform}</span>
            {source.link && (
              <a
                href={source.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-slate-500 hover:text-slate-300 underline underline-offset-2 truncate"
                onClick={(e) => e.stopPropagation()}
              >
                Open source →
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Arrow */}
      <div
        className="absolute w-3 h-3 rotate-45"
        style={{
          bottom: -6,
          left: "50%",
          transform: "translateX(-50%) rotate(45deg)",
          background: "rgba(12,8,4,0.97)",
          borderRight: "1px solid rgba(249,115,22,0.25)",
          borderBottom: "1px solid rgba(249,115,22,0.25)",
        }}
      />
    </motion.div>
  );
}

export default function CitedText({ text, sources }) {
  const [activeIdx, setActiveIdx] = useState(null);

  if (!text || !sources?.length) return null;

  const sentences = splitSentences(text);
  const cited = sentences.map((s) => ({ text: s, srcIdx: bestSource(s, sources) }));

  const usedIndices = [...new Set(cited.map((c) => c.srcIdx).filter((i) => i >= 0))];
  const indexMap = {};
  usedIndices.forEach((srcIdx, n) => { indexMap[srcIdx] = n; });

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-3xl p-7"
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      <h2 className="text-xl font-bold text-white mb-5">✍️ AI Synthesis</h2>

      <p className="text-slate-200 text-base leading-8">
        {cited.map((chunk, i) => {
          const num = chunk.srcIdx >= 0 ? indexMap[chunk.srcIdx] : -1;
          return (
            <span key={i}>
              {chunk.text}
              {num >= 0 && (
                <span className="relative inline-block mx-0.5">
                  <button
                    className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold align-super cursor-pointer transition-colors"
                    style={{
                      background: activeIdx === chunk.srcIdx
                        ? "rgba(249,115,22,0.6)"
                        : "rgba(249,115,22,0.18)",
                      color: "#fb923c",
                      border: "1px solid rgba(249,115,22,0.3)",
                      lineHeight: 1,
                    }}
                    onClick={() =>
                      setActiveIdx(activeIdx === chunk.srcIdx ? null : chunk.srcIdx)
                    }
                  >
                    {num + 1}
                  </button>
                  <AnimatePresence>
                    {activeIdx === chunk.srcIdx && (
                      <Tooltip
                        source={sources[chunk.srcIdx]}
                        index={num}
                        onClose={() => setActiveIdx(null)}
                      />
                    )}
                  </AnimatePresence>
                </span>
              )}{" "}
            </span>
          );
        })}
      </p>

      {usedIndices.length > 0 && (
        <div className="mt-6 pt-5 border-t border-white/5 flex flex-wrap gap-2">
          {usedIndices.map((srcIdx, n) => {
            const src = sources[srcIdx];
            return (
              <a
                key={srcIdx}
                href={src.link || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs transition-all"
                style={{
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  color: "#94a3b8",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(249,115,22,0.08)";
                  e.currentTarget.style.borderColor = "rgba(249,115,22,0.2)";
                  e.currentTarget.style.color = "#fb923c";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                  e.currentTarget.style.color = "#94a3b8";
                }}
              >
                <span
                  className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold"
                  style={{ background: "rgba(249,115,22,0.18)", color: "#fb923c" }}
                >
                  {n + 1}
                </span>
                <span className="truncate max-w-[180px]">{src.title}</span>
              </a>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}

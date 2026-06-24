import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const PERSONAS = [
  {
    id: "academic",
    name: "The Researcher",
    emoji: "🎓",
    role: "Academic & Encyclopedic",
    platforms: ["arxiv", "wikipedia"],
    color: "#818cf8",
    bg: "rgba(129,140,248,0.06)",
    border: "rgba(129,140,248,0.18)",
    voicePrefix: "According to the literature,",
  },
  {
    id: "developer",
    name: "The Engineer",
    emoji: "💻",
    role: "Code & Practice",
    platforms: ["github", "stackoverflow"],
    color: "#34d399",
    bg: "rgba(52,211,153,0.06)",
    border: "rgba(52,211,153,0.18)",
    voicePrefix: "In practice,",
  },
  {
    id: "reporter",
    name: "The Reporter",
    emoji: "📰",
    role: "News & Community",
    platforms: ["news", "reddit"],
    color: "#fb923c",
    bg: "rgba(249,115,22,0.06)",
    border: "rgba(249,115,22,0.18)",
    voicePrefix: "The current conversation says,",
  },
];

function getGroupSources(sources, platforms) {
  return sources.filter((s) =>
    platforms.includes((s.platform || "").toLowerCase())
  );
}

function buildVoice(persona, groupSources) {
  if (!groupSources.length) return null;
  const top = groupSources[0];
  const snippet = top.snippet || top.title || "";
  const clipped = snippet.length > 220 ? snippet.slice(0, 220).replace(/\s+\S*$/, "") + "…" : snippet;
  return `${persona.voicePrefix} ${clipped}`;
}

function PersonaCard({ persona, sources, index }) {
  const [expanded, setExpanded] = useState(false);
  const groupSources = getGroupSources(sources, persona.platforms);
  const voice = buildVoice(persona, groupSources);

  if (!groupSources.length) return null;

  const avgConf = Math.round(
    groupSources.reduce((sum, s) => sum + (parseFloat(s.confidence) || 0), 0) / groupSources.length
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.12, duration: 0.4 }}
      className="rounded-lg sm:rounded-2xl overflow-hidden cursor-pointer select-none"
      style={{
        background: persona.bg,
        border: `1px solid ${persona.border}`,
        boxShadow: `0 4px 24px rgba(0,0,0,0.3)`,
      }}
      onClick={() => setExpanded((v) => !v)}
    >
      {/* Header */}
      <div className="p-3 sm:p-5">
        <div className="flex items-start justify-between gap-2 sm:gap-3">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
            <div
              className="w-8 h-8 sm:w-11 sm:h-11 rounded-lg sm:rounded-2xl flex items-center justify-center text-lg sm:text-2xl flex-shrink-0"
              style={{ background: persona.color + "18" }}
            >
              {persona.emoji}
            </div>
            <div className="min-w-0">
              <p className="text-white font-bold text-xs sm:text-sm truncate">{persona.name}</p>
              <p className="text-[10px] sm:text-xs mt-0.5 truncate" style={{ color: persona.color + "bb" }}>
                {persona.role}
              </p>
            </div>
          </div>

          <div className="flex flex-col items-end gap-1 flex-shrink-0">
            <span
              className="text-[10px] sm:text-xs font-semibold px-2 py-0.5 rounded-full"
              style={{ background: persona.color + "18", color: persona.color }}
            >
              {groupSources.length} source{groupSources.length !== 1 ? "s" : ""}
            </span>
            <span className="text-[9px] sm:text-[10px] text-slate-500 whitespace-nowrap">{avgConf}% conf</span>
          </div>
        </div>

        {voice && (
          <blockquote
            className="mt-2 sm:mt-4 text-xs sm:text-sm leading-5 sm:leading-6 italic line-clamp-2 sm:line-clamp-none"
            style={{ color: "rgba(255,255,255,0.6)", borderLeft: `2px solid ${persona.color}44`, paddingLeft: 12 }}
          >
            "{voice}"
          </blockquote>
        )}

        <div className="mt-2 sm:mt-3 flex items-center gap-2 text-[9px] sm:text-xs text-slate-600 flex-wrap">
          <span>From:</span>
          {persona.platforms.map((p) => (
            <span key={p} className="capitalize text-slate-500 whitespace-nowrap">{p}</span>
          ))}
          <span className="ml-auto flex-shrink-0" style={{ color: persona.color + "88" }}>
            {expanded ? "▲ Less" : "▼ See"}
          </span>
        </div>
      </div>

      {/* Expanded source list */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div
              className="px-3 sm:px-5 pb-3 sm:pb-5 space-y-2 sm:space-y-2.5 border-t"
              style={{ borderColor: persona.border }}
              onClick={(e) => e.stopPropagation()}
            >
              {groupSources.map((src, i) => (
                <a
                  key={i}
                  href={src.link || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-2 sm:gap-3 p-2 sm:p-3 rounded-lg sm:rounded-xl transition-all group"
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.05)",
                    marginTop: i === 0 ? 8 : 0,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.03)")}
                >
                  <div
                    className="w-4 h-4 sm:w-5 sm:h-5 rounded-full flex items-center justify-center text-[8px] sm:text-[9px] font-bold flex-shrink-0 mt-0.5"
                    style={{ background: persona.color + "22", color: persona.color }}
                  >
                    {i + 1}
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] sm:text-xs font-medium leading-4 sm:leading-5 line-clamp-2 group-hover:text-orange-300 transition-colors">
                      {src.title}
                    </p>
                    <p className="text-slate-600 text-[9px] sm:text-[10px] mt-0.5">{src.confidence} confidence</p>
                  </div>
                </a>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function PersonaCards({ sources }) {
  if (!sources?.length) return null;

  const activePersonas = PERSONAS.filter(
    (p) => getGroupSources(sources, p.platforms).length > 0
  );

  if (activePersonas.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="px-2 sm:px-0"
    >
      <h2 className="text-lg sm:text-xl font-bold text-white mb-3 sm:mb-6">🎭 Three Perspectives</h2>
      <p className="text-xs sm:text-sm text-slate-500 mb-4 sm:mb-6 -mt-1 sm:-mt-3">
        The same question, seen through different lenses. Click any card to see sources.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-5">
        {activePersonas.map((persona, i) => (
          <PersonaCard
            key={persona.id}
            persona={persona}
            sources={sources}
            index={i}
          />
        ))}
      </div>
    </motion.div>
  );
}

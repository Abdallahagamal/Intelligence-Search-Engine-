import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

function IntensityBar({ value }) {
  const pct   = Math.min(100, Math.max(0, (value || 0) * 10));
  const color  = pct >= 70 ? "#ef4444" : pct >= 40 ? "#fb923c" : "#22c55e";
  const label  = pct >= 70 ? "High Tension" : pct >= 40 ? "Moderate" : "Low Conflict";

  return (
    <div className="flex items-center gap-3 mb-6">
      <span className="text-xs text-slate-500 w-24 shrink-0">Debate intensity</span>
      <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>
      <span className="text-xs font-medium w-24 text-right" style={{ color }}>
        {label}
      </span>
    </div>
  );
}

function Side({ side, color, label, accentBg, borderColor }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex-1 rounded-2xl p-5"
      style={{ background: accentBg, border: `1px solid ${borderColor}` }}
    >
      <div
        className="inline-block text-xs font-bold px-3 py-1 rounded-full mb-3"
        style={{ background: color + "22", color }}
      >
        {label}
      </div>

      <p className="text-sm text-slate-300 leading-6 mb-4">
        {side?.argument || "No argument extracted."}
      </p>

      {(side?.key_claims || []).length > 0 && (
        <ul className="space-y-2">
          {side.key_claims.map((claim, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
              <span style={{ color }} className="mt-0.5 shrink-0">▸</span>
              {claim}
            </li>
          ))}
        </ul>
      )}
    </motion.div>
  );
}

export default function DebateCard({ debate }) {
  const [tab, setTab] = useState("sides");

  if (!debate || debate.debate_type === "no_debate") return null;

  const agreements    = debate.agreement_points    || [];
  const disagreements = debate.disagreement_points || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="rounded-3xl p-7"
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.07)",
        boxShadow: "0 8px 40px rgba(0,0,0,0.4)",
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-bold text-white">⚖️ Debate Analysis</h2>
        <span
          className="text-xs px-3 py-1 rounded-full capitalize"
          style={{ background: "rgba(249,115,22,0.12)", color: "#fb923c" }}
        >
          {(debate.debate_type || "").replace(/_/g, " ")}
        </span>
      </div>

      <p className="text-sm text-slate-500 mb-5">
        Sources disagree on this topic. Here's both sides.
      </p>

      <IntensityBar value={debate.debate_intensity} />

      <div className="flex gap-2 mb-6">
        {["sides", "common ground"].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-200"
            style={
              tab === t
                ? { background: "rgba(249,115,22,0.18)", color: "#fb923c", border: "1px solid rgba(249,115,22,0.3)" }
                : { background: "rgba(255,255,255,0.04)", color: "#64748b", border: "1px solid rgba(255,255,255,0.06)" }
            }
          >
            {t === "sides" ? "Two Perspectives" : "Common Ground"}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {tab === "sides" ? (
          <motion.div
            key="sides"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex gap-4 flex-col md:flex-row"
          >
            <Side
              side={debate.side_a}
              label="Supporting"
              color="#22c55e"
              accentBg="rgba(34,197,94,0.04)"
              borderColor="rgba(34,197,94,0.12)"
            />
            <div className="flex items-center justify-center text-slate-600 font-bold text-lg shrink-0">
              VS
            </div>
            <Side
              side={debate.side_b}
              label="Opposing"
              color="#ef4444"
              accentBg="rgba(239,68,68,0.04)"
              borderColor="rgba(239,68,68,0.12)"
            />
          </motion.div>
        ) : (
          <motion.div
            key="ground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="grid md:grid-cols-2 gap-4"
          >
            <div
              className="rounded-2xl p-5"
              style={{ background: "rgba(34,197,94,0.04)", border: "1px solid rgba(34,197,94,0.1)" }}
            >
              <p className="text-xs font-bold text-green-400 mb-3">✓ Points of Agreement</p>
              {agreements.length ? (
                <ul className="space-y-2">
                  {agreements.map((p, i) => (
                    <li key={i} className="text-xs text-slate-400 flex gap-2">
                      <span className="text-green-500 shrink-0">•</span>{p}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-xs text-slate-600">None found</p>}
            </div>

            <div
              className="rounded-2xl p-5"
              style={{ background: "rgba(239,68,68,0.04)", border: "1px solid rgba(239,68,68,0.1)" }}
            >
              <p className="text-xs font-bold text-red-400 mb-3">✗ Points of Disagreement</p>
              {disagreements.length ? (
                <ul className="space-y-2">
                  {disagreements.map((p, i) => (
                    <li key={i} className="text-xs text-slate-400 flex gap-2">
                      <span className="text-red-500 shrink-0">•</span>{p}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-xs text-slate-600">None found</p>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

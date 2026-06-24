import { motion } from "framer-motion";

const CX = 120, CY = 100, R = 80;
const TOTAL = Math.PI * R;
const NEEDLE_LEN = R - 16;
const FULL_ARC = `M ${CX - R} ${CY} A ${R} ${R} 0 0 0 ${CX + R} ${CY}`;

function arcEndpoint(pct) {
  const angle = Math.PI * (1 - pct / 100);
  return {
    x: CX + R * Math.cos(angle),
    y: CY - R * Math.sin(angle),
  };
}

function needleEndpoint(pct) {
  const angle = Math.PI * (1 - pct / 100);
  return {
    x: CX + NEEDLE_LEN * Math.cos(angle),
    y: CY - NEEDLE_LEN * Math.sin(angle),
  };
}

export default function ConsensusMeter({ debate }) {
  if (!debate) return null;

  const intensity  = Math.min(1, debate.debate_intensity || 0);
  const consensus  = Math.round((1 - intensity) * 100);
  const color      = consensus >= 66 ? "#22c55e" : consensus >= 33 ? "#fb923c" : "#ef4444";
  const label      = consensus >= 66 ? "High Consensus" : consensus >= 33 ? "Mixed Views" : "Highly Contested";
  const description =
    consensus >= 66
      ? "Sources largely agree. The information is well-established across platforms."
      : consensus >= 33
      ? "Sources hold different perspectives. Consider multiple viewpoints before concluding."
      : "Sources strongly disagree. This is an actively debated topic with no clear consensus.";

  const needle = needleEndpoint(consensus);
  const dashOffset = TOTAL * (1 - consensus / 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="rounded-3xl p-7"
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.07)",
        boxShadow: "0 8px 40px rgba(0,0,0,0.4)",
      }}
    >
      <h2 className="text-xl font-bold text-white mb-6">📊 Source Consensus</h2>

      <div className="flex flex-col md:flex-row items-center gap-8">
        <svg width="240" height="130" viewBox="0 0 240 130" className="flex-shrink-0">
          <path
            d={FULL_ARC}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="12"
            strokeLinecap="round"
          />

          <motion.path
            d={FULL_ARC}
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={TOTAL}
            initial={{ strokeDashoffset: TOTAL }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.4, ease: "easeOut" }}
          />

          {[0, 25, 50, 75, 100].map((tick) => {
            const a = Math.PI * (1 - tick / 100);
            return (
              <line
                key={tick}
                x1={CX + (R + 4) * Math.cos(a)}
                y1={CY - (R + 4) * Math.sin(a)}
                x2={CX + (R + 14) * Math.cos(a)}
                y2={CY - (R + 14) * Math.sin(a)}
                stroke="rgba(255,255,255,0.18)"
                strokeWidth="1.5"
              />
            );
          })}

          <motion.line
            x1={CX} y1={CY}
            initial={{ x2: CX - NEEDLE_LEN, y2: CY }}
            animate={{ x2: needle.x, y2: needle.y }}
            transition={{ duration: 1.4, ease: "easeOut" }}
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          <circle cx={CX} cy={CY} r="6" fill="white" opacity="0.9" />

          <motion.text
            x={CX} y={CY + 28}
            textAnchor="middle"
            fill={color}
            fontSize="26"
            fontWeight="bold"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
          >
            {consensus}%
          </motion.text>

          <motion.text
            x={CX} y={CY + 46}
            textAnchor="middle"
            fill="rgba(255,255,255,0.35)"
            fontSize="11"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
          >
            {label}
          </motion.text>
        </svg>

        <div className="flex-1 space-y-5">
          <p className="text-sm text-slate-300 leading-6">{description}</p>

          <div className="space-y-2">
            {[
              { label: "High Consensus",    color: "#22c55e", range: "66–100%" },
              { label: "Mixed Views",        color: "#fb923c", range: "33–65%"  },
              { label: "Highly Contested",   color: "#ef4444", range: "0–32%"   },
            ].map((row) => (
              <div key={row.label} className="flex items-center gap-2 text-xs text-slate-500">
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: row.color }} />
                <span>{row.label}</span>
                <span className="ml-auto">{row.range}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

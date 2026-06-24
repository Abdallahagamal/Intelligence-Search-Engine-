import { useState } from "react";
import { FaCopy, FaCheck } from "react-icons/fa";
import {
  FaReddit,
  FaGithub,
  FaWikipediaW,
  FaStackOverflow,
  FaNewspaper,
} from "react-icons/fa";
import { SiArxiv } from "react-icons/si";

const PLATFORM_META = {
  reddit: { color: "#FF4500", icon: FaReddit },
  github: { color: "#181717", icon: FaGithub },
  wikipedia: { color: "#a7a9ac", icon: FaWikipediaW },
  stackoverflow: { color: "#F48024", icon: FaStackOverflow },
  news: { color: "#fb923c", icon: FaNewspaper },
  arxiv: { color: "#B31B1B", icon: SiArxiv },
};

export default function SourceCard({
  platform,
  title,
  confidence,
  link,
  time,
  index = 0,
}) {
  const [copied, setCopied] = useState(false);

  const meta =
    PLATFORM_META[platform.toLowerCase().replace(/\s/g, "")] ||
    { color: "#f97316", icon: FaNewspaper };

  const accent = meta.color;
  const Icon = meta.icon;

  return (
    <article
      className="
        source-card-in
        relative
        rounded-r-2xl
        rounded-bl-2xl
        px-6
        pt-8
        pb-5
        transition-all
        duration-300
        hover:-translate-y-1
      "
      style={{
        background: "rgba(255,255,255,0.04)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: `1px solid ${accent}66`,
        borderLeft: `6px solid ${accent}`,
        boxShadow: "0 8px 40px rgba(0,0,0,0.5), 0 0 30px rgba(249,115,22,0.06)",
        animationDelay: `${index * 70}ms`,
      }}
    >

      {/* Platform Tab — white pill, icon + name in brand color */}
      <div
        className="
          absolute
          -top-[13px]
          -left-px
          z-10
          flex
          items-center
          gap-1.5
          px-3
          pt-[5px]
          pb-1
          rounded-tr-md
          rounded-br-md
          text-[10.5px]
          font-semibold
          uppercase
          tracking-wider
          whitespace-nowrap
          shadow-md
        "
        style={{
          background: "#ffffff",
          color: accent,
        }}
      >
        <Icon size={12} style={{ color: accent }} />
        {platform}
      </div>

      {/* Eyebrow — mono meta line */}
      <div
        className="relative text-[11.5px] text-slate-500 mb-2.5 mt-1"
        style={{ fontFamily: '"Space Grotesk", monospace' }}
      >
        {platform.toLowerCase()}.com · <span className="text-slate-300">{time}</span>
      </div>

      {/* Title */}
      <h3
        className="
          relative
          text-xl
          md:text-[21px]
          font-semibold
          text-white
          leading-snug
          mb-3
          tracking-tight
        "
        style={{ fontFamily: '"Sora", serif' }}
      >
        {title}
      </h3>

      {/* Description */}
      <p className="relative text-[14.5px] leading-7 text-slate-400 mb-4">
        Research result collected from {platform}. This source contains
        relevant information that contributed to the generated answer.
      </p>

      {/* Footer */}
      <div
        className="
          relative
          flex
          items-center
          justify-between
          pt-3.5
          border-t
          border-white/10
        "
      >
        <a
          href={link}
          target="_blank"
          rel="noreferrer"
          className="text-[12.5px] font-medium hover:underline transition-colors"
          style={{ color: accent, fontFamily: '"Space Grotesk", monospace' }}
        >
          Open on {platform} ↗
        </a>

        <div className="flex items-center gap-4">
          <span
            className="text-[11px] text-slate-500"
            style={{ fontFamily: '"Space Grotesk", monospace' }}
          >
            {confidence} match
          </span>

          <button
            onClick={() => {
              navigator.clipboard.writeText(title);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            className="text-slate-500 transition-colors"
            onMouseEnter={(e) => (e.currentTarget.style.color = accent)}
            onMouseLeave={(e) => (e.currentTarget.style.color = "")}
          >
            {copied ? <FaCheck style={{ color: accent }} /> : <FaCopy />}
          </button>
        </div>
      </div>
    </article>
  );
}
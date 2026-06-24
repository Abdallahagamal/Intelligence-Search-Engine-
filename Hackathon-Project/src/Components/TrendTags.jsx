export default function TrendTags({ trends }) {
  return (
    <div className="flex flex-wrap gap-3">
      {trends.map((trend) => (
        <span
          key={trend}
          className="
            px-3.5
            py-1.5
            rounded-full
            text-sm
            font-medium
            text-orange-300
            border
            border-orange-500/25
            transition-all
            hover:border-orange-400/50
            hover:text-orange-200
          "
          style={{ background: "rgba(249,115,22,0.08)" }}
        >
          #{trend}
        </span>
      ))}
    </div>
  );
}

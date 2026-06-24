export default function SummaryCard({ takeaway }) {
  return (
    <div
      className="rounded-3xl p-8"
      style={{
        background: "rgba(255,255,255,0.04)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "0 8px 40px rgba(0,0,0,0.5), 0 0 30px rgba(249,115,22,0.06)",
      }}
    >
      <h2 className="text-xl md:text-2xl font-bold mb-4 text-white">
        ⚡ Quick Takeaway
      </h2>

      <p className="text-base text-slate-300 leading-7">
        {takeaway}
      </p>
    </div>
  );
}

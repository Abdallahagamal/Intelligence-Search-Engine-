export default function RelatedQuestions({ questions, setQuery }) {
  return (
    <div>
      <h2 className="text-xl md:text-2xl font-bold mb-4 mt-6 text-white">
        People Also Ask?
      </h2>

      <div className="space-y-3">
        {questions.map((question) => (
          <button
            key={question}
            onClick={() => setQuery(question)}
            className="
              w-full
              text-left
              p-4
              rounded-xl
              text-slate-300
              hover:text-white
              border
              border-white/8
              hover:border-orange-500/40
              hover:bg-orange-500/6
              transition-all
              duration-200
            "
            style={{ background: "rgba(255,255,255,0.03)" }}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

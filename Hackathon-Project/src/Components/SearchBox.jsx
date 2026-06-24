import { FaSearch, FaChevronDown } from "react-icons/fa";
import { useState } from "react";

export default function SearchBox({
  query,
  setQuery,
  handleSearch,
  sources,
  setSources,
  showSuggestions,
  glow = true,
}) {
  const [openSources, setOpenSources] = useState(false);
  return (
     <div className="w-full max-w-3xl mx-auto px-2 sm:px-4 md:px-0">
      <div className="relative">
        {glow && <div className="glow-border" />}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="
            relative
            z-10
            bg-black/55
            backdrop-blur-xl
            border
            border-white/5
            rounded-2xl
            sm:rounded-3xl
            shadow-[0_8px_40px_rgba(0,0,0,0.55)]
            p-2
            sm:p-2.5
            flex
            flex-col
            gap-2
            sm:gap-2.5
            mb-4
            w-full
          "
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Paste an idea or question..."
            className="
              w-full
              bg-transparent
              outline-none
              text-white
              text-sm
              sm:text-base
              px-2
              py-2
              sm:py-3
              placeholder:text-slate-500
              md:placeholder:text-base
            "
          />

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2">
            <div className="flex items-center gap-2 flex-1 sm:flex-none">

              <div className="relative w-full sm:w-auto">
                <button
                  type="button"
                  onClick={() => setOpenSources(!openSources)}
                  className="
                    w-full
                    sm:w-auto
                    flex
                    items-center
                    justify-between
                    sm:justify-center
                    gap-2
                    px-3
                    sm:px-4
                    py-2
                    sm:py-1.5
                    rounded-full
                    text-white/80
                    text-xs
                    sm:text-sm
                    font-medium
                    tracking-wide
                    border
                    border-white/10
                    hover:border-white/20
                    hover:text-white
                    transition-all
                    min-h-[44px]
                    sm:min-h-auto
                  "
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    backdropFilter: "blur(12px)",
                  }}
                >
                  <span className="whitespace-nowrap">
                    Sources ({sources.filter((s) => s.enabled).length})
                  </span>
                  <FaChevronDown
                    size={11}
                    className={`transition-transform duration-300 flex-shrink-0 ${openSources ? "rotate-180" : ""}`}
                  />
                </button>

                {openSources && (
                  <div
                    className="
                      absolute
                      right-0
                      left-0
                      sm:right-0
                      sm:left-auto
                      top-full
                      mt-2
                      sm:mt-3
                      w-full
                      sm:w-80
                      max-h-96
                      overflow-y-auto
                      rounded-2xl
                      p-2
                      sm:p-3
                      z-50
                    "
                    style={{
                      background: "rgba(8, 5, 3, 0.92)",
                      backdropFilter: "blur(24px)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      boxShadow:
                        "0 16px 56px rgba(0,0,0,0.9), 0 0 40px rgba(249,115,22,0.1), 0 0 1px rgba(255,255,255,0.08)",
                    }}
                  >
                    <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest px-2 pb-2 mb-1 border-b border-white/5">
                      Sources
                    </p>

                    {sources.map((source) => (
                      <button
                        key={source.id}
                        type="button"
                        onClick={() => {
                          if (source.pro) return;
                          setSources((prev) =>
                            prev.map((s) =>
                              s.id === source.id
                                ? { ...s, enabled: !s.enabled }
                                : s
                            )
                          );
                        }}
                        className="
                          w-full
                          flex
                          items-center
                          justify-between
                          p-3
                          rounded-xl
                          text-slate-300
                          hover:text-white
                          hover:bg-orange-500/10
                          transition-all
                          duration-200
                        "
                      >
                        <span className="text-sm">{source.name}</span>

                        {source.pro ? (
                          <span
                            className="
                              text-[10px]
                              font-bold
                              tracking-widest
                              px-2.5
                              py-1
                              rounded-full
                              bg-orange-500/15
                              text-orange-300
                              border
                              border-orange-500/30
                            "
                          >
                            PRO
                          </span>
                        ) : (
                          <span
                            className={`
                              w-5
                              h-5
                              rounded-full
                              border
                              flex
                              items-center
                              justify-center
                              text-xs
                              font-bold
                              transition-all
                              duration-200
                              ${
                                source.enabled
                                  ? "bg-orange-500 text-black border-orange-500 shadow-[0_0_10px_rgba(249,115,22,0.55)]"
                                  : "border-slate-600/60 text-slate-600"
                              }
                            `}
                          >
                            {source.enabled && "✓"}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <button
                type="submit"
                title="Search"
                className="
                  w-full
                  sm:w-10
                  h-11
                  sm:h-10
                  flex
                  items-center
                  justify-center
                  rounded-full
                  bg-orange-500
                  hover:bg-orange-400
                  text-white
                  shadow-[0_0_20px_rgba(249,115,22,0.45)]
                  hover:scale-105
                  transition
                  min-h-[44px]
                  sm:min-h-auto
                  text-sm
                  sm:text-base
                  font-medium
                  sm:font-normal
                "
              >
                <FaSearch size={16} className="sm:block md:size-4" />
                <span className="sm:hidden">Search</span>
              </button>
            </div>
          </div>
        </form>
      </div>
      
      {showSuggestions && (
      <div className="flex flex-wrap justify-center gap-2 sm:gap-3 md:gap-4 mt-4 sm:mt-6 mb-15 px-2 sm:px-0">
        <button
  onClick={() => setQuery("AI in Education")}
  type="button"
  className="
    px-3
    sm:px-6
    py-2
    sm:py-3
    rounded-full
    border
    border-slate-700
    text-slate-400
    text-xs
    sm:text-sm
    hover:border-orange-400
    hover:text-orange-400
    transition
    cursor-pointer
    min-h-[40px]
    sm:min-h-auto
    flex
    items-center
    justify-center
    whitespace-nowrap
  "
>
  AI in Education
</button>

        <button onClick={() => setQuery("Climate Change")}
         type="button"
          className="
            px-3
            sm:px-6
            py-2
            sm:py-3
            rounded-full
            border
            border-slate-700
            text-slate-400
            text-xs
            sm:text-sm
            hover:border-orange-400
            hover:text-orange-400
            transition
            min-h-[40px]
            sm:min-h-auto
            flex
            items-center
            justify-center
            whitespace-nowrap
          "
        >
          Climate Change
        </button>

        <button
          onClick={() => setQuery("Future of LLMs")}
          type="button"
          className="
            px-3
            sm:px-6
            py-2
            sm:py-3
            rounded-full
            border
            border-slate-700
            text-slate-400
            text-xs
            sm:text-sm
            hover:border-orange-400
            hover:text-orange-400
            transition
            min-h-[40px]
            sm:min-h-auto
            flex
            items-center
            justify-center
            whitespace-nowrap
          "
        >
          Future of LLMs
        </button>
      </div>
      )}
    </div>
  );
}
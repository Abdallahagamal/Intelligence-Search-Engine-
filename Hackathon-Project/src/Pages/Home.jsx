import { useState } from "react";
import { FaBars, FaPlus } from "react-icons/fa";
import "@fontsource/sora";
import "@fontsource/outfit";
import "@fontsource/space-grotesk";
import "@fontsource/sora";
import "@fontsource/outfit";
import "@fontsource/space-grotesk";
import "@fontsource/inter"; // add this
import PlatformsMarquee from "../Components/PlatformsMarquee";

import SearchBox from "../Components/SearchBox";

import SourceCard from "../Components/SourceCard";
import TrendTags from "../Components/TrendTags";
import RelatedQuestions from "../Components/RelatedQuestions";
import IconRail from "../Components/IconRail";
import ParticleField from "../Components/ParticleField";
import PipelineProgress from "../Components/PipelineProgress";
import DebateCard from "../Components/DebateCard";
import KnowledgeGraph from "../Components/KnowledgeGraph";
import ConsensusMeter from "../Components/ConsensusMeter";
import CitedText from "../Components/CitedText";
import PersonaCards from "../Components/PersonaCards";
import PipelineReplay from "../Components/PipelineReplay";

const API_URL = "https://web-production-4f1c8.up.railway.app/research";

export default function Home() {

  // const [query, setQuery] = useState("");
  // const [results, setResults] = useState(null);

  // const [loading, setLoading] = useState(false);
  // const [searched, setSearched] = useState(false);


  const [query, setQuery] = useState("");

  const [conversation, setConversation] = useState([]);

  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const [railExpanded, setRailExpanded] = useState(false);
  const [openProfileMenu, setOpenProfileMenu] = useState(false);

  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [sources, setSources] = useState([
    {
      id: "reddit",
      name: "Reddit",
      enabled: true,
      pro: false,
    },

    {
      id: "arxiv",
      name: "Arxiv",
      enabled: true,
      pro: false,
    },

    {
      id: "news",
      name: "News",
      enabled: true,
      pro: false,
    },

    {
      id: "stackoverflow",
      name: "Stack Overflow",
      enabled: true,
      pro: false,
    },

    {
      id: "github",
      name: "GitHub",
      enabled: true,
      pro: false,
    },

    {
      id: "wikipedia",
      name: "Wikipedia",
      enabled: true,
      pro: false,
    },

    {
      id: "linkedin",
      name: "LinkedIn",
      enabled: false,
      pro: true,
    },

    {
      id: "scholar",
      name: "Google Scholar",
      enabled: false,
      pro: true,
    },

    {
      id: "x",
      name: "X (Twitter)",
      enabled: false,
      pro: true,
    },

    {
      id: "facebook",
      name: "Facebook",
      enabled: false,
      pro: true,
    },
  ]);

  // const handleSearch = () => {
  //   if (!query.trim()) return;

  //   setSearched(true); 

  //   setLoading(true);

  //   setTimeout(() => {
  //     setResults(dummyData);
  //     setLoading(false);
  //   }, 2000);
  // };

  const handleSearch = async (explicitQuery = null) => {
    const q = (typeof explicitQuery === "string" ? explicitQuery : query).trim();
    if (!q) return;

    setQuery(q);
    setSearched(true);
    setLoading(true);

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: q,
    };

    setConversation((prev) => [...prev, userMessage]);

    const enabledSourceIds = sources
      .filter((s) => s.enabled && !s.pro)
      .map((s) => s.id);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          sources: enabledSourceIds,
          max_results: 10,
          include_debate: true,
          include_graph: true,
          include_llm: true,
        }),
      });

      const data = await response.json();
      const llm = data.llm_response || {};
      const ranked = data.ranked_sources || [];

      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        data: {
          takeaway: llm.takeaway || "No summary available.",
          conclusion: llm.final_conclusion || "",
          summary: llm.detailed_answer || "",
          trends: llm.trends || [],
          relatedQuestions: llm.related_questions || [],
          debate: data.debate || null,
          graph: data.graph || null,
          plan: data.plan || null,
          meta: data.meta || null,
          filterSummary: data.filter_summary || null,
          sources: ranked.map((s) => ({
            id: s.platform?.toLowerCase(),
            platform: s.platform,
            title: s.title,
            snippet: s.snippet || "",
            confidence: `${Math.round(s.confidence)}%`,
            link: s.url,
            time: s.date,
          })),
        },
      };

      setConversation((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("API error:", err);
      setConversation((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          data: {
            takeaway: "Something went wrong. Please try again.",
            summary: "",
            trends: [],
            relatedQuestions: [],
            sources: [],
          },
        },
      ]);
    } finally {
      setLoading(false);
      setQuery("");
    }
  };
  const handleNewChat = () => {
    setConversation([]);
    setSearched(false);
  };

  return (
    <div className="min-h-screen w-full text-white overflow-x-hidden flex flex-col items-center relative" style={{ backgroundColor: "#080503" }}>

      {/* Full hero warm glow — slides away on search */}
      <div
        className={`
        hero-bg-exit
        hero-bg-radial
        fixed
        inset-0
        z-0
        ${searched
            ? "-translate-y-full opacity-0 pointer-events-none"
            : "translate-y-0 opacity-100"
          }
      `}
      >
        <div className="absolute inset-0 bg-black/15" />
      </div>

      {/* Persistent dim warm glow for the results page */}
      <div
        className="fixed inset-0 z-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 70% 40% at 50% 100%, rgba(180,70,15,0.18) 0%, rgba(80,30,5,0.10) 50%, transparent 80%)",
        }}
      />

      {/* Interactive particle field — sits above glows, below content */}
      <ParticleField style={{ zIndex: 1 }} />

      <IconRail
        visible={sidebarOpen}
        expanded={railExpanded}
        setExpanded={setRailExpanded}
        onNewChat={handleNewChat}
      />

      {/* Glow Effects */}

      {/* Glow orbs — hidden over the orange hero, shown after first search */}
      {searched && (
        <>
          <div className="fixed top-20 left-20 w-72 h-72 bg-orange-500/10 blur-[140px] rounded-full pointer-events-none z-0"></div>
          <div className="fixed bottom-20 right-20 w-72 h-72 bg-orange-700/8 blur-[140px] rounded-full pointer-events-none z-0"></div>
        </>
      )}

      <div className="relative z-10 w-full  mx-auto pt-30">

        {/* Navbar */}


        <div
          className="
    fixed
    top-0
    z-50

    flex
    justify-between
    items-center


    px-20
    py-3
    mb-10
    mt-0
    w-full



    shadow-lg
  
"
        >
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="
      p-2
      rounded-xl
      text-slate-400
      hover:text-white
      hover:bg-white/8
      transition-all
      duration-200
    "
            >
              <FaBars size={18} />
            </button>

            <div
              className={`
      flex items-center gap-2.5
      transition-transform
      duration-300
      ease-in-out
      ${sidebarOpen ? (railExpanded ? "translate-x-48" : "translate-x-18") : "translate-x-0"}
    `}
            >
              <h2
                className="text-2xl font-extrabold tracking-tight leading-none text-white select-none"
                style={{ fontFamily: '"Sora", "Outfit", system-ui, sans-serif', letterSpacing: "-0.02em" }}
              >
                <span className="text-white">Re</span><span className="searchify-gradient">Searchify</span>
              </h2>

              {/* Logo mark — open search loop with glowing core */}
              <svg
                viewBox="0 0 32 32"
                className="researchify-logo"
                width="28"
                height="28"
                aria-label="ReSearchify logo"
              >
                <defs>
                  <linearGradient id="rs-ring" x1="6" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#fed7aa" />
                    <stop offset="45%" stopColor="#fb923c" />
                    <stop offset="100%" stopColor="#c2410c" />
                  </linearGradient>
                  <radialGradient id="rs-core" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#ffedd5" />
                    <stop offset="55%" stopColor="#fb923c" />
                    <stop offset="100%" stopColor="#9a3412" />
                  </radialGradient>
                  <radialGradient id="rs-tip" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#fff" />
                    <stop offset="55%" stopColor="#fdba74" />
                    <stop offset="100%" stopColor="#c2410c" />
                  </radialGradient>
                </defs>

                {/* White handle — clean magnifier grip extending from the ring */}
                <line
                  x1="24.6"
                  y1="24.6"
                  x2="29.6"
                  y2="29.6"
                  stroke="#ffffff"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  opacity="0.96"
                />

                {/* Open search loop — ~290° arc, gap at upper-right */}
                <path
                  d="M 23.8 7.8 A 11 11 0 1 1 22.5 5.8"
                  fill="none"
                  stroke="url(#rs-ring)"
                  strokeWidth="2.8"
                  strokeLinecap="round"
                />

                {/* Query tip — bright dot at the arc's leading edge */}
                <circle cx="23.8" cy="7.8" r="2.4" fill="url(#rs-tip)" />

                {/* Core insight — bright center dot with white highlight */}
                <circle cx="16" cy="16" r="3.4" fill="url(#rs-core)" />
                <circle cx="14.9" cy="14.9" r="0.9" fill="#fff" opacity="0.92" />
              </svg>
            </div>

          </div>

          <div className="flex items-center gap-4 mx-8 ">



            <div className="relative flex items-center gap-2.5">
              <span className="text-slate-300 font-semibold text-sm">
                Nancy Mohamed
              </span>

              <button
                type="button"
                onClick={() => setOpenProfileMenu(!openProfileMenu)}
                className="
        w-9 h-9
        rounded-full
        flex items-center justify-center
        text-white font-bold text-sm
        transition-all duration-200
        hover:scale-105
        flex-shrink-0
      "
                style={{
                  background: "linear-gradient(135deg, #c2410c 0%, #fb923c 50%, #94a3b8 100%)",
                  boxShadow: "0 0 14px rgba(249,115,22,0.45)",
                }}
              >
                N
              </button>

              {openProfileMenu && (
                <div
                  className="absolute right-0 top-full mt-3 w-64 rounded-2xl p-3 z-50"
                  style={{
                    background: "rgba(8, 5, 3, 0.95)",
                    backdropFilter: "blur(24px)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    boxShadow: "0 16px 56px rgba(0,0,0,0.9), 0 0 40px rgba(249,115,22,0.1)",
                  }}
                >
                  {/* User info */}
                  <div className="flex items-center gap-3 px-2 py-3 mb-2 border-b border-white/5">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0"
                      style={{
                        background: "linear-gradient(135deg, #c2410c 0%, #fb923c 50%, #94a3b8 100%)",
                        boxShadow: "0 0 12px rgba(249,115,22,0.4)",
                      }}
                    >
                      N
                    </div>
                    <div className="min-w-0">
                      <p className="text-white font-semibold text-sm truncate">Nancy Mohamed</p>
                      <p className="text-slate-500 text-xs truncate">nancy@example.com</p>
                    </div>
                  </div>

                  {/* Menu items */}
                  {[
                    { label: "Profile Settings" },
                    { label: "Help & Support" },
                  ].map((item) => (
                    <button
                      key={item.label}
                      type="button"
                      className="
              w-full text-left px-3 py-2.5 rounded-xl
              text-slate-300 hover:text-white text-sm
              hover:bg-orange-500/10
              transition-all duration-200
            "
                    >
                      {item.label}
                    </button>
                  ))}

                  <div className="my-2 border-t border-white/5" />

                  <button
                    type="button"
                    className="
            w-full text-left px-3 py-2.5 rounded-xl
            text-orange-400 hover:text-orange-300 text-sm font-medium
            hover:bg-orange-500/10
            transition-all duration-200
          "
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>


          </div>

        </div>

        {/* Hero */}

        <div
          className={`
    w-full
    flex
    flex-col
    items-center
    text-center
    transition-all
    duration-1000
    ease-in-out

    ${searched
              ? "min-h-0 pt-4"
              : "min-h-[70vh]"
            }
  `}
        >

          <h2
            className={` 
      font-bold
      leading-tight
      text-center
      transition-all
      duration-700
      ${searched
                ? "text-3xl md:text-4xl"
                : "text-4xl md:text-5xl"
              }
    `}

            style={{ fontFamily: "Pin Sans" }}
          >

            <span style={{ fontFamily: "Makira", fontWeight: 700 }} className="text-white">WELCOME</span>

            <span
              style={{ fontFamily: "Makira", fontWeight: 700, color: "#f97316" }}
              className="ml-3"
            >
              BACK!
            </span>

            <br />


          </h2>

          {!searched && (
            <p
              className=" font-['Sora']
        tracking-tight
        leading-tight
        text-slate-400
        max-w-2xl
        mx-auto
        text-lg
        mt-5
        mb-10
      "
            >
              Search across Reddit, X, Arxiv,
              Research Papers and News
              to discover insights faster.
            </p>
          )}

          {!searched && (
            <SearchBox
              query={query}
              setQuery={setQuery}
              handleSearch={handleSearch}
              sources={sources}
              setSources={setSources}
              showSuggestions={true}
            />
          )}
          {!searched && <PlatformsMarquee />}

        </div>
        {/* Loading */}

        {loading && <PipelineProgress active={loading} />}

        {/* Results */}

        {conversation.length > 0 && !loading && (
          <div
            className="
      mt-12
      w-full
      max-w-6xl
      mx-auto
      space-y-12
      mb-50
    "
          >
            {conversation.map((message) => (
              <div key={message.id}>

                {message.role === "user" ? (

                  <div className="flex justify-end mb-6">
                    <div
                      className="rounded-2xl px-5 py-3 max-w-xl text-slate-200"
                      style={{
                        background: "rgba(249,115,22,0.08)",
                        border: "1px solid rgba(249,115,22,0.18)",
                      }}
                    >
                      {message.content}
                    </div>
                  </div>

                ) : (

                  <div className="space-y-12">

                    {/* 1 — AI Synthesis with inline citations */}
                    <CitedText
                      text={message.data.takeaway}
                      sources={message.data.sources}
                    />

                    {/* 2 — Consensus Meter */}
                    <ConsensusMeter debate={message.data.debate} />

                    {/* 3 — Three Persona Perspectives */}
                    <PersonaCards sources={message.data.sources} />

                    {/* 4 — Sources grid */}
                    <div>
                      <h2 className="text-xl md:text-2xl font-bold mb-6">
                        Sources
                      </h2>
                      <div className="grid grid-cols-1 w-[75%] gap-6 mx-auto">
                        {message.data.sources.map((source) => (
                          <SourceCard
                            key={source.title}
                            platform={source.platform}
                            title={source.title}
                            confidence={source.confidence}
                            link={source.link}
                            time={source.time}
                          />
                        ))}
                      </div>
                    </div>

                    {/* 5 — Debate analysis */}
                    <DebateCard debate={message.data.debate} />

                    {/* 6 — Knowledge Graph (click node → rabbit-hole search) */}
                    <KnowledgeGraph
                      graph={message.data.graph}
                      onNodeClick={(label) => handleSearch(label)}
                    />

                    {/* 7 — Trends & follow-up questions */}
                    <div>
                      <h2 className="text-xl md:text-2xl font-bold mb-6">
                        🔥 Trending Topics
                      </h2>
                      <TrendTags trends={message.data.trends} />
                      <RelatedQuestions
                        questions={message.data.relatedQuestions}
                        setQuery={setQuery}
                      />
                    </div>

                    {/* 8 — Pipeline Replay */}
                    <PipelineReplay
                      plan={message.data.plan}
                      meta={message.data.meta}
                      filterSummary={message.data.filterSummary}
                    />

                  </div>

                )}

              </div>
            ))}
          </div>
        )}
        {searched && (
          <div
            className="
      fixed
      bottom-0
      left-0
      right-0
      z-50

      bg-black/80
    backdrop-blur-xl

      py-4
      px-4
    "
          >
            <SearchBox
              query={query}
              setQuery={setQuery}
              handleSearch={handleSearch}
              sources={sources}
              setSources={setSources}
              showSuggestions={false}
            />
          </div>
        )}

      </div>
    </div>
  );
}
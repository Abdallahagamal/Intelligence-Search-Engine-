const allSources = [
  {
    id: "reddit",
    platform: "Reddit",
    title: "How students use AI every day",
    confidence: "89%",
    link: "https://reddit.com",
  },

  {
    id: "arxiv",
    platform: "Arxiv",
    title: "Large Language Models in Education",
    confidence: "95%",
    link: "https://arxiv.org"
  },

  {
    id: "news",
    platform: "News",
    title: "Universities embrace AI learning",
    confidence: "81%",
  },

  {
    id: "stackoverflow",
    platform: "Stack Overflow",
    title: "Developers discuss AI learning tools",
    confidence: "84%",
    link: "https://stackoverflow.com"
  },

  {
    id: "github",
    platform: "GitHub",
    title: "Open-source AI education projects",
    confidence: "92%",
    link: "https://github.com"
  },

  {
    id: "wikipedia",
    platform: "Wikipedia",
    title: "Artificial Intelligence in Education",
    confidence: "87%",
    link: "https://wikipedia.org"
  },
];

const dummyData = {
  takeaway:
    "Most sources agree that AI significantly improves personalized learning and student engagement.",

  summary:
    "Artificial Intelligence is transforming education through personalized learning, automated assessment and intelligent tutoring systems.",

  sources: allSources,

  trends: [
    "AI Tutors",
    "LLMs",
    "Research Automation",
    "EdTech",
    "Personalized Learning",
  ],
  relatedQuestions: [
    "Will AI replace teachers?",
    "How do LLMs help students?",
    "AI in universities?",
    "AI tutoring systems?"
  ],
};


export default dummyData;
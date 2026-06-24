import {
  FaReddit,
  FaGithub,
  FaWikipediaW,
  FaStackOverflow,
  FaNewspaper,
} from "react-icons/fa";
import { SiArxiv } from "react-icons/si";

const platforms = [
  { name: "Reddit", icon: FaReddit },
  { name: "Arxiv", icon: SiArxiv },
  { name: "News", icon: FaNewspaper },
  { name: "Stack Overflow", icon: FaStackOverflow },
  { name: "GitHub", icon: FaGithub },
  { name: "Wikipedia", icon: FaWikipediaW },
];

export default function PlatformsMarquee() {
  // duplicate the list so the loop is seamless
  const doubled = [...platforms, ...platforms];

  return (
    <div className="w-full overflow-hidden marquee-mask mt-25">
      <div className="marquee-track flex items-center gap-16 w-max">
        {doubled.map(({ name, icon: Icon }, i) => (
          <div
            key={`${name}-${i}`}
            className="logo-fade flex items-center gap-3 text-slate-400"
            style={{ animationDelay: `${(i % platforms.length) * 0.4}s` }}
          >
            <Icon size={26} />
            <span className="text-sm font-medium whitespace-nowrap">
              {name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
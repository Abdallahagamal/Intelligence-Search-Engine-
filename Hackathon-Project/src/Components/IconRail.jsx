import { useState } from "react";

import {
  FaBars,
  FaPlus,
  FaCommentDots,
  FaCog,
  FaBell,
  FaHeart,
  FaUser,
  FaShieldAlt,
  FaQuestionCircle,
  FaSignOutAlt,
} from "react-icons/fa";

export default function IconRail({
  visible,
  expanded,
  setExpanded,
  onNewChat,
  onClose,
}) {
  const [profileOpen, setProfileOpen] = useState(false);

  const MenuItem = ({
    icon,
    label,
    onClick,
    hoverColor = "hover:text-orange-400",
  }) => (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-4 px-5 py-3
        text-slate-300 ${hoverColor} hover:bg-white/5
        transition-all duration-300
      `}
    >
      <span className="text-lg flex-shrink-0">{icon}</span>
      {/* Mobile: always show label (drawer is w-64). Desktop: only when expanded */}
      <span className="text-sm font-medium whitespace-nowrap sm:hidden">{label}</span>
      {expanded && (
        <span className="text-sm font-medium whitespace-nowrap hidden sm:inline">{label}</span>
      )}
    </button>
  );

  return (
    <div
      className={`
        fixed top-0 left-0 h-screen z-50
        flex flex-col
        transition-all duration-300 ease-in-out

        bg-[rgba(8,5,3,0.92)]
        backdrop-blur-2xl
        border-r border-white/10
        shadow-[0_8px_32px_rgba(0,0,0,0.6)]

        /* Mobile: full drawer, slides in/out */
        w-64
        ${visible ? "translate-x-0" : "-translate-x-full"}

        /* Desktop: always visible, collapses to icon rail */
        sm:translate-x-0
        ${expanded ? "sm:w-64" : "sm:w-16"}
      `}
    >
      {/* Top: expand/collapse toggle (desktop) or just a header (mobile) */}
      <div className="px-3 py-5 flex items-center justify-between sm:block">
        <button
          onClick={() => setExpanded(!expanded)}
          className="
            flex items-center gap-4 px-3 py-2 rounded-xl
            text-slate-300 hover:bg-white/5 hover:text-white transition
          "
        >
          <FaBars size={18} />
          {/* Mobile: always show. Desktop: only when expanded */}
          <span className="font-medium sm:hidden">Menu</span>
          {expanded && <span className="font-medium hidden sm:inline">Menu</span>}
        </button>

        {/* Mobile close button */}
        <button
          onClick={onClose}
          className="sm:hidden text-slate-400 hover:text-white px-3 py-2 text-xl leading-none"
        >
          ✕
        </button>
      </div>

      {/* User section */}
      <div className="relative">
        <button
          onClick={() => setProfileOpen(!profileOpen)}
          className="flex items-center gap-3 px-3 mb-6 cursor-pointer w-full"
        >
          <div
            className="
              w-9 h-9 rounded-full flex-shrink-0
              bg-gradient-to-r from-orange-500 via-stone-600 to-stone-900
              flex items-center justify-center
              text-white font-bold
              hover:scale-105 transition
            "
          >
            N
          </div>

          {/* Name: always on mobile, only when expanded on desktop */}
          <div className="sm:hidden">
            <p className="font-medium text-left">Nancy</p>
            <p className="text-xs text-slate-400">Free Plan</p>
          </div>
          {expanded && (
            <div className="hidden sm:block">
              <p className="font-medium text-left">Nancy</p>
              <p className="text-xs text-slate-400">Free Plan</p>
            </div>
          )}
        </button>

        {profileOpen && (
          <div
            className="absolute left-0 top-full mt-2 w-56 rounded-2xl overflow-hidden z-50"
            style={{
              background: "rgba(8,5,3,0.97)",
              backdropFilter: "blur(24px)",
              border: "1px solid rgba(255,255,255,0.08)",
              boxShadow: "0 16px 56px rgba(0,0,0,0.9), 0 0 30px rgba(249,115,22,0.08)",
            }}
          >
            <div className="p-4 border-b border-white/10">
              <p className="font-semibold">Nancy Mohamed</p>
              <p className="text-xs text-slate-400">Free Plan</p>
            </div>

            {[
              { icon: <FaUser />, label: "Profile" },
              { icon: <FaShieldAlt />, label: "Privacy" },
              { icon: <FaQuestionCircle />, label: "Help" },
            ].map((item) => (
              <button
                key={item.label}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/5 transition text-sm text-slate-300 hover:text-white"
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}

            <div className="border-t border-white/10">
              <button className="w-full px-4 py-3 flex items-center gap-3 text-red-400 hover:bg-red-500/10 transition text-sm">
                <FaSignOutAlt />
                <span>Log out</span>
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="mx-3 mb-4 h-px bg-white/10" />

      {/* Menu Items */}
      <MenuItem icon={<FaPlus />} label="New Chat" onClick={onNewChat} />
      <MenuItem icon={<FaCommentDots />} label="History" />
      <MenuItem icon={<FaBell />} label="Notifications" />
      <MenuItem icon={<FaHeart />} label="Likes" hoverColor="hover:text-pink-400" />

      <div className="flex-1" />

      <div className="mb-5">
        <MenuItem icon={<FaCog />} label="Settings" />
      </div>
    </div>
  );
}

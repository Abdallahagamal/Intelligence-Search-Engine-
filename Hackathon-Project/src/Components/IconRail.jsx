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
        w-full
        flex
        items-center
        gap-4
        px-5
        py-3
        text-slate-300
        ${hoverColor}
        hover:bg-white/5
        transition-all
        duration-300
      `}
    >
      <span className="text-lg">
        {icon}
      </span>

      {expanded && (
        <span className="text-sm font-medium whitespace-nowrap">
          {label}
        </span>
      )}
    </button>
  );

  return (
    <div
      className={`
        fixed
        top-0
        left-0
        h-screen
        z-50

        flex
        flex-col

        transition-all
        duration-300

        ${expanded ? "w-64" : "w-16"}
        ${visible ? "translate-x-0" : "-translate-x-full"}

        bg-white/[0.04]
        backdrop-blur-2xl

        border-r
        border-white/10

        shadow-[0_8px_32px_rgba(0,0,0,0.45)]
      `}
    >
      {/* Top Section */}

      <div className="px-3 py-5">

        <button
          onClick={() =>
            setExpanded(!expanded)
          }
          className="
            w-full
            flex
            items-center
            gap-4
            px-3
            py-2
            rounded-xl
            text-slate-300
            hover:bg-white/5
            hover:text-white
            transition
          "
        >
          <FaBars size={18} />

          {expanded && (
            <span className="font-medium">
              Menu
            </span>
          )}
        </button>

      </div>

      {/* User */}

      <div className="relative">

  <button
    onClick={() => setProfileOpen(!profileOpen)}
    className="
      flex
      items-center
      gap-3
      px-3
      mb-6
      cursor-pointer
    "
  >
    <div
      className="
        w-9
        h-9
        rounded-full
        bg-gradient-to-r
        from-orange-500
        via-stone-600
        to-stone-900
        flex
        items-center
        justify-center
        text-white
        font-bold
        shrink-0

        hover:scale-105
        transition
      "
    >
      N
    </div>

    {expanded && (
      <div>
        <p className="font-medium">
          Nancy
        </p>

        <p className="text-xs text-slate-400">
          Free Plan
        </p>
      </div>
    )}
  </button>

  {profileOpen && (
    <div
      className="absolute left-14 top-0 w-64 rounded-2xl overflow-hidden"
      style={{
        background: "rgba(8,5,3,0.95)",
        backdropFilter: "blur(24px)",
        border: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "0 16px 56px rgba(0,0,0,0.9), 0 0 30px rgba(249,115,22,0.08)",
      }}
    >
      {/* Header */}

      <div className="p-4 border-b border-white/10">

        <p className="font-semibold">
          Nancy Mohamed
        </p>

        <p className="text-xs text-slate-400">
          Free Plan
        </p>

      </div>

      {/* Profile */}

      <button
        className="
          w-full
          px-4
          py-3

          flex
          items-center
          gap-3

          hover:bg-white/5
          transition
        "
      >
        <FaUser />

        <span>Profile</span>
      </button>

      {/* Privacy */}

      <button
        className="
          w-full
          px-4
          py-3

          flex
          items-center
          gap-3

          hover:bg-white/5
          transition
        "
      >
        <FaShieldAlt />

        <span>Privacy</span>
      </button>

      {/* Help */}

      <button
        className="
          w-full
          px-4
          py-3

          flex
          items-center
          gap-3

          hover:bg-white/5
          transition
        "
      >
        <FaQuestionCircle />

        <span>Help</span>
      </button>

      {/* Footer */}

      <div className="border-t border-white/10">

        <button
          className="
            w-full
            px-4
            py-3

            flex
            items-center
            gap-3

            text-red-400

            hover:bg-red-500/10
            transition
          "
        >
          <FaSignOutAlt />

          <span>Log out</span>
        </button>

      </div>

    </div>
  )}

</div>
<div className="mx-3 mb-4 h-px bg-white/10" />

      {/* Menu Items */}

      <MenuItem
        icon={<FaPlus />}
        label="New Chat"
        onClick={onNewChat}
      />

      <MenuItem
        icon={<FaCommentDots />}
        label="History"
      />

      <MenuItem
        icon={<FaBell />}
        label="Notifications"
      />

      <MenuItem
        icon={<FaHeart />}
        label="Likes"
        hoverColor="hover:text-pink-400"
      />

      <div className="flex-1" />

      {/* Bottom */}

      <div className="mb-5">
        <MenuItem
          icon={<FaCog />}
          label="Settings"
        />
      </div>
    </div>
  );
}
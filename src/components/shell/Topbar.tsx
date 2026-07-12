import { Search, Bell } from "lucide-react";

interface TopbarProps {
  breadcrumb: string;
  userName: string;
  userInitials: string;
}

export default function Topbar({ breadcrumb, userName, userInitials }: TopbarProps) {
  return (
    <div className="flex items-center justify-between px-6 py-5">
      <p className="text-sm font-medium" style={{ color: "var(--af-text-secondary)" }}>
        {breadcrumb}
      </p>

      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-2 rounded-full bg-white px-4 py-2"
          style={{ boxShadow: "var(--af-shadow-card)" }}
        >
          <Search size={16} style={{ color: "var(--af-text-muted)" }} />
          <span className="text-sm" style={{ color: "var(--af-text-muted)" }}>
            Search assets, people, tags...
          </span>
        </div>

        <button
          className="flex h-9 w-9 items-center justify-center rounded-full bg-white"
          style={{ boxShadow: "var(--af-shadow-card)" }}
        >
          <Bell size={16} style={{ color: "var(--af-text-secondary)" }} />
        </button>

        <div
          className="flex items-center gap-2 rounded-full bg-white py-1.5 pl-1.5 pr-3"
          style={{ boxShadow: "var(--af-shadow-card)" }}
        >
          <div
            className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold"
            style={{ backgroundColor: "var(--af-lilac-bg)", color: "var(--af-lilac-text)" }}
          >
            {userInitials}
          </div>
          <span className="text-sm font-medium" style={{ color: "var(--af-text-primary)" }}>
            {userName}
          </span>
        </div>
      </div>
    </div>
  );
}

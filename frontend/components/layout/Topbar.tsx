"use client";

import { Search, Bell, ChevronDown, Plus } from "lucide-react";
import { ThemeToggle } from "@/components/theme/ThemeToggle";

interface TopbarProps {
  title: string;
  description: string;
  onAddClick?: () => void;
  userInitial?: string;
}

export default function Topbar({
  title,
  description,
  onAddClick,
  userInitial = "U",
}: TopbarProps) {
  return (
    <header className="app-header">
      <div className="header-breadcrumbs">
        <div>
          <h1 className="text-sm font-semibold text-primary">{title}</h1>
          <p className="text-xs text-secondary">{description}</p>
        </div>
      </div>

      <div className="header-right">
        <button type="button" className="header-icon-btn" aria-label="Search">
          <Search size={16} />
        </button>

        <button type="button" className="header-icon-btn" aria-label="Notifications">
          <Bell size={18} />
          <span className="notification-dot" />
        </button>

        {onAddClick && (
          <button type="button" className="btn btn-primary btn-sm" onClick={onAddClick}>
            <Plus size={15} />
            <span>Add Subscription</span>
          </button>
        )}

        <ThemeToggle className="header-theme-toggle" />

        <div className="header-user-badge">
          <span>{userInitial}</span>
        </div>
      </div>
    </header>
  );
}

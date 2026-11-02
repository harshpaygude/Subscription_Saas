"use client";

import {
  Search,
  Bell,
  ChevronDown,
  Plus,
} from "lucide-react";


interface TopbarProps {
  title: string;
  description: string;
}


export default function Topbar({
  title,
  description,
}: TopbarProps) {
  return (
    <header className="topbar">

      <div>
        <h1>{title}</h1>

        <p>{description}</p>
      </div>


      <div className="topbar-actions">

        <button className="search-box">
          <Search size={16} />

          <span>
            Search subscriptions...
          </span>

          <kbd>⌘K</kbd>
        </button>


        <button className="icon-button notification-button">
          <Bell size={18} />
          <span />
        </button>


        <button className="add-subscription">
          <Plus size={17} />
          Add Subscription
        </button>


        <button className="user-menu">

          <div className="user-avatar">
            H
          </div>

          <ChevronDown size={15} />

        </button>

      </div>

    </header>
  );
}

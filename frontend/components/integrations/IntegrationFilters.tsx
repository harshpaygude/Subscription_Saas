"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import type { IntegrationCategory } from "@/lib/integrations";
import { categoryLabels } from "@/lib/integrations";

export type IntegrationFilterCategory = "all" | IntegrationCategory;
export type IntegrationFilterStatus = "all" | "connected" | "available";

interface IntegrationFiltersProps {
  search: string;
  category: IntegrationFilterCategory;
  status: IntegrationFilterStatus;
  onSearchChange: (value: string) => void;
  onCategoryChange: (value: IntegrationFilterCategory) => void;
  onStatusChange: (value: IntegrationFilterStatus) => void;
}

export function IntegrationFilters({
  search,
  category,
  status,
  onSearchChange,
  onCategoryChange,
  onStatusChange,
}: IntegrationFiltersProps) {
  return (
    <div className="filter-toolbar" aria-label="Integration filters">
      {/* Search Input with Icon */}
      <div className="filter-search-box">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search providers by name or capability…"
          aria-label="Search integrations"
        />
        {search && (
          <button
            type="button"
            className="search-clear-btn"
            onClick={() => onSearchChange("")}
            aria-label="Clear search"
          >
            ×
          </button>
        )}
      </div>

      {/* Category Dropdown */}
      <div className="filter-select-wrap">
        <SlidersHorizontal size={14} className="filter-icon" />
        <select
          value={category}
          onChange={(e) => onCategoryChange(e.target.value as IntegrationFilterCategory)}
          aria-label="Filter by category"
        >
          <option value="all">All Categories</option>
          {Object.entries(categoryLabels).map(([val, label]) => (
            <option value={val} key={val}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Status Dropdown */}
      <div className="filter-select-wrap">
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value as IntegrationFilterStatus)}
          aria-label="Filter by status"
        >
          <option value="all">All Statuses</option>
          <option value="connected">Connected Only</option>
          <option value="available">Not Connected</option>
        </select>
      </div>
    </div>
  );
}

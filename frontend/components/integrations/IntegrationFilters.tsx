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
    <div className="hub-filters" aria-label="Integration filters">
      <label className="hub-search">
        <span className="sr-only">Search integrations</span>
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search providers"
        />
      </label>
      <label className="hub-filter-select">
        <span className="sr-only">Filter by category</span>
        <select
          value={category}
          onChange={(event) => onCategoryChange(event.target.value as IntegrationFilterCategory)}
        >
          <option value="all">All categories</option>
          {Object.entries(categoryLabels).map(([value, label]) => (
            <option value={value} key={value}>{label}</option>
          ))}
        </select>
      </label>
      <label className="hub-filter-select">
        <span className="sr-only">Filter by status</span>
        <select
          value={status}
          onChange={(event) => onStatusChange(event.target.value as IntegrationFilterStatus)}
        >
          <option value="all">All statuses</option>
          <option value="connected">Connected</option>
          <option value="available">Not connected</option>
        </select>
      </label>
    </div>
  );
}

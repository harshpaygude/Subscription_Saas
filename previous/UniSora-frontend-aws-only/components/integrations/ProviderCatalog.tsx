"use client";

import type { ProviderDefinition } from "./providerRegistry";

interface ProviderCatalogProps {
  providers: ProviderDefinition[];
  search: string;
  onSelect: (provider: ProviderDefinition) => void;
}

export function ProviderCatalog({ providers, search, onSelect }: ProviderCatalogProps) {
  const query = search.trim().toLowerCase();
  const visible = providers.filter((provider) =>
    [provider.displayName, provider.description, ...provider.searchTerms]
      .join(" ")
      .toLowerCase()
      .includes(query),
  );

  if (!visible.length) return <p className="sh-no-results">No services found.</p>;

  return (
    <div className="sh-provider-catalog">
      {visible.map((provider) => {
        const Icon = provider.icon;
        return (
          <article className="sh-service-option" key={provider.id}>
            <span className="sh-aws-icon"><Icon size={22} /></span>
            <div className="sh-service-option-copy">
              <strong>{provider.displayName}</strong>
              <p>{provider.description}</p>
            </div>
            <button className="sh-add-button" onClick={() => onSelect(provider)}>
              Select
            </button>
          </article>
        );
      })}
    </div>
  );
}

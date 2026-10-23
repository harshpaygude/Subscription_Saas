import { Cloud } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type ProviderCapability = "connection_setup" | "costs" | "account_plan";

export interface ProviderDefinition {
  id: string;
  displayName: string;
  description: string;
  searchTerms: string[];
  icon: LucideIcon;
  capabilities: ProviderCapability[];
}

// Adding a provider means adding metadata and its provider-specific modules;
// the catalog and connection lifecycle UI remain unchanged.
export const providerRegistry: ProviderDefinition[] = [
  {
    id: "AWS",
    displayName: "Amazon Web Services",
    description: "Connect an AWS account to retrieve account-plan and cost information.",
    searchTerms: ["amazon", "aws", "cloud"],
    icon: Cloud,
    capabilities: ["connection_setup", "costs", "account_plan"],
  },
];

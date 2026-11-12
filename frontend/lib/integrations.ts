export type IntegrationCategory =
  | "cloud"
  | "ai"
  | "productivity"
  | "developer"
  | "billing"
  | "custom";

export type IntegrationStatus = "CONNECTED" | "DISCONNECTED" | "EXPIRED" | "ERROR";

export type IntegrationAvailability = "available" | "manual" | "coming_soon";

export interface ProviderDefinition {
  id: string;
  name: string;
  category: IntegrationCategory;
  description: string;
  capabilities: string[];
  availability: IntegrationAvailability;
  icon: string;
  authType: string;
  instructions: string[];
  requiredFields: string[];
  optionalFields?: string[];
}

export interface AWSConnectionCredentials {
  access_key_id: string;
  secret_access_key: string;
  session_token?: string;
  region: string;
}

export interface AzureServicePrincipalCredentials {
  tenant_id: string;
  client_id: string;
  client_secret: string;
  subscription_id?: string;
}

export interface IntegrationConnection {
  id: number;
  provider: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  last_verified_at?: string | null;
  account_id?: string | null;
  provider_tenant_id?: string | null;
  region?: string;
  profile_data?: Record<string, any>;
}

export function connectionStatus(connection?: IntegrationConnection): IntegrationStatus {
  if (!connection) return "DISCONNECTED";
  const status = connection.status.toUpperCase();
  if (["ACTIVE", "CONNECTED", "VERIFIED"].includes(status)) return "CONNECTED";
  if (status === "EXPIRED") return "EXPIRED";
  if (["ERROR", "FAILED", "REAUTH_REQUIRED"].includes(status)) return "ERROR";
  return "DISCONNECTED";
}

export function providerSortPriority(provider: ProviderDefinition, connections: IntegrationConnection[] = []): number {
  if (provider.availability === "manual") return 3;
  const status = connectionStatus(connections[0]);
  if (status === "CONNECTED") return 1;
  if (status === "DISCONNECTED") return 2;
  return 3;
}

export function sortProviders(providers: ProviderDefinition[], connectionsByProvider: Record<string, IntegrationConnection[]>): ProviderDefinition[] {
  return [...providers].sort((a, b) => providerSortPriority(a, connectionsByProvider[a.id]) - providerSortPriority(b, connectionsByProvider[b.id]) || a.name.localeCompare(b.name));
}

export const categoryLabels: Record<IntegrationCategory, string> = {
  cloud: "Cloud infrastructure",
  ai: "AI & LLM providers",
  productivity: "Productivity & collaboration",
  developer: "Developer tools",
  billing: "Billing & payments",
  custom: "Custom integrations",
};

export const providerRegistry: ProviderDefinition[] = [
  {
    id: "aws",
    name: "Amazon Web Services",
    category: "cloud",
    description: "Account identity, Free Tier details and Cost Explorer spend.",
    capabilities: ["Account identity", "Cost Explorer", "Free Tier"],
    availability: "available",
    icon: "aws",
    authType: "Credential verification",
    instructions: [
      "Use an AWS access key with sts:GetCallerIdentity and the read-only Cost Explorer permissions required by this workspace.",
      "The current backend verifies the identity and Cost Explorer access before storing an encrypted connection.",
    ],
    requiredFields: ["Access key ID", "Secret access key", "AWS region"],
    optionalFields: ["Session token"],
  },
  {
    id: "azure",
    name: "Microsoft Azure",
    category: "cloud",
    description: "Connect Azure subscriptions and centralize cloud spend.",
    capabilities: ["Subscriptions", "Usage", "Cost management"],
    availability: "available",
    icon: "azure",
    authType: "OAuth or service principal",
    instructions: [
      "Enter the Microsoft Entra tenant ID, application client ID, and client secret for your service principal.",
      "Azure access is verified server-side before credentials are encrypted and the connection is marked active.",
    ],
    requiredFields: ["Tenant ID", "Application client ID", "Client secret", "Azure subscription access"],
  },
  {
    id: "gcp",
    name: "Google Cloud Platform",
    category: "cloud",
    description: "Track projects, billing accounts and cloud consumption.",
    capabilities: ["Projects", "Billing", "Usage"],
    availability: "available",
    icon: "gcp",
    authType: "Service account JSON or API key",
    instructions: [
      "Provide a Google Cloud Project ID and Service Account Key (JSON) or API Key.",
      "UniSora validates project access before storing your encrypted credentials.",
    ],
    requiredFields: ["GCP Project ID", "Service Account Key or API Key"],
    optionalFields: ["Region"],
  },
  {
    id: "openai",
    name: "OpenAI / ChatGPT API",
    category: "ai",
    description: "Track OpenAI API usage separately from a ChatGPT subscription.",
    capabilities: ["API usage", "Models", "Spend"],
    availability: "available",
    icon: "openai",
    authType: "API key",
    instructions: [
      "OpenAI API access is separate from a ChatGPT subscription.",
      "UniSora verifies the key with OpenAI's read-only List Models endpoint before saving an encrypted connection.",
    ],
    requiredFields: ["OpenAI API key"],
    optionalFields: ["Workspace or project"],
  },
  {
    id: "anthropic",
    name: "Anthropic Claude",
    category: "ai",
    description: "Verify and retain an Anthropic Claude API connection.",
    capabilities: ["API usage", "Models", "Spend"],
    availability: "available",
    icon: "anthropic",
    authType: "API key",
    instructions: [
      "Create an API key in the Anthropic Console.",
      "UniSora sends a minimal real Messages API request before storing the encrypted key.",
    ],
    requiredFields: ["Anthropic API key", "Supported Claude model"],
    optionalFields: ["Connection name"],
  },
  {
    id: "gemini",
    name: "Google Gemini",
    category: "ai",
    description: "Monitor Gemini API usage and spend through a verified API connection.",
    capabilities: ["API usage", "Models", "Spend"],
    availability: "available",
    icon: "gemini",
    authType: "API key or OAuth",
    instructions: [
      "Create a Gemini API key in Google AI Studio and enable the Generative Language API for its project.",
      "UniSora verifies the key with Gemini's read-only model list endpoint before saving it encrypted on the backend.",
    ],
    requiredFields: ["Gemini API key"],
  },
  {
    id: "microsoft-365",
    name: "Microsoft 365",
    category: "productivity",
    description: "Bring licenses, users and renewal context into UniSora.",
    capabilities: ["Licenses", "Users", "Renewals"],
    availability: "available",
    icon: "microsoft",
    authType: "Entra Tenant & Application credentials",
    instructions: [
      "Enter your Microsoft 365 / Entra Tenant ID and client credentials.",
      "UniSora validates tenant credentials and synchronizes license tiers.",
    ],
    requiredFields: ["Tenant ID", "Client Secret or Admin Token"],
    optionalFields: ["Primary Domain"],
  },
  {
    id: "google-workspace",
    name: "Google Workspace",
    category: "productivity",
    description: "Manage workspace seats and subscription visibility.",
    capabilities: ["Seats", "Subscriptions", "Usage"],
    availability: "available",
    icon: "google",
    authType: "Admin API Key or Service Account",
    instructions: [
      "Enter your Google Workspace primary domain and Admin API key or service credentials.",
      "UniSora verifies domain management access before encrypting credentials.",
    ],
    requiredFields: ["Primary Domain", "Admin API Key"],
    optionalFields: ["Admin Email"],
  },
  {
    id: "slack",
    name: "Slack",
    category: "productivity",
    description: "Monitor workspace plans and collaboration spend.",
    capabilities: ["Plans", "Seats", "Renewals"],
    availability: "available",
    icon: "slack",
    authType: "Bot User OAuth Token",
    instructions: [
      "Enter a Slack Bot User OAuth Token (starting with xoxb-) from your Slack App management portal.",
      "UniSora verifies workspace access, team identity, and member counts.",
    ],
    requiredFields: ["Slack Bot Token (xoxb-...)"],
  },
  {
    id: "github",
    name: "GitHub",
    category: "developer",
    description: "Track developer seats, plans and organization usage.",
    capabilities: ["Organizations", "Seats", "Usage"],
    availability: "available",
    icon: "github",
    authType: "Personal Access Token",
    instructions: [
      "Generate a GitHub Personal Access Token (classic or fine-grained) with read:user, repo, and read:org scopes.",
      "UniSora verifies your identity, repositories, and organization seats.",
    ],
    requiredFields: ["GitHub Personal Access Token"],
  },
  {
    id: "gitlab",
    name: "GitLab",
    category: "developer",
    description: "Track GitLab groups, seats, plans, and renewal details.",
    capabilities: ["Groups", "Seats", "Usage"],
    availability: "available",
    icon: "gitlab",
    authType: "Personal Access Token",
    instructions: [
      "Create a GitLab Personal Access Token with read_user and read_api scopes in User Settings > Access Tokens.",
      "UniSora validates user identity and group access.",
    ],
    requiredFields: ["GitLab Personal Access Token"],
  },
  {
    id: "stripe",
    name: "Stripe",
    category: "billing",
    description: "Connect billing data when the Stripe provider is enabled.",
    capabilities: ["Invoices", "Payments", "Revenue"],
    availability: "available",
    icon: "stripe",
    authType: "Secret or Restricted API Key",
    instructions: [
      "Obtain a Secret or Restricted API Key (starting with sk_ or rk_) from your Stripe Developers Dashboard.",
      "UniSora verifies account identity, currency, and balance without charging or modifying data.",
    ],
    requiredFields: ["Stripe API Key (sk_... or rk_...)"],
  },
];

export function getProvider(providerId: string): ProviderDefinition | undefined {
  return providerRegistry.find((provider) => provider.id === providerId);
}

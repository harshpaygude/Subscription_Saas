export type CreditExpiryState = "active" | "today" | "expired" | "unavailable";

export interface CreditExpiryDisplay {
  state: CreditExpiryState;
  days: number | null;
  label: string;
}

/**
 * Calculate calendar-day expiry text from the provider's raw ISO date.
 * Both dates are normalized to UTC midnight so the result is stable across
 * browser time zones and does not depend on the time the API was called.
 */
export function creditExpiryDisplay(expirationDate: string | null | undefined, now = new Date()): CreditExpiryDisplay {
  if (!expirationDate) return { state: "unavailable", days: null, label: "Expiration date unavailable" };

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(expirationDate);
  if (!match) return { state: "unavailable", days: null, label: "Expiration date unavailable" };

  const expirationUtc = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  const today = new Date(now);
  const todayUtc = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  const days = Math.round((expirationUtc - todayUtc) / 86_400_000);

  if (days === 0) return { state: "today", days: 0, label: "Expires today" };
  if (days < 0) {
    const elapsed = Math.abs(days);
    return { state: "expired", days, label: `Expired ${elapsed} day${elapsed === 1 ? "" : "s"} ago` };
  }
  return { state: "active", days, label: `${days} day${days === 1 ? "" : "s"} remaining` };
}

export function creditCapabilityLabel(capability: "supported" | "additional-permissions" | "not-available" | "coming-soon" | "not-applicable") {
  switch (capability) {
    case "supported": return "Supported";
    case "additional-permissions": return "Supported with additional permissions";
    case "not-available": return "Not available for this account";
    case "coming-soon": return "Coming soon";
    case "not-applicable": return "Not applicable";
  }
}

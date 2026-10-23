import { ArrowRight, BarChart3, Bell, CalendarClock, CircleDollarSign, FileText, Receipt, Settings, WalletCards } from "lucide-react";
import Link from "next/link";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";

const icons = { subscriptions: CalendarClock, usage: CircleDollarSign, billing: Receipt, reports: BarChart3, alerts: Bell };
const copy = {
  subscriptions: ["Subscriptions", "Keep recurring services and renewal dates in one place.", "Subscription records are not exposed by the current backend yet."],
  usage: ["Usage & costs", "Understand provider usage and spend from verified connector data.", "Usage and cost data is available within provider details when that provider supports it. Cross-provider reporting is not available yet."],
  billing: ["Billing", "Manage UniSora billing separately from connected provider expenses.", "UniSora billing, invoices, payment methods, and plans are not implemented in the current backend."],
  reports: ["Reports & analytics", "Turn verified subscription and provider data into useful decisions.", "Reports require subscription and billing APIs that are not enabled in the current backend."],
  alerts: ["Alerts", "Review renewal, usage, integration, and billing events.", "Alert records and alert rules are not implemented in the current backend."],
} as const;

export function CapabilityPage({ kind }: { kind: keyof typeof copy }) {
  const [title, description, message] = copy[kind];
  const Icon = icons[kind];
  return <DashboardFrame title={title} description={description}><section className="hub-section"><div className="hub-coming-soon-panel"><Icon size={28} /><div><p className="hub-eyebrow">Backend capability status</p><h2>{message.includes("not available") || message.includes("not implemented") ? "Not available yet" : "Coming soon"}</h2><p>{message}</p></div></div></section><section className="hub-section hub-secondary-sections"><Link className="hub-mini-section" href="/dashboard/integrations"><WalletCards size={20} /><div><h3>Connect a service</h3><p>Open the integration catalog to connect a supported provider.</p></div><ArrowRight size={16} /></Link><Link className="hub-mini-section" href="/dashboard/settings"><Settings size={20} /><div><h3>Workspace settings</h3><p>Manage your profile and security preferences.</p></div><ArrowRight size={16} /></Link></section></DashboardFrame>;
}

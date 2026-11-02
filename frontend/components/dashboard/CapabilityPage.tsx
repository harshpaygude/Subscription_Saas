import { ArrowRight, BarChart3, Bell, CalendarClock, CircleDollarSign, FileText, Receipt, Settings, WalletCards } from "lucide-react";
import Link from "next/link";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";

const icons = { subscriptions: CalendarClock, usage: CircleDollarSign, billing: Receipt, reports: BarChart3, alerts: Bell };
const copy = {
  subscriptions: ["Subscriptions", "Keep recurring services and renewal dates in one place.", "Subscription records, renewal tracking, license capacity, and employee assignments are available now."],
  usage: ["Usage & costs", "Understand provider usage and spend from verified connector data.", "Usage and cost data is available from connected providers, manual cost entries, and persisted subscription records."],
  billing: ["Billing", "Manage UniSora billing separately from connected provider expenses.", "Use persisted subscription records, normalized costs, and provider billing views to manage billing data."],
  reports: ["Reports & analytics", "Turn verified subscription and provider data into useful decisions.", "Live organization-scoped analytics are available from subscription, department, employee, and asset data."],
  alerts: ["Alerts", "Review renewal, usage, integration, and billing events.", "Live alerts are generated from persisted renewal and workspace events."],
} as const;

export function CapabilityPage({ kind }: { kind: keyof typeof copy }) {
  const [title, description, message] = copy[kind];
  const Icon = icons[kind];
  return <DashboardFrame title={title} description={description}><section className="hub-section"><div className="hub-coming-soon-panel"><Icon size={28} /><div><p className="hub-eyebrow">Live workspace capability</p><h2>Ready to use</h2><p>{message}</p></div></div></section><section className="hub-section hub-secondary-sections"><Link className="hub-mini-section" href="/dashboard/integrations"><WalletCards size={20} /><div><h3>Connect or track a service</h3><p>Open the integration catalog to connect a native provider or track any service manually.</p></div><ArrowRight size={16} /></Link><Link className="hub-mini-section" href="/dashboard/settings"><Settings size={20} /><div><h3>Workspace settings</h3><p>Manage your profile and security preferences.</p></div><ArrowRight size={16} /></Link></section></DashboardFrame>;
}

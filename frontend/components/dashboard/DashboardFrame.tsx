"use client";

import { useEffect, useState } from "react";
import { Bell, ChevronDown, LogOut, Menu, Plug, Settings, ShieldCheck, Sparkles, WalletCards, LayoutDashboard, CircleDollarSign } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { getCurrentUser, getOrganization, logout, type Organization, type User } from "@/lib/api";

export const dashboardNavigation = [
  { label: "Overview", href: "/dashboard/overview", icon: LayoutDashboard },
  { label: "All services", href: "/dashboard/integrations", icon: Plug },
  { label: "Subscriptions", href: "/dashboard/subscriptions", icon: WalletCards },
  { label: "Usage & costs", href: "/dashboard/usage", icon: CircleDollarSign },
  { label: "Billing", href: "/dashboard/billing", icon: WalletCards },
  { label: "Reports & analytics", href: "/dashboard/reports", icon: Sparkles },
  { label: "Alerts", href: "/dashboard/alerts", icon: Bell },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
];

export interface DashboardSession { user: User; organization: Organization | null; }

interface Props { title: string; description: string; children: React.ReactNode; onAddIntegration?: () => void; }

export function DashboardFrame({ title, description, children, onAddIntegration }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<DashboardSession | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const user = await getCurrentUser();
        const organization = await getOrganization(user.organization_id);
        if (!cancelled) setSession({ user, organization });
      } catch (error) {
        if (!cancelled) {
          localStorage.removeItem("access_token");
          router.replace(`/login?reason=${error instanceof Error ? "session-expired" : "auth-required"}`);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [router]);

  if (!session) return <div className="hub-loading-screen"><div className="hub-spinner" /> Loading your workspace…</div>;
  const initial = (session.user.display_name || session.user.email || "S").slice(0, 1).toUpperCase();
  const workspace = session.organization?.name || "Workspace";
  const active = (href: string) => pathname === href || (href === "/dashboard/overview" && pathname === "/dashboard");

  return <main className="hub-shell">
    <aside className={`hub-sidebar ${mobileNav ? "open" : ""}`}>
      <div className="hub-brand"><span className="hub-brand-mark">U</span><div><strong>UniSora</strong><small>Subscription intelligence</small></div></div>
      <nav className="hub-nav" aria-label="Primary navigation">
        <p>Workspace</p>
        {dashboardNavigation.slice(0, 4).map(({ label, href, icon: Icon }) => <Link key={href} className={active(href) ? "active" : ""} href={href} onClick={() => setMobileNav(false)}><Icon size={17} /> {label}{label === "All services" && <span>12</span>}</Link>)}
        <p>Manage</p>
        {dashboardNavigation.slice(4).map(({ label, href, icon: Icon }) => <Link key={href} className={active(href) ? "active" : ""} href={href} onClick={() => setMobileNav(false)}><Icon size={17} /> {label}</Link>)}
      </nav>
      <div className="hub-sidebar-footer"><div className="hub-security-note"><ShieldCheck size={16} /><span>Private workspace<br /><small>Provider data stays scoped to you</small></span></div><button className="hub-user-row" onClick={() => setProfileOpen((value) => !value)}><span className="hub-avatar">{initial}</span><span><strong>{session.user.display_name || session.user.email}</strong><small>{workspace}</small></span><ChevronDown size={15} /></button></div>
    </aside>
    <section className="hub-main">
      <header className="hub-header"><div className="hub-header-title"><button className="hub-mobile-menu" onClick={() => setMobileNav((value) => !value)} aria-label="Toggle navigation"><Menu size={20} /></button><div><p className="hub-eyebrow">{workspace}</p><h1>{title}</h1><p className="hub-header-description">{description}</p></div></div><div className="hub-header-actions"><button className="hub-icon-action" aria-label="Notifications" onClick={() => router.push("/dashboard/alerts")}><Bell size={18} /></button>{onAddIntegration && <button className="hub-primary-button" onClick={onAddIntegration}><Plug size={16} /> Add integration</button>}<div className="hub-popover-wrap"><button className="hub-user-trigger" onClick={() => setProfileOpen((value) => !value)}><span className="hub-avatar">{initial}</span><ChevronDown size={15} /></button>{profileOpen && <div className="hub-popover hub-profile-popover"><strong>{session.user.display_name || session.user.email}</strong><span>{workspace}</span><button onClick={() => logout()}><LogOut size={15} /> Sign out</button></div>}</div></div></header>
      {notice && <div className="hub-content"><div className="hub-notice" role="status">{notice}</div></div>}
      <div className="hub-content">{children}<footer className="hub-footer">UniSora · {workspace}<span>Integration data is scoped to your signed-in account.</span></footer></div>
    </section>
  </main>;
}

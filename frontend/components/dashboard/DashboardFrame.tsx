"use client";

import { useEffect, useState, useRef } from "react";
import {
  Bell,
  ChevronDown,
  ChevronRight,
  LogOut,
  Menu,
  Plug,
  Settings,
  ShieldCheck,
  Sparkles,
  WalletCards,
  LayoutDashboard,
  CircleDollarSign,
  Users,
  Laptop,
  UserRoundCheck,
  X,
  Search,
  ExternalLink,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { getCurrentUser, getOrganization, logout, type Organization, type User } from "@/lib/api";
import { ThemeToggle } from "@/components/theme/ThemeToggle";

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  badge?: string | number;
}

export const workspaceNav: NavItem[] = [
  { label: "Overview", href: "/dashboard/overview", icon: LayoutDashboard },
  { label: "All Services", href: "/dashboard/integrations", icon: Plug, badge: "12" },
  { label: "Subscriptions", href: "/dashboard/subscriptions", icon: WalletCards },
  { label: "IT Assets", href: "/dashboard/assets", icon: Laptop },
  { label: "Usage & Costs", href: "/dashboard/usage", icon: CircleDollarSign },
  { label: "Billing", href: "/dashboard/billing", icon: WalletCards },
];

export const manageNav: NavItem[] = [
  { label: "Departments", href: "/dashboard/departments", icon: Users },
  { label: "Employee Lifecycle", href: "/dashboard/employees", icon: UserRoundCheck },
  { label: "Reports & Analytics", href: "/dashboard/reports", icon: Sparkles },
  { label: "Alerts", href: "/dashboard/alerts", icon: Bell },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
];

export interface DashboardSession {
  user: User;
  organization: Organization | null;
}

interface Props {
  title: string;
  description: string;
  children: React.ReactNode;
  onAddIntegration?: () => void;
  actions?: React.ReactNode;
}

export function DashboardFrame({ title, description, children, onAddIntegration, actions }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<DashboardSession | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const user = await getCurrentUser();
        const organization = await getOrganization(user.organization_id);
        if (!organization?.onboarding_completed && !sessionStorage.getItem("skip_onboarding")) {
          if (!cancelled) {
            router.replace("/onboarding");
            return;
          }
        }
        if (!cancelled) setSession({ user, organization });
      } catch (error) {
        if (!cancelled) {
          localStorage.removeItem("access_token");
          router.replace(`/login?reason=${error instanceof Error ? "session-expired" : "auth-required"}`);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!session) {
    return (
      <div className="hub-loading-screen">
        <div className="hub-spinner" />
        <span>Loading your UniSora workspace…</span>
      </div>
    );
  }

  const initial = (session.user.display_name || session.user.email || "U").slice(0, 1).toUpperCase();
  const workspaceName = session.organization?.name || "Workspace";
  const userRole = session.user.role || "Member";

  const isActive = (href: string) => {
    if (href === "/dashboard/overview") {
      return pathname === "/dashboard/overview" || pathname === "/dashboard";
    }
    return pathname.startsWith(href);
  };

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-is-collapsed" : ""}`}>
      {/* Mobile Backdrop */}
      {mobileNav && (
        <div
          className="mobile-backdrop"
          onClick={() => setMobileNav(false)}
          aria-hidden="true"
        />
      )}

      {/* Modern Enterprise Sidebar */}
      <aside className={`app-sidebar ${mobileNav ? "is-open" : ""}`}>
        {/* Brand Header */}
        <div className="sidebar-brand">
          <Link href="/dashboard/overview" className="brand-link">
            <div className="brand-logo-mark">
              <span>U</span>
            </div>
            <div className="brand-text">
              <div className="brand-title-row">
                <span className="brand-name">UniSora</span>
                <span className="brand-badge">PRO</span>
              </div>
              <span className="brand-subtitle">Subscription SaaS</span>
            </div>
          </Link>
          <button
            type="button"
            className="mobile-close-btn"
            onClick={() => setMobileNav(false)}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation Groups */}
        <nav className="sidebar-nav" aria-label="Main Navigation">
          <div className="nav-group">
            <span className="nav-group-title">WORKSPACE</span>
            {workspaceNav.map(({ label, href, icon: Icon, badge }) => {
              const active = isActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`nav-link ${active ? "is-active" : ""}`}
                  onClick={() => setMobileNav(false)}
                >
                  <Icon size={18} className="nav-icon" />
                  <span className="nav-label">{label}</span>
                  {badge && <span className="nav-counter">{badge}</span>}
                  {active && <span className="nav-active-pill" />}
                </Link>
              );
            })}
          </div>

          <div className="nav-group">
            <span className="nav-group-title">MANAGE</span>
            {manageNav.map(({ label, href, icon: Icon }) => {
              const active = isActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`nav-link ${active ? "is-active" : ""}`}
                  onClick={() => setMobileNav(false)}
                >
                  <Icon size={18} className="nav-icon" />
                  <span className="nav-label">{label}</span>
                  {active && <span className="nav-active-pill" />}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Sidebar Footer with Organization Context & User Profile */}
        <div className="sidebar-footer">
          <div className="workspace-security-pill">
            <ShieldCheck size={14} className="security-icon" />
            <div className="security-text">
              <strong>Enterprise Encrypted</strong>
              <small>Scoped to {workspaceName}</small>
            </div>
          </div>

          <div className="user-profile-widget" ref={popoverRef}>
            <button
              type="button"
              className="user-profile-button"
              onClick={() => setProfileOpen((prev) => !prev)}
              aria-expanded={profileOpen}
              aria-label="User menu"
            >
              <div className="user-avatar-circle">{initial}</div>
              <div className="user-info-text">
                <span className="user-name">{session.user.display_name || session.user.email}</span>
                <span className="user-role">{userRole} · {workspaceName}</span>
              </div>
              <ChevronDown size={14} className={`user-chevron ${profileOpen ? "is-rotated" : ""}`} />
            </button>

            {profileOpen && (
              <div className="user-dropdown-popover">
                <div className="dropdown-header">
                  <strong>{session.user.display_name || session.user.email}</strong>
                  <span>{session.user.email}</span>
                  <div className="dropdown-org-badge">
                    <span>{workspaceName}</span>
                    <small>({userRole})</small>
                  </div>
                </div>
                <div className="dropdown-divider" />
                <Link
                  href="/dashboard/settings"
                  className="dropdown-item"
                  onClick={() => setProfileOpen(false)}
                >
                  <Settings size={15} />
                  <span>Account & Settings</span>
                </Link>
                <button
                  type="button"
                  className="dropdown-item is-danger"
                  onClick={() => {
                    setProfileOpen(false);
                    logout();
                  }}
                >
                  <LogOut size={15} />
                  <span>Sign out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="app-main-layout">
        {/* Modern Unified Header */}
        <header className="app-header">
          <div className="header-left">
            <button
              type="button"
              className="header-mobile-toggle"
              onClick={() => setMobileNav(true)}
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <div className="header-breadcrumbs">
              <span className="breadcrumb-workspace">{workspaceName}</span>
              <ChevronRight size={14} className="breadcrumb-separator" />
              <span className="breadcrumb-current">{title}</span>
            </div>
          </div>

          <div className="header-right">
            {/* Context Actions */}
            {actions}

            {onAddIntegration && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={onAddIntegration}
              >
                <Plug size={15} />
                <span>Add Integration</span>
              </button>
            )}

            {/* Quick Alert Bell */}
            <button
              type="button"
              className="header-icon-btn"
              onClick={() => router.push("/dashboard/alerts")}
              aria-label="Alerts and notifications"
              title="Alerts and notifications"
            >
              <Bell size={18} />
              <span className="notification-dot" />
            </button>

            {/* Global Theme Toggle */}
            <ThemeToggle className="header-theme-toggle" />

            {/* Header User Pill */}
            <div className="header-user-badge" onClick={() => router.push("/dashboard/settings")} title="Manage Settings">
              <span className="header-user-initial">{initial}</span>
            </div>
          </div>
        </header>

        {/* Content Body */}
        <main className="app-content-container">
          <div className="page-title-banner">
            <div>
              <h1 className="page-heading">{title}</h1>
              <p className="page-subheading">{description}</p>
            </div>
          </div>

          <div className="page-inner-content">
            {children}
          </div>

          {/* Unified Footer */}
          <footer className="app-footer">
            <div className="footer-left">
              <span>UniSora PRO</span>
              <span className="footer-dot">·</span>
              <span>{workspaceName}</span>
            </div>
            <div className="footer-right">
              <span>Subscription SaaS Intelligence</span>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

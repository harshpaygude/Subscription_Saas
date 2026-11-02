"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, ChevronDown, ChevronRight, Menu, Plus, Search, X, ArrowUpRight, CreditCard, Wallet, PiggyBank, Layers3, LogOut, LayoutDashboard, Settings, Plug, Users, ReceiptText } from "lucide-react";
import { getCurrentUser, getOrganization, logout } from "@/lib/api";

type Subscription = { id: number; name: string; category: string; amount: number; renewal: string; color: string; initials: string };
const initialSubscriptions: Subscription[] = [
  { id: 1, name: "OpenAI", category: "AI & APIs", amount: 2499, renewal: "Oct 14, 2026", color: "#e8f8ef", initials: "O" },
  { id: 2, name: "Amazon Web Services", category: "Cloud", amount: 7400, renewal: "Oct 16, 2026", color: "#fff0df", initials: "A" },
  { id: 3, name: "Figma", category: "Software", amount: 2120, renewal: "Oct 19, 2026", color: "#f4eaff", initials: "F" },
  { id: 4, name: "Netflix", category: "Entertainment", amount: 1850, renewal: "Oct 21, 2026", color: "#ffe9eb", initials: "N" },
  { id: 5, name: "Other services", category: "Other", amount: 1132, renewal: "Oct 25, 2026", color: "#eeeaff", initials: "+" },
];
const categoryColors: Record<string, string> = { "AI & APIs": "#655ff4", Cloud: "#10b981", Software: "#f59e0b", Entertainment: "#ef4444", Other: "#8b5cf6" };
const currency = (amount: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [organization, setOrganization] = useState<any>(null);
  const [subscriptions, setSubscriptions] = useState(initialSubscriptions);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState("Software");
  const [newAmount, setNewAmount] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    async function loadUser() {
      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        const org = await getOrganization(currentUser.organization_id);
        setOrganization(org);
      } catch (error) {
        console.error(error);
        localStorage.removeItem("access_token");
        router.replace("/login");
      } finally { setLoading(false); }
    }
    loadUser();
  }, [router]);

  const total = subscriptions.reduce((sum, item) => sum + item.amount, 0);
  const filtered = useMemo(() => subscriptions.filter(s => `${s.name} ${s.category}`.toLowerCase().includes(search.toLowerCase())), [subscriptions, search]);
  const categoryTotals = Object.keys(categoryColors).map(category => ({ category, amount: subscriptions.filter(s => s.category === category).reduce((sum, s) => sum + s.amount, 0), color: categoryColors[category] })).filter(x => x.amount > 0);
  const donut = categoryTotals.reduce((acc, item) => { const start = acc.end; const end = start + item.amount / (total || 1) * 100; acc.parts.push(`${item.color} ${start}% ${end}%`); acc.end = end; return acc; }, { end: 0, parts: [] as string[] });

  function addSubscription(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amount = Number(newAmount);
    if (!newName.trim() || !amount || amount < 0) return;
    setSubscriptions(current => [...current, { id: Date.now(), name: newName.trim(), category: newCategory, amount, renewal: "Not set", color: "#f1f0ff", initials: newName.trim().slice(0, 1).toUpperCase() }]);
    setNewName(""); setNewAmount(""); setNewCategory("Software"); setShowAdd(false);
    setNotice("Subscription added to this dashboard demo.");
    window.setTimeout(() => setNotice(""), 3500);
  }

  if (loading) return <div className="loading-screen">Loading your workspace...</div>;

  return <main className="sh-page">
    <header className="sh-topbar">
      <div className="sh-heading"><button className="sh-icon-button sh-menu-button" aria-label="Toggle navigation" onClick={() => setMobileNav(v => !v)}><Menu size={22}/></button><div><h1>Dashboard</h1><p>Here&apos;s what&apos;s happening with your subscriptions.</p></div></div>
      <div className="sh-top-actions"><label className="sh-search"><Search size={19}/><input aria-label="Search subscriptions" placeholder="Search subscriptions..." value={search} onChange={e => setSearch(e.target.value)}/><kbd>⌘K</kbd></label><div className="sh-pop-wrap"><button className="sh-icon-button sh-bell" aria-label="Notifications" onClick={() => setShowNotifications(v => !v)}><Bell size={21}/><i/></button>{showNotifications && <div className="sh-popover"><strong>Notifications</strong><p>You&apos;re all caught up.</p><small>Renewals and billing alerts will appear here.</small></div>}</div><button className="sh-add-button" onClick={() => setShowAdd(true)}><Plus size={18}/> Add Subscription</button><div className="sh-pop-wrap"><button className="sh-user-menu" onClick={() => setShowProfile(v => !v)}><span className="sh-avatar">{user?.email?.slice(0,1).toUpperCase() || "U"}</span><ChevronDown size={16}/></button>{showProfile && <div className="sh-popover sh-profile-pop"><strong>{user?.email}</strong><span>{organization?.name || "Your workspace"}</span><button onClick={() => logout()}><LogOut size={15}/> Sign out</button></div>}</div></div>
    </header>
    {mobileNav && <nav className="sh-mobile-nav"><a className="active" href="/dashboard"><LayoutDashboard size={17}/>Dashboard</a><a href="#subscriptions"><ReceiptText size={17}/>Subscriptions</a><a href="#services" onClick={e => {e.preventDefault(); setNotice("Service integrations are the next step to connect real provider data.");}}><Plug size={17}/>Services</a><a href="#settings" onClick={e => {e.preventDefault(); setNotice(`Workspace: ${organization?.name || "UniSora"}`);}}><Settings size={17}/>Settings</a></nav>}
    <section className="sh-content">
      {notice && <div className="sh-notice">{notice}<button aria-label="Dismiss" onClick={() => setNotice("")}><X size={15}/></button></div>}
      <div className="sh-stats-grid">
        <article className="sh-stat-card"><span>Total Monthly Spend</span><strong>{currency(total)}</strong><small><b className="sh-green"><ArrowUpRight size={16}/> 8.4%</b> vs last month</small></article>
        <article className="sh-stat-card"><span>Active Subscriptions</span><strong>{subscriptions.length + 8}</strong><small><b className="sh-renewal">3 renewals</b> this week</small></article>
        <article className="sh-stat-card"><span>Upcoming Payments</span><strong>{currency(4280)}</strong><small>Next 7 days <button className="sh-inline-link" onClick={() => setNotice("Payment actions will be available when billing integrations are connected.")}>Pay now</button></small></article>
        <article className="sh-stat-card sh-savings"><span>Potential Savings</span><strong>{currency(3450)}</strong><small>Based on low usage</small></article>
      </div>
      <section className="sh-panel sh-spending-panel"><div className="sh-panel-header"><h2>Spending Breakdown</h2><span className="sh-total-pill">All ({(total / 1000).toFixed(1)}k)</span></div><div className="sh-spending-body"><div className="sh-donut-area"><div className="sh-donut" style={{ background: `conic-gradient(${donut.parts.join(", ")})` }}><div className="sh-donut-hole"><strong>{(total / 1000).toFixed(1)}k</strong><span>Total</span></div></div></div><div className="sh-legend">{categoryTotals.map(item => <div className="sh-legend-row" key={item.category}><span><i style={{ background: item.color }}/>{item.category}</span><strong>{currency(item.amount)}</strong></div>)}</div></div></section>
      <section className="sh-panel sh-recent-panel" id="subscriptions"><div className="sh-panel-header"><h2>Recent Subscriptions <span className="sh-count">{subscriptions.length + 8}</span></h2><button className="sh-view-all" onClick={() => setShowAll(v => !v)}>{showAll ? "Show less" : "View All"}<ChevronRight size={17}/></button></div><div className="sh-table-wrap"><table className="sh-table"><thead><tr><th>Service</th><th>Category</th><th>Monthly cost</th><th>Next renewal</th><th>Status</th></tr></thead><tbody>{(showAll ? filtered : filtered.slice(0, 5)).map(item => <tr key={item.id}><td><div className="sh-service"><span style={{ background: item.color }}>{item.initials}</span><strong>{item.name}</strong></div></td><td>{item.category}</td><td className="sh-amount">{currency(item.amount)}</td><td>{item.renewal}</td><td><span className="sh-status">Active</span></td></tr>)}{filtered.length === 0 && <tr><td colSpan={5} className="sh-empty">No subscriptions match “{search}”.</td></tr>}</tbody></table></div></section>
      <footer className="sh-footer">Workspace: <strong>{organization?.name || "UniSora"}</strong><span>Signed in as {user?.email}</span></footer>
    </section>
    {showAdd && <div className="sh-modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setShowAdd(false); }}><section className="sh-modal" role="dialog" aria-modal="true" aria-labelledby="sh-modal-title"><div className="sh-modal-heading"><div><h2 id="sh-modal-title">Add subscription</h2><p>Add a service to your dashboard.</p></div><button className="sh-icon-button" aria-label="Close" onClick={() => setShowAdd(false)}><X size={20}/></button></div><form onSubmit={addSubscription}><label>Service name<input value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Figma" required autoFocus/></label><label>Category<select value={newCategory} onChange={e => setNewCategory(e.target.value)}>{Object.keys(categoryColors).map(c => <option key={c}>{c}</option>)}</select></label><label>Monthly cost (₹)<input type="number" min="1" step="1" value={newAmount} onChange={e => setNewAmount(e.target.value)} placeholder="e.g. 1200" required/></label><div className="sh-modal-actions"><button type="button" className="sh-cancel-button" onClick={() => setShowAdd(false)}>Cancel</button><button type="submit" className="sh-add-button">Add subscription</button></div><small className="sh-demo-note">This currently adds to the local dashboard state. Persistent storage requires a backend subscriptions endpoint.</small></form></section></div>}
  </main>;
}

"use client";
import { useEffect, useState } from "react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { SettingsPanel } from "@/components/settings/SettingsPanel";
import { getCurrentUser, getOrganization, type Organization, type User } from "@/lib/api";
export default function SettingsPage() { const [user, setUser] = useState<User | null>(null); const [organization, setOrganization] = useState<Organization | null>(null); const [notice, setNotice] = useState(""); useEffect(() => { void getCurrentUser().then((value) => { setUser(value); return getOrganization(value.organization_id); }).then(setOrganization).catch(() => undefined); }, []); return <DashboardFrame title="Settings" description="Manage your account and security preferences.">{notice && <div className="hub-notice" role="status">{notice}</div>}{user ? <SettingsPanel user={user} organization={organization} onUserChange={setUser} onNotice={setNotice} /> : <div className="hub-loading-screen"><div className="hub-spinner" /> Loading settings…</div>}</DashboardFrame>; }

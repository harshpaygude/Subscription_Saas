"use client";

import { FormEvent, useState } from "react";
import { changePassword, logout, updateProfile, type Organization, type User } from "@/lib/api";

interface Props { user: User; organization: Organization | null; onUserChange: (user: User) => void; onNotice: (message: string) => void; }

export function SettingsPanel({ user, organization, onUserChange, onNotice }: Props) {
  const [displayName, setDisplayName] = useState(user.display_name || user.email.split("@")[0]);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    if (!displayName.trim()) return onNotice("Display name is required.");
    setSaving(true);
    try { onUserChange(await updateProfile({ display_name: displayName.trim() })); onNotice("Profile updated."); }
    catch (error) { onNotice(error instanceof Error ? error.message : "Could not update profile."); }
    finally { setSaving(false); }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    if (newPassword.length < 8) return onNotice("New password must be at least 8 characters.");
    if (newPassword !== confirmPassword) return onNotice("New password and confirmation do not match.");
    setSaving(true);
    try { await changePassword({ current_password: currentPassword, new_password: newPassword, confirm_password: confirmPassword }); setCurrentPassword(""); setNewPassword(""); setConfirmPassword(""); onNotice("Password changed successfully."); }
    catch (error) { onNotice(error instanceof Error ? error.message : "Could not change password."); }
    finally { setSaving(false); }
  }

  return <section className="hub-section hub-settings" id="settings">
    <div className="hub-section-heading"><div><p className="hub-eyebrow">Workspace controls</p><h2>Settings</h2><p>Manage your account and security preferences.</p></div></div>
    <div className="hub-settings-grid">
      <form className="hub-settings-card" onSubmit={saveProfile}><h3>Account</h3><p>Update the profile information shown across UniSora.</p>
        <label>Display name<input value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={255} /></label>
        <label>Email<input value={user.email} readOnly /></label>
        <label>Role<input value={user.role} readOnly /></label>
        <label>Organization<input value={organization?.name || "—"} readOnly /></label>
        <small>Member since {new Date(user.created_at).toLocaleDateString()}</small>
        <button className="hub-primary-button small" disabled={saving}>Save profile</button>
      </form>
      <form className="hub-settings-card" onSubmit={savePassword}><h3>Security</h3><p>Passwords are verified and hashed on the server.</p>
        <label>Current password<input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} autoComplete="current-password" required /></label>
        <label>New password<input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} minLength={8} autoComplete="new-password" required /></label>
        <label>Confirm new password<input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} minLength={8} autoComplete="new-password" required /></label>
        <button className="hub-primary-button small" disabled={saving}>Change password</button>
        <button type="button" className="hub-secondary-button small" onClick={() => { if (window.confirm("Sign out of this session?")) logout(); }}>Sign out</button>
      </form>
      <div className="hub-settings-card"><h3>Preferences</h3><p>Theme preference is saved locally on this device.</p><p className="hub-settings-muted">Notification preferences and active-session management are not supported by the current backend yet.</p></div>
    </div>
  </section>;
}

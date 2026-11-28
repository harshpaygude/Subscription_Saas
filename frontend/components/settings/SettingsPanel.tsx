"use client";

import { FormEvent, useState } from "react";
import {
  CheckCircle2,
  LogOut,
  Moon,
  Shield,
  Sun,
  User as UserIcon,
  Monitor,
} from "lucide-react";
import {
  changePassword,
  logout,
  updateProfile,
  type Organization,
  type User,
} from "@/lib/api";
import { useTheme } from "@/components/theme/ThemeProvider";

interface Props {
  user: User;
  organization: Organization | null;
  onUserChange: (user: User) => void;
  onNotice: (message: string) => void;
}

export function SettingsPanel({
  user,
  organization,
  onUserChange,
  onNotice,
}: Props) {
  const { theme, setTheme } = useTheme();

  const [activeTab, setActiveTab] = useState<"appearance" | "account" | "security">("appearance");
  const [displayName, setDisplayName] = useState(user.display_name || user.email.split("@")[0]);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    if (!displayName.trim()) {
      onNotice("Display name cannot be empty.");
      return;
    }
    setSavingProfile(true);
    try {
      const updated = await updateProfile({ display_name: displayName.trim() });
      onUserChange(updated);
      onNotice("Profile updated successfully.");
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Could not update profile.");
    } finally {
      setSavingProfile(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    if (newPassword.length < 8) {
      onNotice("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      onNotice("New password and confirmation do not match.");
      return;
    }
    setSavingPassword(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      onNotice("Password changed successfully.");
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Could not change password.");
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <div className="settings-layout-wrapper">
      {/* Settings Navigation Tabs */}
      <div className="settings-tabs-bar" role="tablist" aria-label="Settings sections">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "appearance"}
          className={`settings-tab-btn ${activeTab === "appearance" ? "is-active" : ""}`}
          onClick={() => setActiveTab("appearance")}
        >
          <Monitor size={16} />
          <span>Display Mode</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "account"}
          className={`settings-tab-btn ${activeTab === "account" ? "is-active" : ""}`}
          onClick={() => setActiveTab("account")}
        >
          <UserIcon size={16} />
          <span>Account Profile</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "security"}
          className={`settings-tab-btn ${activeTab === "security" ? "is-active" : ""}`}
          onClick={() => setActiveTab("security")}
        >
          <Shield size={16} />
          <span>Security &amp; Passwords</span>
        </button>
      </div>

      {/* Tab 1: Unified Dual-Mode Display */}
      {activeTab === "appearance" && (
        <div className="settings-tab-content space-y-6">
          <section className="dashboard-content-card">
            <div className="card-header-bar">
              <div>
                <span className="section-eyebrow">UNISORA LIQUID GLASS SYSTEM</span>
                <h2 className="card-heading">Display Mode</h2>
                <p className="card-subheading">
                  Switch between Light Surface and Ink Black modes with the unified Electric Lime &amp; Liquid Glass interface.
                </p>
              </div>
            </div>

            <div className="theme-mode-selector-grid">
              <button
                type="button"
                className={`theme-mode-card ${theme === "light" ? "is-selected" : ""}`}
                onClick={() => {
                  setTheme("light");
                  onNotice("Light mode enabled.");
                }}
              >
                <div className="mode-card-preview preview-light">
                  <div className="preview-topbar" />
                  <div className="preview-sidebar" />
                  <div className="preview-body">
                    <div className="preview-pill" />
                    <div className="preview-line" />
                  </div>
                </div>
                <div className="mode-card-info">
                  <Sun size={17} className="mode-icon text-warning" />
                  <div>
                    <strong>Light Mode</strong>
                    <small>Light Surface (#F1F3F9) · Brushed Silver · Electric Lime</small>
                  </div>
                  {theme === "light" && <CheckCircle2 size={18} className="mode-check text-accent" />}
                </div>
              </button>

              <button
                type="button"
                className={`theme-mode-card ${theme === "dark" ? "is-selected" : ""}`}
                onClick={() => {
                  setTheme("dark");
                  onNotice("Dark mode enabled.");
                }}
              >
                <div className="mode-card-preview preview-dark">
                  <div className="preview-topbar" />
                  <div className="preview-sidebar" />
                  <div className="preview-body">
                    <div className="preview-pill" />
                    <div className="preview-line" />
                  </div>
                </div>
                <div className="mode-card-info">
                  <Moon size={17} className="mode-icon text-accent" />
                  <div>
                    <strong>Dark Mode</strong>
                    <small>Ink Black (#030407) · Silver Glass · Electric Lime</small>
                  </div>
                  {theme === "dark" && <CheckCircle2 size={18} className="mode-check text-accent" />}
                </div>
              </button>
            </div>
          </section>
        </div>
      )}

      {/* Tab 2: Account Profile */}
      {activeTab === "account" && (
        <section className="dashboard-content-card">
          <div className="card-header-bar">
            <div>
              <span className="section-eyebrow">IDENTITY &amp; WORKSPACE</span>
              <h2 className="card-heading">Account Profile</h2>
              <p className="card-subheading">
                Update how your name appears to colleagues and administrative records.
              </p>
            </div>
          </div>

          <form onSubmit={saveProfile} className="space-y-4 max-w-lg">
            <div className="form-group">
              <label className="form-label">Display Name <span className="text-danger">*</span></label>
              <input
                type="text"
                className="form-input"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={255}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-input is-readonly"
                value={user.email}
                readOnly
              />
              <small className="form-label-help">Email is bound to your authentication provider.</small>
            </div>

            <div className="form-group">
              <label className="form-label">Organization Role</label>
              <input
                type="text"
                className="form-input is-readonly"
                value={user.role}
                readOnly
              />
            </div>

            <div className="form-group">
              <label className="form-label">Company Workspace</label>
              <input
                type="text"
                className="form-input is-readonly"
                value={organization?.name || "Independent"}
                readOnly
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={savingProfile}
              >
                {savingProfile ? "Saving…" : "Save Profile Changes"}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Tab 3: Security & Passwords */}
      {activeTab === "security" && (
        <section className="dashboard-content-card">
          <div className="card-header-bar">
            <div>
              <span className="section-eyebrow">AUTHENTICATION</span>
              <h2 className="card-heading">Change Password</h2>
              <p className="card-subheading">
                Passwords are cryptographically hashed and salted using bcrypt.
              </p>
            </div>
          </div>

          <form onSubmit={savePassword} className="space-y-4 max-w-lg">
            <div className="form-group">
              <label className="form-label">Current Password <span className="text-danger">*</span></label>
              <input
                type="password"
                className="form-input"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">New Password <span className="text-danger">*</span></label>
              <input
                type="password"
                className="form-input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                minLength={8}
                autoComplete="new-password"
                required
              />
              <small className="form-label-help">Must contain at least 8 characters.</small>
            </div>

            <div className="form-group">
              <label className="form-label">Confirm New Password <span className="text-danger">*</span></label>
              <input
                type="password"
                className="form-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                minLength={8}
                autoComplete="new-password"
                required
              />
            </div>

            <div className="flex-items-center gap-3 pt-2">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={savingPassword}
              >
                {savingPassword ? "Updating…" : "Update Password"}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  if (window.confirm("Sign out of your active UniSora session?")) {
                    logout();
                  }
                }}
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  );
}

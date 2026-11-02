"use client";

import { FormEvent, useState } from "react";
import {
  Check,
  CheckCircle2,
  Lock,
  LogOut,
  Moon,
  Palette,
  Shield,
  Sun,
  User as UserIcon,
  Sparkles,
} from "lucide-react";
import {
  changePassword,
  logout,
  updateProfile,
  type Organization,
  type User,
} from "@/lib/api";
import { ACCENT_PRESETS, AccentPreset } from "@/lib/theme";
import { useTheme } from "@/components/theme/ThemeProvider";
import { StatusBadge } from "@/components/ui/StatusBadge";

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
  const { theme, setTheme, accent, setAccent, isDark } = useTheme();

  const [activeTab, setActiveTab] = useState<"appearance" | "account" | "security">("appearance");
  const [displayName, setDisplayName] = useState(user.display_name || user.email.split("@")[0]);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [customHex, setCustomHex] = useState(accent);

  function handleSelectAccent(preset: AccentPreset) {
    setAccent(preset.hex);
    setCustomHex(preset.hex);
    onNotice(`Accent set to ${preset.name}.`);
  }

  function handleCustomColorChange(color: string) {
    setCustomHex(color);
    setAccent(color);
  }

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
      <div className="settings-tabs-bar">
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "appearance" ? "is-active" : ""}`}
          onClick={() => setActiveTab("appearance")}
        >
          <Palette size={16} />
          <span>Appearance & Theme</span>
        </button>
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "account" ? "is-active" : ""}`}
          onClick={() => setActiveTab("account")}
        >
          <UserIcon size={16} />
          <span>Account Profile</span>
        </button>
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "security" ? "is-active" : ""}`}
          onClick={() => setActiveTab("security")}
        >
          <Shield size={16} />
          <span>Security & Passwords</span>
        </button>
      </div>

      {/* Tab 1: Appearance & Theme */}
      {activeTab === "appearance" && (
        <div className="settings-tab-content space-y-6">
          {/* Mode Switch Card */}
          <section className="dashboard-content-card">
            <div className="card-header-bar">
              <div>
                <h3 className="card-heading">Interface Mode</h3>
                <p className="card-subheading">
                  Choose between high-contrast crisp light mode or eye-friendly dark mode.
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
                    <small>Crisp white surfaces with balanced contrast</small>
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
                  <Moon size={17} className="mode-icon text-info" />
                  <div>
                    <strong>Dark Mode</strong>
                    <small>Deep slate tones optimized for focused reading</small>
                  </div>
                  {theme === "dark" && <CheckCircle2 size={18} className="mode-check text-accent" />}
                </div>
              </button>
            </div>
          </section>

          {/* Global Accent Presets */}
          <section className="dashboard-content-card">
            <div className="card-header-bar">
              <div>
                <h3 className="card-heading">Primary Accent Color</h3>
                <p className="card-subheading">
                  Select a unified brand accent for buttons, active navigation, badges, focus rings, and metrics.
                </p>
              </div>
            </div>

            <div className="accent-presets-grid">
              {ACCENT_PRESETS.map((preset) => {
                const isSelected = accent.toUpperCase() === preset.hex.toUpperCase();
                return (
                  <button
                    key={preset.id}
                    type="button"
                    className={`accent-preset-card ${isSelected ? "is-selected" : ""}`}
                    onClick={() => handleSelectAccent(preset)}
                  >
                    <div
                      className="preset-swatch-circle"
                      style={{ backgroundColor: preset.hex }}
                    >
                      {isSelected && <Check size={16} className="preset-check" />}
                    </div>
                    <div className="preset-details">
                      <strong>{preset.name}</strong>
                      <span className="preset-hex">{preset.hex}</span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Custom Hex Selector */}
            <div className="custom-accent-row">
              <label htmlFor="custom-color-input" className="form-label inline-flex items-center gap-2">
                <span>Custom Accent Hex:</span>
              </label>
              <div className="custom-color-picker-wrap">
                <input
                  id="custom-color-input"
                  type="color"
                  value={customHex}
                  onChange={(e) => handleCustomColorChange(e.target.value)}
                  className="color-wheel-input"
                  title="Choose custom color"
                />
                <input
                  type="text"
                  value={customHex}
                  onChange={(e) => handleCustomColorChange(e.target.value)}
                  className="form-input custom-hex-text"
                  maxLength={7}
                  placeholder="#10B981"
                />
              </div>
            </div>

            {/* Live Component Preview */}
            <div className="accent-preview-box">
              <div className="preview-box-header">
                <Sparkles size={15} className="text-accent" />
                <span>Live Component Accent Preview</span>
              </div>
              <div className="preview-components-row">
                <button type="button" className="btn btn-primary btn-sm">
                  Primary Button
                </button>
                <button type="button" className="btn btn-secondary btn-sm">
                  Secondary Button
                </button>
                <div className="nav-preview-item">
                  <span className="nav-preview-pill" />
                  <span className="nav-preview-text">Active Nav Item</span>
                </div>
                <StatusBadge variant="accent" size="md">
                  Accent Status Badge
                </StatusBadge>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* Tab 2: Account Profile */}
      {activeTab === "account" && (
        <section className="dashboard-content-card">
          <div className="card-header-bar">
            <div>
              <h3 className="card-heading">Account Profile</h3>
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
              <h3 className="card-heading">Change Password</h3>
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

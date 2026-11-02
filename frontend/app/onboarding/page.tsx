"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Upload,
  FileSpreadsheet,
  Building2,
  Users,
  UserCheck,
  ChevronRight,
  ChevronLeft,
  Check,
  AlertCircle,
  Download,
  RefreshCw,
  CheckCircle,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Laptop,
  Zap,
  Globe,
  Mail,
  Phone,
  MapPin,
  Hash,
  Tag,
  CheckCircle2,
} from "lucide-react";
import {
  getCurrentUser,
  getOnboardingStatus,
  submitOnboarding,
  parseOnboardingExcel,
  type CompanyProfile,
  type DepartmentInput,
  type User,
  type ExcelImportResult,
} from "@/lib/api";
import { OnboardingProgress } from "@/components/onboarding/OnboardingProgress";
import { DepartmentEditor } from "@/components/onboarding/DepartmentEditor";

type Mode = "choose" | "excel" | "manual";
type ManualStep = 1 | 2 | 3 | 4;
type PreviewTab = "overview" | "company" | "departments" | "employees" | "assets";

const INDUSTRIES = [
  "Technology & Software",
  "Financial Services & Banking",
  "Healthcare & Life Sciences",
  "Retail & E-commerce",
  "Manufacturing & Industrial",
  "Consulting & Professional Services",
  "Media & Entertainment",
  "Education & EdTech",
  "Telecommunications",
  "Energy & Utilities",
  "Real Estate & Construction",
  "Transportation & Logistics",
  "Hospitality & Travel",
  "Non-Profit & Government",
  "Other",
];

const COMPANY_SIZES = [
  "1–10 employees",
  "11–50 employees",
  "51–200 employees",
  "201–500 employees",
  "501–1,000 employees",
  "1,001–5,000 employees",
  "5,000+ employees",
];

const PROGRESS_STEPS = [
  "Company profile",
  "Administrator",
  "Departments",
  "Review & confirm",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [mode, setMode] = useState<Mode>("choose");
  const [manualStep, setManualStep] = useState<ManualStep>(1);

  // Company profile state
  const [company, setCompany] = useState<CompanyProfile>({});
  const [adminTitle, setAdminTitle] = useState("Company Administrator");
  const [adminPhone, setAdminPhone] = useState("");
  const [departments, setDepartments] = useState<DepartmentInput[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [done, setDone] = useState(false);

  // Excel state
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [excelDragging, setExcelDragging] = useState(false);
  const [excelParsing, setExcelParsing] = useState(false);
  const [loadingSample, setLoadingSample] = useState(false);
  const [excelPreview, setExcelPreview] = useState<ExcelImportResult | null>(null);
  const [excelError, setExcelError] = useState("");
  const [previewTab, setPreviewTab] = useState<PreviewTab>("overview");

  // Check onboarding status and load user
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          router.replace("/login");
          return;
        }

        const user = await getCurrentUser();
        if (cancelled) return;
        setCurrentUser(user);

        // Prepopulate administrator contact and company email if available
        if (user.display_name) {
          setCompany((prev) => ({
            ...prev,
            company_email: prev.company_email || user.email,
          }));
        }

        const status = await getOnboardingStatus();
        if (status.onboarding_completed) {
          router.replace("/dashboard");
          return;
        }
      } catch (err) {
        if (!cancelled) {
          localStorage.removeItem("access_token");
          router.replace("/login");
          return;
        }
      }
      if (!cancelled) setChecking(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [router]);

  // Excel drag-and-drop
  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setExcelDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) await handleExcelFile(file);
  }, []);

  async function handleExcelFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".xlsx")) {
      setExcelError("Only .xlsx files are accepted.");
      return;
    }
    setExcelFile(file);
    setExcelError("");
    setExcelPreview(null);
    setExcelParsing(true);

    try {
      const preview = await parseOnboardingExcel(file);
      setExcelPreview(preview);
      setPreviewTab("overview");

      if (preview.company) {
        setCompany({
          legal_name: preview.company.legal_name || preview.company.company_name || undefined,
          display_name: preview.company.company_name || undefined,
          industry: preview.company.industry || undefined,
          company_size: preview.company.company_size || undefined,
          website: preview.company.website || undefined,
          company_email: preview.company.company_email || undefined,
          company_phone: preview.company.company_phone || undefined,
          country: preview.company.country || undefined,
          state: preview.company.state || undefined,
          city: preview.company.city || undefined,
          address: preview.company.address || undefined,
          postal_code: preview.company.postal_code || undefined,
          tax_registration_number: preview.company.tax_registration_number || undefined,
        });
      }
      if (preview.departments && preview.departments.length > 0) {
        setDepartments(preview.departments);
      }
    } catch (err) {
      setExcelError(err instanceof Error ? err.message : "Failed to parse workbook.");
    } finally {
      setExcelParsing(false);
    }
  }

  // Quick 1-click test with sample Excel file
  async function handleLoadSampleFile() {
    setLoadingSample(true);
    setExcelError("");
    try {
      const res = await fetch("/UniSora_PRO_Sample_Onboarding.xlsx");
      if (!res.ok) {
        throw new Error("Could not fetch sample workbook from server. Please upload it directly from the samples directory.");
      }
      const blob = await res.blob();
      const file = new File([blob], "UniSora_PRO_Sample_Onboarding.xlsx", {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      await handleExcelFile(file);
    } catch (err) {
      setExcelError(err instanceof Error ? err.message : "Failed to load sample workbook.");
    } finally {
      setLoadingSample(false);
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError("");

    try {
      await submitOnboarding({
        company,
        departments,
        employees: excelPreview?.employees || [],
        assets: excelPreview?.assets || [],
      });
      setDone(true);
      setTimeout(() => {
        router.replace("/dashboard");
      }, 2000);
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "Failed to submit onboarding. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  function updateCompany(field: keyof CompanyProfile, value: string) {
    setCompany((prev) => ({ ...prev, [field]: value.trim() ? value : undefined }));
  }

  if (checking) {
    return (
      <div className="ob-loading">
        <div className="ob-spinner" />
        <p>Checking workspace configuration…</p>
      </div>
    );
  }

  if (done) {
    return (
      <div className="ob-success-screen">
        <div className="ob-success-card">
          <div className="ob-success-icon-wrap">
            <CheckCircle size={52} className="ob-success-icon" />
          </div>
          <h2>Welcome to UniSora PRO!</h2>
          <p>
            Your organization workspace has been configured successfully. Taking you to your dashboard…
          </p>
          <div className="ob-success-bar" />
        </div>
      </div>
    );
  }

  return (
    <div className="ob-page">
      {/* Header */}
      <header className="ob-header">
        <div className="ob-header-brand">
          <div className="ob-header-logo">U</div>
          <div>
            <div className="ob-header-app">
              UniSora <span>PRO</span>
            </div>
            <div className="ob-header-sub">Company Setup Experience</div>
          </div>
        </div>

        <button
          className="ob-skip-btn"
          onClick={() => {
            sessionStorage.setItem("skip_onboarding", "1");
            router.replace("/dashboard");
          }}
          title="You can complete setup later in Settings"
        >
          Skip to dashboard
        </button>
      </header>

      <main className="ob-body">
        {/* ============================================================ */}
        {/* MODE: CHOOSE */}
        {/* ============================================================ */}
        {mode === "choose" && (
          <div className="ob-choose">
            <div className="ob-page-heading">
              <span className="ob-eyebrow">Workspace Configuration</span>
              <h1>Let&apos;s set up your company</h1>
              <p>
                Choose how you would like to set up your organization, teams, staff members, and IT hardware assets.
              </p>
            </div>

            <div className="ob-choose-cards">
              {/* Option A: Excel Import */}
              <button
                type="button"
                className="ob-choose-card"
                onClick={() => setMode("excel")}
              >
                <div className="ob-choose-icon ob-choose-icon-excel">
                  <FileSpreadsheet size={28} />
                </div>
                <div className="ob-choose-copy">
                  <div className="ob-choose-title-row">
                    <strong>Import company Excel workbook</strong>
                    <span className="ob-tag-recommended">Fastest & Complete</span>
                  </div>
                  <span>
                    Upload your company workbook to automatically extract and configure your company profile, departments, employee accounts, and IT assets in one step.
                  </span>
                  <div className="ob-choose-tags">
                    <span>.xlsx workbook</span>
                    <span>Extracts staff & assets</span>
                    <span>Sample workbook included</span>
                    <span>Live data preview</span>
                  </div>
                </div>
                <ChevronRight size={20} className="ob-choose-arrow" />
              </button>

              {/* Option B: Manual */}
              <button
                type="button"
                className="ob-choose-card"
                onClick={() => setMode("manual")}
              >
                <div className="ob-choose-icon ob-choose-icon-manual">
                  <Building2 size={28} />
                </div>
                <div className="ob-choose-copy">
                  <div className="ob-choose-title-row">
                    <strong>Enter company information manually</strong>
                  </div>
                  <span>
                    Fill in your organization details and configure your workspace step by step with our guided form.
                  </span>
                  <div className="ob-choose-tags">
                    <span>Guided 4-step wizard</span>
                    <span>Admin profile</span>
                    <span>Department editor</span>
                    <span>Instant review</span>
                  </div>
                </div>
                <ChevronRight size={20} className="ob-choose-arrow" />
              </button>
            </div>

            {/* Quick Demo Sample Callout */}
            <div
              className="ob-sample-banner"
              style={{ marginTop: 24, cursor: "pointer" }}
              onClick={() => {
                setMode("excel");
                setTimeout(handleLoadSampleFile, 150);
              }}
            >
              <div className="ob-sample-banner-left">
                <div className="ob-sample-banner-icon">
                  <Zap size={22} />
                </div>
                <div>
                  <div className="ob-sample-banner-title">
                    <strong>Want to test immediately?</strong>
                    <span className="ob-tag-demo">1-Click Test</span>
                  </div>
                  <p>
                    Test the complete extraction workflow with our pre-configured sample workbook (NovaTech Cloud / UniSora PRO). Extracts 6 departments, 6 employees, and 6 IT hardware assets!
                  </p>
                  <span className="ob-sample-path-hint">
                    File available in workspace: <code>UniSora_PRO_Sample_Onboarding.xlsx</code>
                  </span>
                </div>
              </div>
              <div className="ob-sample-banner-actions">
                <button
                  type="button"
                  className="ob-btn-sample-load"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMode("excel");
                    handleLoadSampleFile();
                  }}
                >
                  <Zap size={15} /> Instant Test
                </button>
              </div>
            </div>

            <div className="ob-security-callout">
              <ShieldCheck size={16} />
              <span>
                All organization details remain private to your workspace and encrypted in storage.
              </span>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* MODE: EXCEL IMPORT */}
        {/* ============================================================ */}
        {mode === "excel" && (
          <div className="ob-excel-flow">
            <div className="ob-back-row">
              <button
                type="button"
                className="ob-back-btn"
                onClick={() => {
                  setMode("choose");
                  setExcelPreview(null);
                  setExcelFile(null);
                  setExcelError("");
                }}
              >
                <ChevronLeft size={16} /> Back to options
              </button>
              <div className="ob-flow-title-wrap">
                <h2>Import Company & Organization Data</h2>
                <span className="ob-flow-badge">Auto-Extraction</span>
              </div>
            </div>

            {/* Sample File Banner with 1-click test button & download links */}
            <div className="ob-sample-banner">
              <div className="ob-sample-banner-left">
                <div className="ob-sample-banner-icon">
                  <FileSpreadsheet size={24} />
                </div>
                <div>
                  <div className="ob-sample-banner-title">
                    <strong>UniSora PRO Sample Onboarding Workbook</strong>
                    <span className="ob-tag-demo">Ready to test</span>
                  </div>
                  <p>
                    Use our pre-filled workbook to test full extraction: <strong>Company Details</strong>, <strong>6 Departments</strong>, <strong>6 Employees</strong>, and <strong>6 Hardware Assets</strong>.
                  </p>
                  <span className="ob-sample-path-hint">
                    Located in workspace: <code>UniSora_PRO_Sample_Onboarding.xlsx</code>
                  </span>
                </div>
              </div>

              <div className="ob-sample-banner-actions">
                <button
                  type="button"
                  className="ob-btn-sample-load"
                  onClick={handleLoadSampleFile}
                  disabled={loadingSample || excelParsing}
                  title="Directly load and parse the sample Excel file"
                >
                  {loadingSample || excelParsing ? (
                    <>
                      <div className="ob-spinner-sm" /> Loading…
                    </>
                  ) : (
                    <>
                      <Zap size={15} /> Load Demo Sample
                    </>
                  )}
                </button>

                <a
                  href="/UniSora_PRO_Sample_Onboarding.xlsx"
                  download="UniSora_PRO_Sample_Onboarding.xlsx"
                  className="ob-btn-sample-dl"
                  title="Download the full sample workbook to your computer"
                >
                  <Download size={14} /> Download .xlsx
                </a>

                <a
                  href="/api/organizations/me/onboarding/excel-template"
                  download="unisora_onboarding_template.xlsx"
                  className="ob-link-template"
                  title="Download an empty template with sheet definitions"
                >
                  Blank Template
                </a>
              </div>
            </div>

            {/* Upload drop zone */}
            {!excelPreview && (
              <div
                className={`ob-dropzone ${excelDragging ? "ob-dropzone-active" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setExcelDragging(true);
                }}
                onDragLeave={() => setExcelDragging(false)}
                onDrop={handleDrop}
                onClick={() => document.getElementById("ob-file-input")?.click()}
                role="button"
                tabIndex={0}
              >
                <input
                  id="ob-file-input"
                  type="file"
                  accept=".xlsx"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleExcelFile(file);
                  }}
                />
                <div className="ob-dropzone-icon">
                  {excelParsing ? <div className="ob-spinner" /> : <Upload size={32} />}
                </div>
                <strong>
                  {excelParsing
                    ? "Analyzing workbook & extracting data…"
                    : "Drop your company Excel workbook here"}
                </strong>
                <span>or click to browse your computer</span>
                <div className="ob-dropzone-features">
                  <span className="ob-feature-chip">
                    <Building2 size={12} /> Company Info
                  </span>
                  <span className="ob-feature-chip">
                    <Users size={12} /> Departments
                  </span>
                  <span className="ob-feature-chip">
                    <UserCheck size={12} /> Employees
                  </span>
                  <span className="ob-feature-chip">
                    <Laptop size={12} /> IT Hardware Assets
                  </span>
                </div>
                <span className="ob-dropzone-hint">Supports .xlsx up to 10 MB</span>
              </div>
            )}

            {excelError && (
              <div className="ob-alert ob-alert-error" role="alert">
                <AlertCircle size={16} />
                <span>{excelError}</span>
              </div>
            )}

            {/* Preview of parsed data */}
            {excelPreview && (
              <div className="ob-preview">
                {/* Header bar */}
                <div className="ob-preview-header">
                  <div className="ob-preview-file">
                    <FileSpreadsheet size={18} className="ob-file-icon" />
                    <strong>{excelFile?.name || "UniSora_PRO_Sample_Onboarding.xlsx"}</strong>
                    <span className="ob-badge-success">
                      <CheckCircle2 size={12} style={{ display: "inline", marginRight: 4 }} />
                      Parsed &amp; Validated
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      type="button"
                      className="ob-icon-btn"
                      onClick={handleLoadSampleFile}
                      disabled={loadingSample || excelParsing}
                    >
                      <Zap size={13} /> Re-load demo
                    </button>
                    <button
                      type="button"
                      className="ob-icon-btn"
                      onClick={() => {
                        setExcelPreview(null);
                        setExcelFile(null);
                      }}
                    >
                      <RefreshCw size={13} /> Change file
                    </button>
                  </div>
                </div>

                {/* Validation Errors */}
                {excelPreview.errors.length > 0 && (
                  <div className="ob-alert ob-alert-error ob-alert-list" role="alert">
                    <strong>
                      <AlertCircle size={15} /> Errors detected in workbook:
                    </strong>
                    <ul>
                      {excelPreview.errors.map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Validation Warnings */}
                {excelPreview.warnings.length > 0 && (
                  <div className="ob-alert ob-alert-warn ob-alert-list">
                    <strong>Notice / skipped items:</strong>
                    <ul>
                      {excelPreview.warnings.map((warn, i) => (
                        <li key={i}>{warn}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* KPI Summary Grid */}
                <div className="ob-kpi-grid">
                  <div className="ob-kpi-card" onClick={() => setPreviewTab("company")} style={{ cursor: "pointer" }}>
                    <div className="ob-kpi-icon-wrap ob-kpi-icon-org">
                      <Building2 size={20} />
                    </div>
                    <div>
                      <div className="ob-kpi-val">
                        {excelPreview.company?.company_name || excelPreview.company?.legal_name || "Company Profile"}
                      </div>
                      <div className="ob-kpi-sub">
                        {excelPreview.company?.industry || "Profile detected"}
                      </div>
                    </div>
                  </div>

                  <div className="ob-kpi-card" onClick={() => setPreviewTab("departments")} style={{ cursor: "pointer" }}>
                    <div className="ob-kpi-icon-wrap ob-kpi-icon-dept">
                      <Users size={20} />
                    </div>
                    <div>
                      <div className="ob-kpi-val">{excelPreview.department_count} Departments</div>
                      <div className="ob-kpi-sub">Cost centers &amp; teams</div>
                    </div>
                  </div>

                  <div className="ob-kpi-card" onClick={() => setPreviewTab("employees")} style={{ cursor: "pointer" }}>
                    <div className="ob-kpi-icon-wrap ob-kpi-icon-emp">
                      <UserCheck size={20} />
                    </div>
                    <div>
                      <div className="ob-kpi-val">{excelPreview.employee_count} Employees</div>
                      <div className="ob-kpi-sub">Accounts &amp; lifecycles</div>
                    </div>
                  </div>

                  <div className="ob-kpi-card" onClick={() => setPreviewTab("assets")} style={{ cursor: "pointer" }}>
                    <div className="ob-kpi-icon-wrap ob-kpi-icon-asset">
                      <Laptop size={20} />
                    </div>
                    <div>
                      <div className="ob-kpi-val">{excelPreview.asset_count} IT Assets</div>
                      <div className="ob-kpi-sub">Hardware &amp; assignments</div>
                    </div>
                  </div>
                </div>

                {/* Tab Navigation */}
                <div className="ob-tab-nav">
                  <button
                    type="button"
                    className={`ob-tab-btn ${previewTab === "overview" ? "ob-tab-btn-active" : ""}`}
                    onClick={() => setPreviewTab("overview")}
                  >
                    <Sparkles size={15} /> Overview
                  </button>
                  <button
                    type="button"
                    className={`ob-tab-btn ${previewTab === "company" ? "ob-tab-btn-active" : ""}`}
                    onClick={() => setPreviewTab("company")}
                  >
                    <Building2 size={15} /> Company Profile
                  </button>
                  <button
                    type="button"
                    className={`ob-tab-btn ${previewTab === "departments" ? "ob-tab-btn-active" : ""}`}
                    onClick={() => setPreviewTab("departments")}
                  >
                    <Users size={15} /> Departments{" "}
                    <span className="ob-tab-count">{excelPreview.department_count}</span>
                  </button>
                  <button
                    type="button"
                    className={`ob-tab-btn ${previewTab === "employees" ? "ob-tab-btn-active" : ""}`}
                    onClick={() => setPreviewTab("employees")}
                  >
                    <UserCheck size={15} /> Employees{" "}
                    <span className="ob-tab-count">{excelPreview.employee_count}</span>
                  </button>
                  <button
                    type="button"
                    className={`ob-tab-btn ${previewTab === "assets" ? "ob-tab-btn-active" : ""}`}
                    onClick={() => setPreviewTab("assets")}
                  >
                    <Laptop size={15} /> IT Assets{" "}
                    <span className="ob-tab-count">{excelPreview.asset_count}</span>
                  </button>
                </div>

                {/* ==================================================== */}
                {/* TAB 1: OVERVIEW */}
                {/* ==================================================== */}
                {previewTab === "overview" && (
                  <div className="ob-preview-summary">
                    {excelPreview.company && (
                      <div className="ob-preview-card">
                        <div className="ob-preview-card-title">
                          <Building2 size={16} />
                          <h4>Company Identity &amp; Location</h4>
                        </div>
                        <div className="ob-preview-grid">
                          <div>
                            <span>Legal entity name</span>
                            <strong>{excelPreview.company.legal_name || "—"}</strong>
                          </div>
                          <div>
                            <span>Trading / display name</span>
                            <strong>{excelPreview.company.company_name || "—"}</strong>
                          </div>
                          <div>
                            <span>Industry sector</span>
                            <strong>{excelPreview.company.industry || "—"}</strong>
                          </div>
                          <div>
                            <span>Company size</span>
                            <strong>{excelPreview.company.company_size || "—"}</strong>
                          </div>
                          <div>
                            <span>Location</span>
                            <strong>
                              {[excelPreview.company.city, excelPreview.company.state, excelPreview.company.country]
                                .filter(Boolean)
                                .join(", ") || "—"}
                            </strong>
                          </div>
                          <div>
                            <span>Primary contact</span>
                            <strong>{excelPreview.company.company_email || "—"}</strong>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Departments Summary Card */}
                    <div className="ob-preview-card">
                      <div className="ob-preview-card-title">
                        <Users size={16} />
                        <h4>
                          Departments ({excelPreview.department_count})
                        </h4>
                      </div>
                      <div className="ob-preview-chips">
                        {excelPreview.departments.map((dept, i) => (
                          <span key={i} className="ob-preview-chip">
                            {dept.name}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Employees Summary Card */}
                    {excelPreview.employee_count > 0 && (
                      <div className="ob-preview-card">
                        <div className="ob-preview-card-title">
                          <UserCheck size={16} />
                          <h4>
                            Staff Members ({excelPreview.employee_count} detected)
                          </h4>
                        </div>
                        <p className="ob-preview-note" style={{ marginBottom: 12 }}>
                          Initial user accounts and lifecycle entries will be provisioned directly into your workspace.
                        </p>
                        <div className="ob-preview-chips">
                          {excelPreview.employees.slice(0, 6).map((emp, i) => (
                            <span key={i} className="ob-feature-chip">
                              <strong>{emp.full_name}</strong> ({emp.department_name || "General"})
                            </span>
                          ))}
                          {excelPreview.employees.length > 6 && (
                            <span className="ob-preview-count">+{excelPreview.employees.length - 6} more</span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* IT Assets Summary Card */}
                    {excelPreview.asset_count > 0 && (
                      <div className="ob-preview-card">
                        <div className="ob-preview-card-title">
                          <Laptop size={16} />
                          <h4>
                            Hardware Assets ({excelPreview.asset_count} detected)
                          </h4>
                        </div>
                        <p className="ob-preview-note" style={{ marginBottom: 12 }}>
                          Devices will be added to your IT asset inventory and automatically linked to their assigned staff members.
                        </p>
                        <div className="ob-preview-chips">
                          {excelPreview.assets.slice(0, 6).map((asset, i) => (
                            <span key={i} className="ob-feature-chip">
                              <Tag size={11} style={{ marginRight: 4 }} />
                              <strong>{asset.asset_tag}</strong>: {asset.name}
                            </span>
                          ))}
                          {excelPreview.assets.length > 6 && (
                            <span className="ob-preview-count">+{excelPreview.assets.length - 6} more</span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ==================================================== */}
                {/* TAB 2: COMPANY PROFILE */}
                {/* ==================================================== */}
                {previewTab === "company" && excelPreview.company && (
                  <div className="ob-preview-card">
                    <div className="ob-preview-card-title">
                      <Building2 size={16} />
                      <h4>Extracted Company Profile</h4>
                    </div>
                    <div className="ob-preview-grid">
                      <div>
                        <span>Legal name</span>
                        <strong>{excelPreview.company.legal_name || "—"}</strong>
                      </div>
                      <div>
                        <span>Display / brand name</span>
                        <strong>{excelPreview.company.company_name || "—"}</strong>
                      </div>
                      <div>
                        <span>Industry sector</span>
                        <strong>{excelPreview.company.industry || "—"}</strong>
                      </div>
                      <div>
                        <span>Organization size</span>
                        <strong>{excelPreview.company.company_size || "—"}</strong>
                      </div>
                      <div>
                        <span>Official email</span>
                        <strong>{excelPreview.company.company_email || "—"}</strong>
                      </div>
                      <div>
                        <span>Telephone number</span>
                        <strong>{excelPreview.company.company_phone || "—"}</strong>
                      </div>
                      <div>
                        <span>Website</span>
                        <strong>
                          {excelPreview.company.website ? (
                            <a
                              href={excelPreview.company.website}
                              target="_blank"
                              rel="noreferrer"
                              style={{ color: "#059669" }}
                            >
                              {excelPreview.company.website}
                            </a>
                          ) : (
                            "—"
                          )}
                        </strong>
                      </div>
                      <div>
                        <span>Tax / VAT registration number</span>
                        <strong>{excelPreview.company.tax_registration_number || "—"}</strong>
                      </div>
                      <div style={{ gridColumn: "1 / -1" }}>
                        <span>Headquarters address</span>
                        <strong>
                          {[
                            excelPreview.company.address,
                            excelPreview.company.city,
                            excelPreview.company.state,
                            excelPreview.company.postal_code,
                            excelPreview.company.country,
                          ]
                            .filter(Boolean)
                            .join(", ") || "—"}
                        </strong>
                      </div>
                    </div>
                  </div>
                )}

                {/* ==================================================== */}
                {/* TAB 3: DEPARTMENTS */}
                {/* ==================================================== */}
                {previewTab === "departments" && (
                  <div className="ob-card-grid-depts">
                    {excelPreview.departments.map((dept, i) => {
                      const empCount = excelPreview.employees.filter(
                        (e) => e.department_name?.toLowerCase() === dept.name.toLowerCase()
                      ).length;
                      return (
                        <div key={i} className="ob-dept-box">
                          <div className="ob-dept-box-top">
                            <h4>{dept.name}</h4>
                            <span className="ob-badge-dept">
                              {empCount} {empCount === 1 ? "member" : "members"}
                            </span>
                          </div>
                          <p>{dept.description || "Active department unit."}</p>
                          <div className="ob-dept-box-meta">
                            <span>Auto-provisions in workspace</span>
                            <span style={{ color: "#059669", fontWeight: 600 }}>Active</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* ==================================================== */}
                {/* TAB 4: EMPLOYEES */}
                {/* ==================================================== */}
                {previewTab === "employees" && (
                  <div className="ob-table-wrapper">
                    <table className="ob-data-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Employee Name</th>
                          <th>Work Email</th>
                          <th>Department</th>
                          <th>Contact Phone</th>
                          <th>Joining Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {excelPreview.employees.map((emp, i) => {
                          const initials = emp.full_name
                            .split(" ")
                            .map((p) => p[0])
                            .slice(0, 2)
                            .join("")
                            .toUpperCase();
                          return (
                            <tr key={i}>
                              <td>
                                <span className="ob-tag-id">{emp.employee_id || `EMP-${100 + i}`}</span>
                              </td>
                              <td>
                                <div className="ob-user-cell">
                                  <div className="ob-avatar">{initials}</div>
                                  <strong>{emp.full_name}</strong>
                                </div>
                              </td>
                              <td style={{ color: "#059669", fontWeight: 500 }}>{emp.email}</td>
                              <td>
                                <span className="ob-badge-dept">{emp.department_name || "General"}</span>
                              </td>
                              <td>{emp.phone_number || "—"}</td>
                              <td>{emp.joining_date ? String(emp.joining_date).slice(0, 10) : "Today"}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* ==================================================== */}
                {/* TAB 5: IT HARDWARE ASSETS */}
                {/* ==================================================== */}
                {previewTab === "assets" && (
                  <div className="ob-table-wrapper">
                    <table className="ob-data-table">
                      <thead>
                        <tr>
                          <th>Asset Tag</th>
                          <th>Hardware / Device Name</th>
                          <th>Type</th>
                          <th>Model &amp; Serial</th>
                          <th>Cost</th>
                          <th>Assigned User</th>
                          <th>Location</th>
                        </tr>
                      </thead>
                      <tbody>
                        {excelPreview.assets.map((asset, i) => (
                          <tr key={i}>
                            <td>
                              <span className="ob-tag-id">{asset.asset_tag}</span>
                            </td>
                            <td>
                              <strong>{asset.name}</strong>
                            </td>
                            <td>
                              <span className="ob-badge-type">{asset.asset_type || "Hardware"}</span>
                            </td>
                            <td style={{ fontSize: 12, color: "#64748b" }}>
                              {asset.model || "—"}
                              {asset.serial_number && (
                                <span style={{ display: "block", color: "#94a3b8", fontFamily: "monospace" }}>
                                  S/N: {asset.serial_number}
                                </span>
                              )}
                            </td>
                            <td style={{ fontWeight: 600 }}>
                              {asset.purchase_cost
                                ? `$${Number(asset.purchase_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })} ${asset.currency || "USD"}`
                                : "—"}
                            </td>
                            <td>
                              {asset.assigned_to ? (
                                <span className="ob-badge-assigned">
                                  <UserCheck size={12} /> {asset.assigned_to}
                                </span>
                              ) : (
                                <span className="ob-badge-available">In Inventory</span>
                              )}
                            </td>
                            <td>{asset.location || "Headquarters"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Callout Summary */}
                <div className="ob-provision-callout">
                  <Sparkles size={20} color="#059669" />
                  <div>
                    <strong>Ready to provision:</strong> Finishing onboarding will establish your organization and initialize{" "}
                    <strong>{excelPreview.department_count} departments</strong>,{" "}
                    <strong>{excelPreview.employee_count} user accounts</strong>, and{" "}
                    <strong>{excelPreview.asset_count} IT hardware assets</strong> in your workspace database.
                  </div>
                </div>

                {/* Action Confirmation Button */}
                {excelPreview.valid && (
                  <button
                    type="button"
                    className="ob-confirm-btn"
                    onClick={handleSubmit}
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <span className="ob-btn-spinner" /> Initializing workspace &amp; provisioning data…
                      </>
                    ) : (
                      <>
                        <Check size={18} /> Confirm and finish onboarding
                      </>
                    )}
                  </button>
                )}

                {submitError && (
                  <div className="ob-alert ob-alert-error" style={{ marginTop: 14 }}>
                    <AlertCircle size={15} />
                    <span>{submitError}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* MODE: MANUAL ENTRY */}
        {/* ============================================================ */}
        {mode === "manual" && (
          <div className="ob-manual-flow">
            <div className="ob-back-row">
              <button
                type="button"
                className="ob-back-btn"
                onClick={() => setMode("choose")}
              >
                <ChevronLeft size={16} /> Back to options
              </button>
              <h2>Company onboarding</h2>
            </div>

            <OnboardingProgress
              step={manualStep}
              total={4}
              steps={PROGRESS_STEPS}
            />

            {/* ── STEP 1: Company Profile ──────────────────────────── */}
            {manualStep === 1 && (
              <div className="ob-section">
                <div className="ob-section-header">
                  <div className="ob-section-icon">
                    <Building2 size={20} />
                  </div>
                  <div>
                    <h3>Company information</h3>
                    <p>Enter the legal and operational details of your organization.</p>
                  </div>
                </div>

                <div className="ob-form-grid">
                  <div className="ob-field ob-field-full">
                    <label htmlFor="legal_name">
                      Registered company legal name <span className="ob-required">*</span>
                    </label>
                    <input
                      id="legal_name"
                      type="text"
                      placeholder="e.g. Acme Technologies Inc."
                      value={company.legal_name || ""}
                      onChange={(e) => updateCompany("legal_name", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="display_name">Trading / display name</label>
                    <input
                      id="display_name"
                      type="text"
                      placeholder="e.g. Acme"
                      value={company.display_name || ""}
                      onChange={(e) => updateCompany("display_name", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="industry">
                      Industry <span className="ob-required">*</span>
                    </label>
                    <select
                      id="industry"
                      value={company.industry || ""}
                      onChange={(e) => updateCompany("industry", e.target.value)}
                    >
                      <option value="">Select industry…</option>
                      {INDUSTRIES.map((ind) => (
                        <option key={ind} value={ind}>
                          {ind}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="ob-field">
                    <label htmlFor="company_size">
                      Company size <span className="ob-required">*</span>
                    </label>
                    <select
                      id="company_size"
                      value={company.company_size || ""}
                      onChange={(e) => updateCompany("company_size", e.target.value)}
                    >
                      <option value="">Select employee range…</option>
                      {COMPANY_SIZES.map((size) => (
                        <option key={size} value={size}>
                          {size}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="ob-field">
                    <label htmlFor="country">
                      Country <span className="ob-required">*</span>
                    </label>
                    <input
                      id="country"
                      type="text"
                      placeholder="e.g. United States"
                      value={company.country || ""}
                      onChange={(e) => updateCompany("country", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="company_email">
                      Official company email <span className="ob-required">*</span>
                    </label>
                    <input
                      id="company_email"
                      type="email"
                      placeholder="contact@company.com"
                      value={company.company_email || ""}
                      onChange={(e) => updateCompany("company_email", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="company_phone">
                      Company contact number <span className="ob-required">*</span>
                    </label>
                    <input
                      id="company_phone"
                      type="tel"
                      placeholder="+1 (555) 012-3456"
                      value={company.company_phone || ""}
                      onChange={(e) => updateCompany("company_phone", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="website">Company website</label>
                    <input
                      id="website"
                      type="url"
                      placeholder="https://example.com"
                      value={company.website || ""}
                      onChange={(e) => updateCompany("website", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="tax_registration_number">
                      Tax / VAT registration number
                    </label>
                    <input
                      id="tax_registration_number"
                      type="text"
                      placeholder="e.g. US123456789"
                      value={company.tax_registration_number || ""}
                      onChange={(e) =>
                        updateCompany("tax_registration_number", e.target.value)
                      }
                    />
                  </div>

                  <div className="ob-field ob-field-full">
                    <label htmlFor="address">Registered office address</label>
                    <input
                      id="address"
                      type="text"
                      placeholder="Suite 400, 100 Innovation Way"
                      value={company.address || ""}
                      onChange={(e) => updateCompany("address", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="city">City</label>
                    <input
                      id="city"
                      type="text"
                      placeholder="e.g. Austin"
                      value={company.city || ""}
                      onChange={(e) => updateCompany("city", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="state">State / Province / Region</label>
                    <input
                      id="state"
                      type="text"
                      placeholder="e.g. Texas"
                      value={company.state || ""}
                      onChange={(e) => updateCompany("state", e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="postal_code">Postal code</label>
                    <input
                      id="postal_code"
                      type="text"
                      placeholder="e.g. 78701"
                      value={company.postal_code || ""}
                      onChange={(e) => updateCompany("postal_code", e.target.value)}
                    />
                  </div>
                </div>

                {submitError && (
                  <div className="ob-alert ob-alert-error" style={{ marginTop: 14 }}>
                    <AlertCircle size={15} />
                    <span>{submitError}</span>
                  </div>
                )}

                <div className="ob-step-actions">
                  <div />
                  <button
                    type="button"
                    className="ob-next-btn"
                    onClick={() => {
                      if (!company.legal_name?.trim()) {
                        setSubmitError("Please enter the registered company name.");
                        return;
                      }
                      if (!company.industry) {
                        setSubmitError("Please select an industry.");
                        return;
                      }
                      if (!company.company_size) {
                        setSubmitError("Please select a company size range.");
                        return;
                      }
                      if (!company.country?.trim()) {
                        setSubmitError("Please specify the country.");
                        return;
                      }
                      if (!company.company_email?.trim()) {
                        setSubmitError("Please provide an official company email.");
                        return;
                      }
                      if (!company.company_phone?.trim()) {
                        setSubmitError("Please provide a company contact number.");
                        return;
                      }
                      setSubmitError("");
                      setManualStep(2);
                    }}
                  >
                    Next: Administrator details <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}

            {/* ── STEP 2: Manager / Administrator ──────────────────── */}
            {manualStep === 2 && (
              <div className="ob-section">
                <div className="ob-section-header">
                  <div className="ob-section-icon">
                    <UserCheck size={20} />
                  </div>
                  <div>
                    <h3>Company administrator</h3>
                    <p>
                      Your authenticated profile serves as the primary workspace administrator.
                    </p>
                  </div>
                </div>

                <div className="ob-form-grid">
                  <div className="ob-field">
                    <label>Administrator name</label>
                    <input
                      type="text"
                      value={currentUser?.display_name || currentUser?.email.split("@")[0] || ""}
                      readOnly
                      className="ob-input-readonly"
                    />
                    <small className="ob-field-note">
                      From your authenticated account
                    </small>
                  </div>

                  <div className="ob-field">
                    <label>Official work email</label>
                    <input
                      type="email"
                      value={currentUser?.email || ""}
                      readOnly
                      className="ob-input-readonly"
                    />
                    <small className="ob-field-note">
                      Used for authentication and billing notices
                    </small>
                  </div>

                  <div className="ob-field">
                    <label htmlFor="admin_title">Designation / Role in company</label>
                    <input
                      id="admin_title"
                      type="text"
                      placeholder="e.g. Chief Information Officer, IT Director"
                      value={adminTitle}
                      onChange={(e) => setAdminTitle(e.target.value)}
                    />
                  </div>

                  <div className="ob-field">
                    <label htmlFor="admin_phone">Direct contact number</label>
                    <input
                      id="admin_phone"
                      type="tel"
                      placeholder="+1 (555) 019-8765"
                      value={adminPhone}
                      onChange={(e) => setAdminPhone(e.target.value)}
                    />
                  </div>
                </div>

                <div className="ob-admin-badge-row">
                  <div className="ob-admin-badge">
                    <ShieldCheck size={16} />
                    <div>
                      <strong>Account role: {currentUser?.role || "OWNER"}</strong>
                      <span>Has full workspace administration, billing, and member management privileges.</span>
                    </div>
                  </div>
                </div>

                <div className="ob-step-actions">
                  <button
                    type="button"
                    className="ob-back-step-btn"
                    onClick={() => setManualStep(1)}
                  >
                    <ChevronLeft size={16} /> Back
                  </button>
                  <button
                    type="button"
                    className="ob-next-btn"
                    onClick={() => {
                      setSubmitError("");
                      setManualStep(3);
                    }}
                  >
                    Next: Departments <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}

            {/* ── STEP 3: Departments ──────────────────────────────── */}
            {manualStep === 3 && (
              <div className="ob-section">
                <div className="ob-section-header">
                  <div className="ob-section-icon">
                    <Users size={20} />
                  </div>
                  <div>
                    <h3>Company departments</h3>
                    <p>
                      Add the departments across your organization to allocate SaaS licenses, costs, and hardware assets.
                    </p>
                  </div>
                </div>

                <DepartmentEditor
                  departments={departments}
                  onChange={setDepartments}
                />

                <div className="ob-step-actions">
                  <button
                    type="button"
                    className="ob-back-step-btn"
                    onClick={() => setManualStep(2)}
                  >
                    <ChevronLeft size={16} /> Back
                  </button>
                  <button
                    type="button"
                    className="ob-next-btn"
                    onClick={() => {
                      setSubmitError("");
                      setManualStep(4);
                    }}
                  >
                    Next: Review & confirm <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}

            {/* ── STEP 4: Review and Confirm ───────────────────────── */}
            {manualStep === 4 && (
              <div className="ob-section">
                <div className="ob-section-header">
                  <div className="ob-section-icon">
                    <Sparkles size={20} />
                  </div>
                  <div>
                    <h3>Review and confirm</h3>
                    <p>Please review your information before completing workspace setup.</p>
                  </div>
                </div>

                <div className="ob-review-grid">
                  {/* Company Summary */}
                  <div className="ob-review-block">
                    <div className="ob-review-block-header">
                      <h4>Company profile</h4>
                      <button
                        type="button"
                        className="ob-edit-btn"
                        onClick={() => setManualStep(1)}
                      >
                        Edit
                      </button>
                    </div>
                    <div className="ob-review-fields">
                      <div>
                        <span>Legal name</span>
                        <strong>{company.legal_name || "—"}</strong>
                      </div>
                      <div>
                        <span>Display name</span>
                        <strong>{company.display_name || "—"}</strong>
                      </div>
                      <div>
                        <span>Industry</span>
                        <strong>{company.industry || "—"}</strong>
                      </div>
                      <div>
                        <span>Company size</span>
                        <strong>{company.company_size || "—"}</strong>
                      </div>
                      <div>
                        <span>Country</span>
                        <strong>{company.country || "—"}</strong>
                      </div>
                      <div>
                        <span>Official email</span>
                        <strong>{company.company_email || "—"}</strong>
                      </div>
                      <div>
                        <span>Phone</span>
                        <strong>{company.company_phone || "—"}</strong>
                      </div>
                      <div>
                        <span>Website</span>
                        <strong>{company.website || "—"}</strong>
                      </div>
                      {company.address && (
                        <div style={{ gridColumn: "1 / -1" }}>
                          <span>Address</span>
                          <strong>
                            {[company.address, company.city, company.state, company.postal_code]
                              .filter(Boolean)
                              .join(", ")}
                          </strong>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Administrator Summary */}
                  <div className="ob-review-block">
                    <div className="ob-review-block-header">
                      <h4>Primary administrator</h4>
                      <button
                        type="button"
                        className="ob-edit-btn"
                        onClick={() => setManualStep(2)}
                      >
                        Edit
                      </button>
                    </div>
                    <div className="ob-review-fields">
                      <div>
                        <span>Name</span>
                        <strong>{currentUser?.display_name || currentUser?.email.split("@")[0]}</strong>
                      </div>
                      <div>
                        <span>Work email</span>
                        <strong>{currentUser?.email}</strong>
                      </div>
                      <div>
                        <span>Designation</span>
                        <strong>{adminTitle || "Company Administrator"}</strong>
                      </div>
                      <div>
                        <span>Direct phone</span>
                        <strong>{adminPhone || "—"}</strong>
                      </div>
                    </div>
                  </div>

                  {/* Departments Summary */}
                  <div className="ob-review-block">
                    <div className="ob-review-block-header">
                      <h4>
                        Departments configured{" "}
                        <span className="ob-preview-count">{departments.length}</span>
                      </h4>
                      <button
                        type="button"
                        className="ob-edit-btn"
                        onClick={() => setManualStep(3)}
                      >
                        Edit
                      </button>
                    </div>
                    {departments.length === 0 ? (
                      <p className="ob-review-empty">
                        No departments added. You can create departments anytime from your dashboard.
                      </p>
                    ) : (
                      <div className="ob-preview-chips" style={{ padding: "8px 0" }}>
                        {departments.map((dept, i) => (
                          <span key={i} className="ob-preview-chip">
                            {dept.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {submitError && (
                  <div className="ob-alert ob-alert-error" style={{ marginBottom: 16 }}>
                    <AlertCircle size={15} />
                    <span>{submitError}</span>
                  </div>
                )}

                <div className="ob-step-actions">
                  <button
                    type="button"
                    className="ob-back-step-btn"
                    onClick={() => setManualStep(3)}
                  >
                    <ChevronLeft size={16} /> Back
                  </button>
                  <button
                    type="button"
                    className="ob-confirm-btn"
                    onClick={handleSubmit}
                    disabled={submitting}
                    style={{ marginTop: 0 }}
                  >
                    {submitting ? (
                      <>
                        <span className="ob-btn-spinner" /> Setting up your workspace…
                      </>
                    ) : (
                      <>
                        <Check size={18} /> Confirm and finish setup
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

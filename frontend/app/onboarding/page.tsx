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
  const [excelPreview, setExcelPreview] = useState<ExcelImportResult | null>(null);
  const [excelError, setExcelError] = useState("");

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
        if (preview.departments && preview.departments.length > 0) {
          setDepartments(preview.departments);
        }
      }
    } catch (err) {
      setExcelError(err instanceof Error ? err.message : "Failed to parse workbook.");
    } finally {
      setExcelParsing(false);
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError("");

    try {
      await submitOnboarding({ company, departments });
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
                Tell us a little about your organization so we can configure your subscription management workspace.
              </p>
            </div>

            <div className="ob-choose-cards">
              {/* Option A: Excel */}
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
                    <strong>Import company information</strong>
                    <span className="ob-tag-recommended">Fastest</span>
                  </div>
                  <span>
                    Upload your company Excel workbook to quickly configure your organization, departments, and teams.
                  </span>
                  <div className="ob-choose-tags">
                    <span>.xlsx workbook</span>
                    <span>Downloadable template</span>
                    <span>Auto-detects departments</span>
                    <span>Validation preview</span>
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
              <h2>Import company information</h2>
            </div>

            {/* Template download banner */}
            <div className="ob-template-banner">
              <div className="ob-template-icon">
                <FileSpreadsheet size={22} />
              </div>
              <div className="ob-template-copy">
                <strong>Download our standard onboarding template</strong>
                <span>
                  Includes <strong>Company</strong>, <strong>Departments</strong>, and <strong>Employees</strong> sheets with column definitions and sample data.
                </span>
              </div>
              <a
                href="/api/organizations/me/onboarding/excel-template"
                download="unisora_onboarding_template.xlsx"
                className="ob-template-btn"
              >
                <Download size={14} /> Download .xlsx
              </a>
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
                  {excelParsing ? <div className="ob-spinner" /> : <Upload size={30} />}
                </div>
                <strong>{excelParsing ? "Analyzing workbook…" : "Drop your Excel workbook here"}</strong>
                <span>or click to browse your computer</span>
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
                <div className="ob-preview-header">
                  <div className="ob-preview-file">
                    <FileSpreadsheet size={18} className="ob-file-icon" />
                    <strong>{excelFile?.name}</strong>
                    <span className="ob-badge-success">Ready to review</span>
                  </div>
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

                {/* Company & Department Summary */}
                {excelPreview.valid && excelPreview.company && (
                  <div className="ob-preview-summary">
                    <div className="ob-preview-card">
                      <div className="ob-preview-card-title">
                        <Building2 size={16} />
                        <h4>Company profile</h4>
                      </div>
                      <div className="ob-preview-grid">
                        <div>
                          <span>Legal name</span>
                          <strong>{excelPreview.company.legal_name || excelPreview.company.company_name || "—"}</strong>
                        </div>
                        <div>
                          <span>Trading name</span>
                          <strong>{excelPreview.company.company_name || "—"}</strong>
                        </div>
                        <div>
                          <span>Industry</span>
                          <strong>{excelPreview.company.industry || "—"}</strong>
                        </div>
                        <div>
                          <span>Company size</span>
                          <strong>{excelPreview.company.company_size || "—"}</strong>
                        </div>
                        <div>
                          <span>Country</span>
                          <strong>{excelPreview.company.country || "—"}</strong>
                        </div>
                        <div>
                          <span>Official email</span>
                          <strong>{excelPreview.company.company_email || "—"}</strong>
                        </div>
                      </div>
                    </div>

                    <div className="ob-preview-card">
                      <div className="ob-preview-card-title">
                        <Users size={16} />
                        <h4>
                          Departments{" "}
                          <span className="ob-preview-count">
                            {excelPreview.department_count}
                          </span>
                        </h4>
                      </div>
                      {excelPreview.departments.length === 0 ? (
                        <p className="ob-preview-empty">No departments found in sheet.</p>
                      ) : (
                        <div className="ob-preview-chips">
                          {excelPreview.departments.map((dept, i) => (
                            <span key={i} className="ob-preview-chip">
                              {dept.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {excelPreview.employee_count > 0 && (
                      <div className="ob-preview-card">
                        <div className="ob-preview-card-title">
                          <UserCheck size={16} />
                          <h4>
                            Employees in sheet{" "}
                            <span className="ob-preview-count">
                              {excelPreview.employee_count}
                            </span>
                          </h4>
                        </div>
                        <p className="ob-preview-note">
                          {excelPreview.employee_count} employee records detected. Departments will be created now, and employee accounts can be added from the Employees directory once setup is complete.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {excelPreview.valid && (
                  <button
                    type="button"
                    className="ob-confirm-btn"
                    onClick={handleSubmit}
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <span className="ob-btn-spinner" /> Configuring workspace…
                      </>
                    ) : (
                      <>
                        <Check size={17} /> Confirm and finish onboarding
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

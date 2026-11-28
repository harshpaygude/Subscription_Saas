"use client";

import React, { useState, useRef } from "react";
import {
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  X,
  Download,
  WalletCards,
  Calendar,
  Zap,
  FileText,
  Loader2,
  Clock,
  Sparkles,
} from "lucide-react";
import { importSubscriptionsCSV, seedDemoSubscriptions } from "@/lib/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ImportSubscriptionsModal({ isOpen, onClose, onSuccess }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{
    imported: number;
    updated: number;
    total_processed: number;
    errors: string[];
  } | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  function handleFileChange(selectedFile: File) {
    setError("");
    setResult(null);
    const fname = selectedFile.name.toLowerCase();
    if (!fname.endsWith(".csv") && !fname.endsWith(".xlsx") && !fname.endsWith(".xls")) {
      setError("Please choose a valid CSV (.csv) or Excel (.xlsx, .xls) file.");
      return;
    }
    setFile(selectedFile);
  }

  function downloadSampleCsv() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    const in30d = new Date(today);
    in30d.setDate(today.getDate() + 30);
    const in90d = new Date(today);
    in90d.setDate(today.getDate() + 90);

    const fmt = (d: Date) => d.toISOString().split("T")[0];

    const csvContent =
      "provider,name,plan,amount,currency,billing_interval,renewal_type,start_date,next_renewal_date,status,seats,note\n" +
      `github,GitHub Enterprise,Enterprise Cloud (50 seats),1050.00,USD,monthly,AUTOPAY,2024-01-15,${fmt(tomorrow)},ACTIVE,50,Corporate Amex 4092. Renews tomorrow (1-day prior alert test case).\n` +
      `figma,Figma Enterprise Suite,Organization & FigJam,18000.00,USD,annual,MANUAL,2024-02-01,${fmt(tomorrow)},ACTIVE,35,Manual Invoice Net-30. Purchase Order PO-2024-892 required (1-day prior alert test case).\n` +
      `slack,Slack Enterprise Grid,Enterprise Grid Tier 1,12500.00,USD,annual,AUTOPAY,2024-01-01,${fmt(in30d)},ACTIVE,60,Auto-renews via corporate billing profile in 30 days (1-month prior alert test case).\n` +
      `datadog,Datadog APM & Infra,Pro Infrastructure (50 hosts),24000.00,USD,annual,MANUAL,2024-01-01,${fmt(in30d)},ACTIVE,50,Vendor contract renewal quote required 30 days prior (1-month prior alert test case).\n` +
      `openai,OpenAI ChatGPT Team & API,Team Tier 4 Usage Tier,750.00,USD,monthly,AUTOPAY,2024-03-01,${fmt(in90d)},ACTIVE,25,Auto-reload active with backup corporate card.\n` +
      `google,Google Workspace Enterprise,Enterprise Plus with Gemini,7200.00,USD,annual,AUTOPAY,2024-01-15,${fmt(in90d)},ACTIVE,65,Primary domain Google Workspace directory.\n` +
      "microsoft,Microsoft 365 E5,Enterprise E5 Compliance Suite,21600.00,USD,annual,MANUAL,2024-02-15,2025-06-30,ACTIVE,40,Enterprise agreement with Microsoft reseller.\n";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "UniSora_SaaS_Subscriptions_Sample.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError("");
    setResult(null);
    try {
      const res = await importSubscriptionsCSV(file);
      setResult(res);
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to import SaaS subscriptions.");
    } finally {
      setUploading(false);
    }
  }

  async function handleSeedDemo() {
    setSeeding(true);
    setError("");
    setResult(null);
    try {
      const res = await seedDemoSubscriptions();
      setResult(res);
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load dummy SaaS dataset.");
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !uploading && !seeding) onClose();
      }}
    >
      <div className="modal-dialog modal-dialog-lg" role="dialog" aria-modal="true">
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-header-title-row">
            <WalletCards size={20} className="text-accent" />
            <div>
              <h3 className="font-semibold">Import SaaS Subscriptions & Renewals</h3>
              <p className="text-xs text-muted">
                Bulk upload recurring SaaS licenses, contract dates, and autopay vs. manual renewal types.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            disabled={uploading || seeding}
          >
            <X size={17} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body space-y-4">
          {/* Quick Info Banner */}
          <div className="import-info-box">
            <div className="import-info-title">
              <Zap size={14} className="text-warning" />
              <span>Smart SaaS Renewal Alerting (1-Month &amp; 1-Day Prior)</span>
            </div>
            <p className="text-secondary leading-relaxed" style={{ margin: 0 }}>
              UniSora scans renewal milestones automatically:
              <br />
              • <strong>1-Month (30 Days) Prior:</strong> Sends an advance notice alerting the user whether the contract will auto-debit or requires manual purchase order processing.
              <br />
              • <strong>1-Day Prior:</strong> Generates an urgent reminder alerting about tomorrow&apos;s auto-charge or critical manual invoice payment due to avoid license suspension.
            </p>
          </div>

          {/* Quick Action: Seed Demo Dataset */}
          <div className="import-demo-banner">
            <div style={{ flex: 1, minWidth: 220 }}>
              <h4 className="task-title" style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <Sparkles size={14} className="text-accent" />
                <span>Need dummy data to test right away?</span>
              </h4>
              <p className="text-xs text-secondary" style={{ margin: 0 }}>
                Pre-loads complete SaaS test cases (renews tomorrow, in 30 days, autopay &amp; manual) and mock connections.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleSeedDemo}
              disabled={seeding || uploading}
            >
              {seeding ? (
                <>
                  <Loader2 size={13} className="spin-animation" />
                  <span>Loading…</span>
                </>
              ) : (
                <>
                  <Sparkles size={13} />
                  <span>Load Demo Dataset</span>
                </>
              )}
            </button>
          </div>

          {/* Download Sample Templates Bar */}
          <div className="import-template-bar">
            <div className="flex items-center gap-2 text-xs text-secondary">
              <FileSpreadsheet size={16} className="text-success" />
              <span>Download sample spreadsheet with preconfigured test cases:</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={downloadSampleCsv}
              >
                <Download size={13} />
                <span>Sample CSV</span>
              </button>
              <a
                href="/UniSora_Complete_SaaS_Demo_Dataset.xlsx"
                download="UniSora_Complete_SaaS_Demo_Dataset.xlsx"
                className="btn btn-outline btn-sm"
              >
                <Download size={13} />
                <span>Full Excel (.xlsx)</span>
              </a>
            </div>
          </div>

          {/* Drag & Drop Upload Zone */}
          <div
            className={`import-dropzone-area ${isDragOver ? "is-dragover" : ""} ${file ? "has-file" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileChange(e.dataTransfer.files[0]);
              }
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileChange(e.target.files[0]);
                }
              }}
            />

            {file ? (
              <div className="flex flex-col items-center gap-2">
                <FileSpreadsheet size={36} className="text-success" />
                <span className="font-semibold text-sm text-primary">{file.name}</span>
                <span className="text-xs text-muted">
                  {(file.size / 1024).toFixed(1)} KB · Click or drag to replace
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Upload size={32} className="text-muted" />
                <span className="font-medium text-sm text-primary">
                  Choose a CSV or Excel file or drag &amp; drop here
                </span>
                <span className="text-xs text-muted">
                  Supported formats: .csv, .xlsx, .xls (up to 10MB)
                </span>
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="alert-notice alert-danger text-xs" role="alert">
              <AlertCircle size={14} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Import Result Feedback */}
          {result && (
            <div className="import-result-box space-y-2">
              <div className="flex items-center gap-2 font-medium text-success">
                <CheckCircle2 size={15} />
                <span>
                  Successfully processed {result.total_processed} SaaS subscription records!
                </span>
              </div>
              <p className="text-secondary" style={{ margin: 0 }}>
                Created: <strong>{result.imported}</strong> new · Updated:{" "}
                <strong>{result.updated}</strong> existing
              </p>
              {result.errors && result.errors.length > 0 && (
                <div className="text-danger mt-1">
                  <strong>Notes / Warnings:</strong>
                  <ul className="list-disc pl-4 mt-1">
                    {result.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={uploading || seeding}
          >
            Close
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!file || uploading || seeding}
          >
            {uploading ? (
              <>
                <Loader2 size={14} className="spin-animation" />
                <span>Importing…</span>
              </>
            ) : (
              <>
                <Upload size={14} />
                <span>Upload &amp; Import</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

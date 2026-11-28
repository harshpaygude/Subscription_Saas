"use client";

import React, { useState, useRef } from "react";
import {
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  X,
  Download,
  Users,
  Laptop,
  WalletCards,
  Loader2,
  FileText,
} from "lucide-react";
import { importEmployeesCSV, type BulkImportResult } from "@/lib/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ImportEmployeesModal({ isOpen, onClose, onSuccess }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BulkImportResult | null>(null);
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

  function downloadSampleTemplate() {
    const csvContent =
      "Employee ID,Full Name,Email,Department,Role,Joining Date,Phone Number,Asset Tag,Asset Name,Asset Type,Manufacturer,Model,Serial Number,Subscription Name,Plan,Subscription Cost\n" +
      "EMP101,Alex Rivera,alex.rivera@acme.com,Engineering,Full-Stack Lead,2026-01-15,+1 555-0101,AST-101,MacBook Pro 16 M3,Laptop,Apple,MacBook Pro,SN-APL-8821,GitHub,Pro,21.00\n" +
      "EMP102,Sophia Chen,sophia.chen@acme.com,Product,Principal PM,2026-02-01,+1 555-0102,AST-102,Dell XPS 15 9530,Laptop,Dell,XPS 15,SN-DLL-9943,OpenAI,Tier 4,45.00\n" +
      "EMP103,Marcus Vance,marcus.vance@acme.com,Design,Senior Product Designer,2026-02-15,+1 555-0103,AST-103,Apple Studio Display 27,Monitor,Apple,Studio Display,SN-APL-4412,Claude Pro,Team,30.00\n" +
      "EMP104,Elena Rostova,elena.rostova@acme.com,Security,SecOps Engineer,2026-03-01,+1 555-0104,AST-104,Lenovo ThinkPad X1 Carbon,Laptop,Lenovo,ThinkPad X1,SN-LNV-7731,AWS,Developer,50.00\n" +
      "EMP105,Priya Patel,priya.patel@acme.com,Operations,Finance Analyst,2026-03-10,+1 555-0105,AST-105,MacBook Air 15 M2,Laptop,Apple,MacBook Air,SN-APL-2299,Slack,Enterprise,15.00\n";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "UniSora_Employee_Lifecycle_MultiService_Template.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function handleUpload() {
    if (!file) {
      setError("Please select a file to import.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const res = await importEmployeesCSV(file);
      setResult(res);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import file.");
    } finally {
      setUploading(false);
    }
  }

  function handleReset() {
    setFile(null);
    setResult(null);
    setError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !uploading) onClose();
      }}
    >
      <div className="modal-dialog modal-dialog-lg" role="dialog" aria-modal="true" style={{ maxWidth: 620 }}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-title-row">
            <div
              className="modal-icon-badge"
              style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "var(--color-accent-subtle)",
                color: "var(--color-accent-ink)",
                border: "1px solid var(--color-accent-ring)",
              }}
            >
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 18 }}>Import Multi-Service Roster</h3>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
                Automatically provision Employees, assign IT Assets, and link Subscriptions in one upload.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            disabled={uploading}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body" style={{ padding: "20px 24px" }}>
          {error && (
            <div className="alert-notice alert-danger mb-4" role="alert">
              <AlertCircle size={16} className="flex-none" />
              <span>{error}</span>
              <button type="button" onClick={() => setError("")}>×</button>
            </div>
          )}

          {/* Result view */}
          {result ? (
            <div className="import-success-box" style={{ background: "var(--bg-subtle)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-lg)", padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--color-success)", marginBottom: 14 }}>
                <CheckCircle2 size={24} />
                <strong style={{ fontSize: 15 }}>Multi-Service Sync Completed!</strong>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
                <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)", textAlign: "center" }}>
                  <Users size={18} style={{ margin: "0 auto 4px", color: "var(--color-info)" }} />
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{result.created_employees}</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Employees Added</div>
                </div>

                <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)", textAlign: "center" }}>
                  <Laptop size={18} style={{ margin: "0 auto 4px", color: "var(--color-accent)" }} />
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{result.assigned_assets}</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>IT Assets Assigned</div>
                </div>

                <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)", textAlign: "center" }}>
                  <WalletCards size={18} style={{ margin: "0 auto 4px", color: "var(--color-warning)" }} />
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{result.assigned_subscriptions}</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Subscriptions Linked</div>
                </div>
              </div>

              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px", lineHeight: 1.4 }}>
                {result.message}
              </p>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={handleReset}>
                  Import Another File
                </button>
                <button type="button" className="btn btn-primary btn-sm" onClick={onClose}>
                  Done
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Dropzone */}
              <div
                className={`import-dropzone ${isDragOver ? "is-dragover" : ""} ${file ? "has-file" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragOver(false);
                  if (e.dataTransfer.files?.[0]) {
                    handleFileChange(e.dataTransfer.files[0]);
                  }
                }}
                onClick={() => {
                  if (!file) fileInputRef.current?.click();
                }}
                style={{
                  border: isDragOver ? "2px dashed var(--color-accent)" : "2px dashed var(--border-color)",
                  borderRadius: "var(--radius-lg)",
                  padding: "28px 20px",
                  textAlign: "center",
                  background: isDragOver ? "var(--color-accent-subtle)" : "var(--bg-subtle)",
                  cursor: file ? "default" : "pointer",
                  transition: "all var(--transition-fast)",
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv, .xlsx, .xls, text/csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleFileChange(e.target.files[0]);
                  }}
                />

                {file ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-surface)", padding: "12px 16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <FileText size={24} style={{ color: "var(--color-accent)" }} />
                      <div style={{ textAlign: "left" }}>
                        <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{file.name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          {(file.size / 1024).toFixed(1)} KB · Ready to process
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleReset();
                      }}
                      title="Remove file"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div>
                    <Upload size={32} style={{ margin: "0 auto 10px", color: "var(--text-muted)" }} />
                    <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)", marginBottom: 4 }}>
                      Drag and drop your CSV or Excel file here
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 12 }}>
                      Supports .csv and .xlsx spreadsheets with multiple services
                    </div>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        fileInputRef.current?.click();
                      }}
                    >
                      Browse Computer
                    </button>
                  </div>
                )}
              </div>

              {/* Supported Services Preview */}
              <div style={{ marginTop: 18, background: "var(--bg-subtle)", borderRadius: "var(--radius-md)", padding: "12px 16px", border: "1px solid var(--border-subtle)" }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-muted)", marginBottom: 8 }}>
                  Services Updated in this Import
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
                    <Users size={15} style={{ color: "var(--color-info)" }} />
                    <span><strong>1. Employee Info</strong></span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
                    <Laptop size={15} style={{ color: "var(--color-accent)" }} />
                    <span><strong>2. IT Asset Custody</strong></span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
                    <WalletCards size={15} style={{ color: "var(--color-warning)" }} />
                    <span><strong>3. SaaS Subscriptions</strong></span>
                  </div>
                </div>
              </div>

              {/* Sample Template Download */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 16 }}>
                <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  Need the standard format?
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={downloadSampleTemplate}
                  title="Download sample CSV template"
                >
                  <Download size={13} />
                  <span>Download Sample CSV Template</span>
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {!result && (
          <div className="modal-footer" style={{ padding: "14px 24px", display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button type="button" className="btn btn-secondary btn-sm" onClick={onClose} disabled={uploading}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleUpload}
              disabled={!file || uploading}
            >
              {uploading ? (
                <>
                  <Loader2 size={14} className="spin-animation" />
                  <span>Importing & Syncing Services…</span>
                </>
              ) : (
                <>
                  <Upload size={14} />
                  <span>Import & Update All Services</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

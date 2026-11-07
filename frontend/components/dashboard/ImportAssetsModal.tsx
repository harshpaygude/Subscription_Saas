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
  Headphones,
  Monitor,
  Smartphone,
  Layers,
  Loader2,
  FileText,
  HelpCircle,
} from "lucide-react";
import { importAssetsCSV, type AssetBulkImportResult } from "@/lib/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ImportAssetsModal({ isOpen, onClose, onSuccess }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AssetBulkImportResult | null>(null);
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
    const csvContent =
      "Asset Tag,Asset Name,Asset Type,Manufacturer,Model,Serial Number,Purchase Cost,Currency,Location,Status,Assigned Employee Email,Assigned Employee Name,Employee ID,Handover Notes\n" +
      "LT-101,MacBook Pro 16 M3 Max,Laptop,Apple,A2991,SN-APL-8821,3499.00,USD,San Francisco HQ,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,Primary workstation with 64GB RAM\n" +
      "HD-101,Jabra Evolve2 65 Wireless,Headset,Jabra,Evolve2-65,SN-JBR-9912,249.00,USD,San Francisco HQ,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,Wireless ANC headset with desk stand\n" +
      "MN-101,Dell UltraSharp 27 4K USB-C,Monitor,Dell,U2723QE,SN-DLL-4412,579.00,USD,Desk 4A,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,External 4K display with USB-C Hub\n" +
      "LT-102,Lenovo ThinkPad X1 Carbon Gen 11,Laptop,Lenovo,21HM000EUS,SN-LNV-7731,1899.00,USD,Austin Office,Assigned,sophia.chen@acme.com,Sophia Chen,EMP102,Ultrabook for engineering lead\n" +
      "HD-102,Sony WH-1000XM5 ANC,Headset,Sony,WH-1000XM5,SN-SNY-3319,399.00,USD,Austin Office,Assigned,sophia.chen@acme.com,Sophia Chen,EMP102,Over-ear ANC headset for focus\n" +
      "LT-103,MacBook Air 15 M3,Laptop,Apple,A3114,SN-APL-2299,1499.00,USD,Remote,Assigned,marcus.vance@acme.com,Marcus Vance,EMP103,Design laptop\n" +
      "MN-102,Apple Studio Display 27,Monitor,Apple,MK0U3LL/A,SN-APL-5520,1599.00,USD,Remote,Assigned,marcus.vance@acme.com,Marcus Vance,EMP103,5K Studio Display\n" +
      "PH-101,iPhone 15 Pro Enterprise,Mobile Phone,Apple,A3102,SN-APL-7744,999.00,USD,San Francisco HQ,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,Dedicated fleet testing phone\n" +
      "LT-104,Dell Latitude 5540,Laptop,Dell,5540-I7,SN-DLL-1092,1299.00,USD,IT Storage Room,Available,,,,Ready for next onboarding batch\n" +
      "HD-103,Jabra Evolve 40 Stereo,Headset,Jabra,Evolve-40,SN-JBR-1188,89.00,USD,IT Storage Room,Available,,,,Wired USB headset in backup storage\n" +
      "MN-103,LG 34 Curved UltraWide,Monitor,LG,34WN80C-B,SN-LG-9821,549.00,USD,IT Storage Room,Available,,,,Spare ultrawide display in inventory\n";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "UniSora_IT_Assets_MultiDevice_Template.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function downloadSampleExcel() {
    setDownloadingTemplate(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const res = await fetch("/api/assets/sample-template?format=excel", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        throw new Error("Could not download sample Excel from server.");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "UniSora_IT_Assets_MultiDevice_Template.xlsx";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Fallback to CSV if excel endpoint isn't reached
      downloadSampleCsv();
    } finally {
      setDownloadingTemplate(false);
    }
  }

  async function handleUpload() {
    if (!file) {
      setError("Please select a file to import.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const res = await importAssetsCSV(file);
      setResult(res);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import asset file.");
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
      <div className="modal-dialog modal-dialog-lg" role="dialog" aria-modal="true" style={{ maxWidth: 660 }}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-title-row">
            <div
              className="modal-icon-badge"
              style={{ backgroundColor: "var(--color-accent-subtle)", color: "var(--color-accent)" }}
            >
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 18 }}>Import IT Hardware Assets</h3>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
                Bulk import laptops, headsets, monitors, and peripherals with 1-to-many employee custody links.
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
            <div
              className="import-success-box"
              style={{
                background: "var(--bg-subtle)",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-lg)",
                padding: 20,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--color-success)", marginBottom: 14 }}>
                <CheckCircle2 size={24} />
                <strong style={{ fontSize: 15 }}>IT Hardware Inventory Synchronized!</strong>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
                <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)", textAlign: "center" }}>
                  <Laptop size={18} style={{ margin: "0 auto 4px", color: "var(--color-accent)" }} />
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{result.created_assets}</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Created</div>
                </div>

                <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)", textAlign: "center" }}>
                  <Layers size={18} style={{ margin: "0 auto 4px", color: "var(--color-info)" }} />
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{result.updated_assets}</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Updated</div>
                </div>

                <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)", textAlign: "center" }}>
                  <CheckCircle2 size={18} style={{ margin: "0 auto 4px", color: "var(--color-success)" }} />
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{result.assigned_assets}</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Assigned</div>
                </div>

                <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)", textAlign: "center" }}>
                  <Users size={18} style={{ margin: "0 auto 4px", color: "var(--color-warning)" }} />
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{result.employees_matched}</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Employees</div>
                </div>
              </div>

              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px", lineHeight: 1.5 }}>
                {result.message}
              </p>

              {result.warnings && result.warnings.length > 0 && (
                <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-md)", padding: "10px 14px", marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-warning)", marginBottom: 4 }}>
                    Import Notes:
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11, color: "var(--text-secondary)" }}>
                    {result.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

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
                  padding: "26px 20px",
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
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      background: "var(--bg-surface)",
                      padding: "12px 16px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-color)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <FileText size={24} style={{ color: "var(--color-accent)" }} />
                      <div style={{ textAlign: "left" }}>
                        <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{file.name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          {(file.size / 1024).toFixed(1)} KB · Ready to upload
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
                      Drag and drop your IT Assets CSV or Excel file
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 12 }}>
                      Supports .csv and .xlsx spreadsheets with multiple assets per employee
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

              {/* 1-to-Many Relationship Informational Card */}
              <div
                style={{
                  marginTop: 16,
                  background: "var(--bg-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "12px 16px",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                  <HelpCircle size={15} style={{ color: "var(--color-accent)" }} />
                  <strong style={{ fontSize: 12, color: "var(--text-primary)" }}>
                    1-to-Many Custody Supported
                  </strong>
                </div>
                <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "0 0 10px", lineHeight: 1.45 }}>
                  A single employee can be provided multiple devices simultaneously (e.g. 1 Laptop, 1 Headset, 1 External Monitor, and accessories). You can format this as:
                </p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-secondary)" }}>
                    <Laptop size={14} style={{ color: "var(--color-accent)" }} />
                    <span>Laptops</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-secondary)" }}>
                    <Headphones size={14} style={{ color: "var(--color-warning)" }} />
                    <span>Headsets</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-secondary)" }}>
                    <Monitor size={14} style={{ color: "var(--color-info)" }} />
                    <span>Monitors</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-secondary)" }}>
                    <Smartphone size={14} style={{ color: "var(--color-success)" }} />
                    <span>Phones & Peripherals</span>
                  </div>
                </div>
              </div>

              {/* Sample Template Downloads */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 16, flexWrap: "wrap", gap: 8 }}>
                <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  Need a pre-filled sample template?
                </span>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={downloadSampleCsv}
                    title="Download sample CSV template"
                  >
                    <Download size={13} />
                    <span>Sample CSV</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={downloadSampleExcel}
                    disabled={downloadingTemplate}
                    title="Download styled Excel workbook template"
                  >
                    <Download size={13} />
                    <span>{downloadingTemplate ? "Generating…" : "Sample Excel (.xlsx)"}</span>
                  </button>
                </div>
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
              type="submit"
              className="btn btn-primary btn-sm"
              onClick={handleUpload}
              disabled={!file || uploading}
            >
              {uploading ? (
                <>
                  <Loader2 size={14} className="spin-animation" />
                  <span>Importing & Assigning Assets…</span>
                </>
              ) : (
                <>
                  <Upload size={14} />
                  <span>Import IT Assets</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Key,
  Laptop,
  Shield,
  FileCheck,
  RefreshCw,
  Sparkles,
  AlertTriangle,
  Check,
} from "lucide-react";
import Link from "next/link";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  listActiveOffboardings,
  autoGenerateOffboardingChecklist,
  completeLifecycleTask,
  type LifecycleEmployeeRecord,
  type LifecycleTaskRecord,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function EmployeeOffboardingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const lifecycleId = Number(params?.id);

  const [employeeData, setEmployeeData] = useState<LifecycleEmployeeRecord | null>(null);
  const [tasks, setTasks] = useState<LifecycleTaskRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadData() {
    setLoading(true);
    try {
      const active = await listActiveOffboardings();
      const match = active.find((a) => a.id === lifecycleId);
      if (match) {
        setEmployeeData(match);
        setTasks(match.tasks || []);
      } else {
        setError("Offboarding clearance record not found.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load offboarding clearance.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (lifecycleId) void loadData();
  }, [lifecycleId]);

  async function handleAutoGenerate() {
    setGenerating(true);
    setError("");
    try {
      const generated = await autoGenerateOffboardingChecklist(lifecycleId);
      setTasks(generated);
      setNotice("Smart checklist generated based on user's active SaaS seats, assets, and security requirements.");
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to auto-generate checklist.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleCompleteTask(taskId: number, taskType: string) {
    let note = "Cleared by administrator";
    if (taskType === "MANUAL_CHECK") {
      const promptNote = prompt("Enter verification note for this clearance task:", "Verified and confirmed");
      if (promptNote === null) return;
      note = promptNote;
    }

    try {
      await completeLifecycleTask(taskId, note);
      setNotice("Task marked as completed.");
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not complete task.");
    }
  }

  const licenseTasks = tasks.filter((t) => t.task_type === "REVOKE_SUBSCRIPTION");
  const assetTasks = tasks.filter((t) => t.task_type === "RECOVER_ASSET");
  const securityTasks = tasks.filter(
    (t) => t.task_type === "MANUAL_CHECK" && (t.title.includes("Account") || t.title.includes("Slack") || t.title.includes("VPN"))
  );
  const adminTasks = tasks.filter(
    (t) => t.task_type === "MANUAL_CHECK" && !securityTasks.some((s) => s.id === t.id)
  );

  const completedCount = tasks.filter((t) => t.status === "COMPLETED").length;
  const progressPercent = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0;
  const employeeDisplayName = employeeData ? (employeeData.display_name || employeeData.email) : "Employee";

  return (
    <DashboardFrame
      title={employeeData ? `${employeeDisplayName} — Offboarding Clearance` : "Employee Offboarding"}
      description="Automated clearance workflow for departing employee accounts, software licenses, and hardware assets."
      actions={
        <div style={{ display: "flex", gap: "8px" }}>
          <Link href="/dashboard/offboarding" className="btn btn-secondary btn-sm">
            <ArrowLeft size={14} />
            <span>Back to Hub</span>
          </Link>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleAutoGenerate}
            disabled={generating}
          >
            <Sparkles size={14} />
            <span>{generating ? "Scanning…" : "Auto-Generate Checklist"}</span>
          </button>
        </div>
      }
    >
      {notice && (
        <div className="alert-notice alert-success mb-4" role="status" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")} style={{ background: "none", border: "none", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {error && (
        <div className="alert-notice alert-danger mb-4" role="alert" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{error}</span>
          <button type="button" onClick={() => setError("")} style={{ background: "none", border: "none", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {/* Header Profile Card */}
      {employeeData && (
        <div
          style={{
            background: "var(--card-bg, #ffffff)",
            border: "1px solid var(--border-color, #e2e8f0)",
            borderRadius: "12px",
            padding: "24px",
            marginBottom: "24px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <h2 style={{ fontSize: "20px", fontWeight: 700, margin: 0, color: "var(--foreground, #0f172a)" }}>
                  {employeeDisplayName}
                </h2>
                <StatusBadge variant="warning" size="sm">
                  {employeeData.status}
                </StatusBadge>
              </div>
              <p style={{ margin: "4px 0 0 0", color: "#64748b", fontSize: "14px" }}>
                {employeeData.email} • Department: <strong>{employeeData.department_names?.[0] || "General"}</strong> • Last Working Date: <strong>{employeeData.last_working_date || "Immediate"}</strong>
              </p>
            </div>

            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "13px", color: "#64748b" }}>Overall Clearance</div>
              <div style={{ fontSize: "22px", fontWeight: 700, color: progressPercent === 100 ? "#16a34a" : "#f59e0b" }}>
                {completedCount} / {tasks.length} Completed ({progressPercent}%)
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div style={{ width: "100%", height: "8px", backgroundColor: "#e2e8f0", borderRadius: "4px", overflow: "hidden", marginTop: "16px" }}>
            <div
              style={{
                width: `${progressPercent}%`,
                height: "100%",
                backgroundColor: progressPercent === 100 ? "#16a34a" : "#f59e0b",
                transition: "width 0.4s ease",
              }}
            />
          </div>
        </div>
      )}

      {loading ? (
        <div className="hub-data-empty">
          <div className="hub-spinner" />
          <span>Loading clearance checklist…</span>
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState
          icon={<Sparkles size={36} color="#f59e0b" />}
          title="No clearance tasks provisioned yet."
          description="Click 'Auto-Generate Checklist' above to automatically scan this employee's active software licenses and company devices."
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* SaaS License Revocations */}
          {licenseTasks.length > 0 && (
            <div className="dashboard-content-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                <Key size={18} color="#2563eb" />
                <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>SaaS Software & License Revocations</h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {licenseTasks.map((t) => (
                  <TaskRow key={t.id} task={t} onComplete={() => handleCompleteTask(t.id, t.task_type)} />
                ))}
              </div>
            </div>
          )}

          {/* Asset Returns */}
          {assetTasks.length > 0 && (
            <div className="dashboard-content-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                <Laptop size={18} color="#d97706" />
                <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>Company Hardware & Device Recovery</h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {assetTasks.map((t) => (
                  <TaskRow key={t.id} task={t} onComplete={() => handleCompleteTask(t.id, t.task_type)} />
                ))}
              </div>
            </div>
          )}

          {/* IT & Security Clearances */}
          {securityTasks.length > 0 && (
            <div className="dashboard-content-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                <Shield size={18} color="#dc2626" />
                <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>IT & Security Clearances</h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {securityTasks.map((t) => (
                  <TaskRow key={t.id} task={t} onComplete={() => handleCompleteTask(t.id, t.task_type)} />
                ))}
              </div>
            </div>
          )}

          {/* Administrative Clearances */}
          {adminTasks.length > 0 && (
            <div className="dashboard-content-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                <FileCheck size={18} color="#16a34a" />
                <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>Operational & Administrative Clearance</h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {adminTasks.map((t) => (
                  <TaskRow key={t.id} task={t} onComplete={() => handleCompleteTask(t.id, t.task_type)} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </DashboardFrame>
  );
}

function TaskRow({ task, onComplete }: { task: LifecycleTaskRecord; onComplete: () => void }) {
  const isDone = task.status === "COMPLETED";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "12px 16px",
        borderRadius: "8px",
        border: `1px solid ${isDone ? "#bbf7d0" : "var(--border-color, #e2e8f0)"}`,
        backgroundColor: isDone ? "#f0fdf4" : "var(--card-bg, #ffffff)",
        gap: "12px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {isDone ? (
          <CheckCircle2 size={18} color="#16a34a" />
        ) : (
          <div
            style={{
              width: "18px",
              height: "18px",
              borderRadius: "50%",
              border: "2px solid #cbd5e1",
            }}
          />
        )}
        <div>
          <div style={{ fontWeight: 600, color: isDone ? "#166534" : "var(--foreground, #0f172a)", fontSize: "14px" }}>
            {task.title}
          </div>
          {task.completion_note && (
            <div style={{ fontSize: "12px", color: "#15803d", marginTop: "2px" }}>
              Note: {task.completion_note}
            </div>
          )}
        </div>
      </div>

      <div>
        {isDone ? (
          <span style={{ fontSize: "12px", fontWeight: 600, color: "#16a34a" }}>Completed ✓</span>
        ) : (
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={onComplete}
            style={{ fontSize: "12px", padding: "4px 12px" }}
          >
            Mark Done
          </button>
        )}
      </div>
    </div>
  );
}

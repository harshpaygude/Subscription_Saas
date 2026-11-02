"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Laptop,
  Mail,
  Phone,
  UserRoundCheck,
  WalletCards,
  Calendar,
  Building,
  ShieldAlert,
  ClipboardCheck,
  Clock,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  completeLifecycleTask,
  getEmployeeLifecycle,
  startEmployeeOffboarding,
  type LifecycleEmployeeRecord,
  type LifecycleResourceRecord,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function EmployeeLifecycleDetailPage() {
  const params = useParams<{ userId: string }>();
  const [employee, setEmployee] = useState<LifecycleEmployeeRecord | null>(null);
  const [lastWorkingDate, setLastWorkingDate] = useState("");
  const [offboarding, setOffboarding] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    try {
      setEmployee(await getEmployeeLifecycle(Number(params.userId)));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load employee lifecycle.");
    }
  }

  useEffect(() => {
    if (params.userId) void load();
  }, [params.userId]);

  async function offboard(event: FormEvent) {
    event.preventDefault();
    if (!lastWorkingDate) return;
    setOffboarding(true);
    try {
      await startEmployeeOffboarding(Number(params.userId), lastWorkingDate);
      setNotice("Offboarding workflow started. Clearance tasks have been generated.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start offboarding.");
    } finally {
      setOffboarding(false);
    }
  }

  async function complete(taskId: number, taskType: string) {
    const note =
      taskType === "MANUAL_ACCESS"
        ? window.prompt("Enter the verification note for this resource task:") || undefined
        : undefined;
    try {
      await completeLifecycleTask(taskId, note);
      setNotice("Clearance task marked completed.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The linked resource action is not complete.");
    }
  }

  const initial = (employee?.display_name || employee?.email || "E")
    .slice(0, 1)
    .toUpperCase();

  return (
    <DashboardFrame
      title={employee?.display_name || employee?.email || "Employee Details"}
      description="Employee company profile, assigned SaaS licenses, hardware custody, and lifecycle audit history."
    >
      <div className="mb-4">
        <Link href="/dashboard/employees" className="btn btn-secondary btn-sm inline-flex">
          <ArrowLeft size={14} />
          <span>Back to Employee Directory</span>
        </Link>
      </div>

      {notice && (
        <div className="alert-notice alert-success" role="status">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")}>×</button>
        </div>
      )}

      {error && (
        <div className="alert-notice alert-danger" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>×</button>
        </div>
      )}

      {!employee ? (
        <div className="hub-data-empty">
          <div className="hub-spinner" />
          <span>Loading employee record…</span>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Header Profile Card */}
          <section className="dashboard-content-card">
            <div className="employee-detail-header">
              <div className="detail-avatar">{initial}</div>
              <div className="detail-info-col">
                <div className="detail-title-row">
                  <h2 className="detail-name">{employee.display_name || employee.email}</h2>
                  <StatusBadge
                    variant={
                      employee.status === "COMPLETED"
                        ? "neutral"
                        : employee.status === "OFFBOARDING"
                        ? "warning"
                        : "success"
                    }
                    size="md"
                  >
                    {employee.status}
                  </StatusBadge>
                </div>
                <div className="detail-contacts-row">
                  <span className="contact-item">
                    <Mail size={14} className="text-muted" />
                    <span>{employee.email}</span>
                  </span>
                  {employee.phone_number && (
                    <span className="contact-item">
                      <Phone size={14} className="text-muted" />
                      <span>{employee.phone_number}</span>
                    </span>
                  )}
                  <span className="contact-item">
                    <Building size={14} className="text-muted" />
                    <span>
                      {employee.department_names.length
                        ? employee.department_names.join(", ")
                        : "No Department"}
                    </span>
                  </span>
                </div>
              </div>
            </div>

            {/* Profile Meta Grid */}
            <div className="detail-attributes-grid">
              <div className="attr-item">
                <span className="attr-label">Employee ID</span>
                <span className="attr-value">{employee.employee_id || "—"}</span>
              </div>
              <div className="attr-item">
                <span className="attr-label">Organization Role</span>
                <span className="attr-value">{employee.role}</span>
              </div>
              <div className="attr-item">
                <span className="attr-label">Joined On</span>
                <span className="attr-value">{employee.joined_at}</span>
              </div>
              <div className="attr-item">
                <span className="attr-label">Last Working Day</span>
                <span className="attr-value">{employee.last_working_date || "Active Staff"}</span>
              </div>
              <div className="attr-item">
                <span className="attr-label">Open Clearance Tasks</span>
                <span className="attr-value">{employee.open_task_count}</span>
              </div>
            </div>
          </section>

          {/* Assigned Resources: Subscriptions & IT Assets */}
          <div className="grid-2col">
            {/* Subscriptions Card */}
            <section className="dashboard-content-card">
              <div className="card-header-bar">
                <div className="flex-items-center gap-2">
                  <WalletCards size={18} className="text-accent" />
                  <h3 className="card-heading">Assigned Subscriptions</h3>
                </div>
                <span className="text-xs text-muted">
                  {employee.subscription_assignments.length} Allocated
                </span>
              </div>

              {employee.subscription_assignments.length === 0 ? (
                <div className="empty-subpanel">
                  <p>No active or historical software subscriptions allocated.</p>
                </div>
              ) : (
                <div className="resource-list">
                  {employee.subscription_assignments.map((sub) => (
                    <div key={sub.id} className="resource-item-row">
                      <div className="resource-item-main">
                        <strong className="resource-item-title">
                          {sub.resource_provider ? `${sub.resource_provider} · ` : ""}
                          {sub.resource_name || `Subscription #${sub.resource_id}`}
                        </strong>
                        <span className="resource-item-sub">
                          Allocated {new Date(sub.assigned_at).toLocaleDateString()}
                          {sub.released_at && ` · Released ${new Date(sub.released_at).toLocaleDateString()}`}
                        </span>
                      </div>
                      <StatusBadge
                        variant={sub.status === "ACTIVE" ? "success" : "neutral"}
                        size="sm"
                      >
                        {sub.status}
                      </StatusBadge>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* IT Assets Card */}
            <section className="dashboard-content-card">
              <div className="card-header-bar">
                <div className="flex-items-center gap-2">
                  <Laptop size={18} className="text-accent" />
                  <h3 className="card-heading">Provided IT Assets</h3>
                </div>
                <span className="text-xs text-muted">
                  {employee.asset_assignments.length} Devices
                </span>
              </div>

              {employee.asset_assignments.length === 0 ? (
                <div className="empty-subpanel">
                  <p>No hardware devices currently in employee custody.</p>
                </div>
              ) : (
                <div className="resource-list">
                  {employee.asset_assignments.map((asset) => (
                    <div key={asset.id} className="resource-item-row">
                      <div className="resource-item-main">
                        <strong className="resource-item-title">
                          {asset.resource_name || `Asset #${asset.resource_id}`}
                        </strong>
                        <span className="resource-item-sub">
                          Handed over {new Date(asset.assigned_at).toLocaleDateString()}
                          {asset.released_at && ` · Returned ${new Date(asset.released_at).toLocaleDateString()}`}
                        </span>
                      </div>
                      <StatusBadge
                        variant={asset.status === "ACTIVE" ? "success" : "neutral"}
                        size="sm"
                      >
                        {asset.status}
                      </StatusBadge>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* Offboarding Trigger Card */}
          {employee.status !== "COMPLETED" && employee.status !== "OFFBOARDING" && (
            <section className="dashboard-content-card card-warning-outline">
              <div className="card-header-bar">
                <div>
                  <h3 className="card-heading">Initiate Offboarding Protocol</h3>
                  <p className="card-subheading">
                    Setting a last working date will automatically schedule IT asset return and software license release checklists.
                  </p>
                </div>
              </div>

              <form className="inline-add-bar mt-2" onSubmit={offboard}>
                <div className="flex-1">
                  <label htmlFor="last-date" className="sr-only">Last Working Date</label>
                  <input
                    id="last-date"
                    type="date"
                    className="form-input"
                    value={lastWorkingDate}
                    onChange={(e) => setLastWorkingDate(e.target.value)}
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-danger btn-sm"
                  disabled={offboarding || !lastWorkingDate}
                >
                  <ShieldAlert size={14} />
                  <span>{offboarding ? "Processing…" : "Start Offboarding"}</span>
                </button>
              </form>
            </section>
          )}

          {/* Lifecycle & Clearance Tasks Card */}
          <section className="dashboard-content-card">
            <div className="card-header-bar">
              <div>
                <h3 className="card-heading">Clearance & Provisioning Audit Trail</h3>
                <p className="card-subheading">
                  All compliance tasks and handover confirmations associated with this team member.
                </p>
              </div>
            </div>

            {employee.tasks.length === 0 ? (
              <div className="empty-subpanel">
                <CheckCircle2 size={24} className="text-muted" />
                <p>No lifecycle tasks logged for this profile yet.</p>
              </div>
            ) : (
              <div className="tasks-list-grid">
                {employee.tasks.map((task) => {
                  const isCompleted = task.status === "COMPLETED";
                  return (
                    <div key={task.id} className="task-item-card">
                      <div className="task-icon-col">
                        {isCompleted ? (
                          <CheckCircle2 size={20} className="text-success" />
                        ) : (
                          <Clock size={20} className="text-warning" />
                        )}
                      </div>
                      <div className="task-content-col">
                        <h4 className="task-title">{task.title}</h4>
                        <p className="task-meta">
                          {task.task_type.replaceAll("_", " ")} · {task.action_status}
                        </p>
                      </div>
                      <div className="task-action-col">
                        {task.status === "OPEN" ? (
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            onClick={() => void complete(task.id, task.task_type)}
                          >
                            <CheckCircle2 size={13} />
                            <span>Mark Completed</span>
                          </button>
                        ) : (
                          <StatusBadge variant="success" size="sm">
                            Completed
                          </StatusBadge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardFrame>
  );
}

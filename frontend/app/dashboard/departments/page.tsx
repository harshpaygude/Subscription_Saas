"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  Users,
  Plus,
  Power,
  UserPlus,
  ArrowRight,
  X,
  Search,
  CheckCircle2,
  Building2,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  addDepartmentMember,
  createDepartment,
  listDepartmentMembers,
  listDepartments,
  listEmployees,
  updateDepartment,
  type DepartmentRecord,
  type EmployeeRecord,
  type MembershipRecord,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function DepartmentsPage() {
  const [items, setItems] = useState<DepartmentRecord[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [members, setMembers] = useState<MembershipRecord[]>([]);
  const [memberId, setMemberId] = useState("");
  const [addingMember, setAddingMember] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [search, setSearch] = useState("");

  async function load() {
    try {
      const [departmentList, employeeList] = await Promise.all([
        listDepartments(),
        listEmployees(),
      ]);
      setItems(departmentList);
      setEmployees(employeeList);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load departments.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function showMembers(id: number) {
    setSelected(id);
    try {
      setMembers(await listDepartmentMembers(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load department members.");
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await createDepartment({ name: name.trim(), description: description.trim() || undefined });
      setName("");
      setDescription("");
      setError("");
      setShowCreateModal(false);
      setNotice(`Department "${name.trim()}" created successfully.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create department.");
    } finally {
      setSaving(false);
    }
  }

  async function addMember(event: FormEvent) {
    event.preventDefault();
    if (selected === null || !memberId) return;
    setAddingMember(true);
    try {
      await addDepartmentMember(selected, Number(memberId));
      setMemberId("");
      setError("");
      setNotice("Employee assigned to department.");
      await showMembers(selected);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add employee to department.");
    } finally {
      setAddingMember(false);
    }
  }

  async function toggleStatus(dept: DepartmentRecord) {
    const nextStatus = !dept.is_active;
    const actionName = nextStatus ? "activate" : "deactivate";
    if (!window.confirm(`Are you sure you want to ${actionName} "${dept.name}"?`)) return;
    try {
      await updateDepartment(dept.id, { is_active: nextStatus });
      setNotice(`Department "${dept.name}" ${nextStatus ? "activated" : "deactivated"}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : `Could not ${actionName} department.`);
    }
  }

  const selectedDepartment = items.find((d) => d.id === selected);
  const filteredDepartments = items.filter((dept) =>
    !search.trim() ||
    dept.name.toLowerCase().includes(search.toLowerCase()) ||
    (dept.description && dept.description.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <DashboardFrame
      title="Departments"
      description="Configure organization teams, track functional divisions, and preserve employee transfer history."
      actions={
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus size={15} />
          <span>Add Department</span>
        </button>
      }
    >
      {/* Toast Notice */}
      {notice && (
        <div className="alert-notice alert-success" role="status">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")}>×</button>
        </div>
      )}

      {/* Error Notice */}
      {error && (
        <div className="alert-notice alert-danger" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>×</button>
        </div>
      )}

      {/* Department Directory Table Section */}
      <section className="dashboard-content-card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Organization Departments</h2>
            <p className="card-subheading">
              {items.length} departments registered in your workspace.
            </p>
          </div>

          <div className="card-header-actions">
            <div className="filter-search-box table-search-box">
              <Search size={15} className="search-icon" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search departments…"
                aria-label="Search departments"
              />
            </div>
          </div>
        </div>

        {items.length === 0 ? (
          <EmptyState
            icon={<Building2 size={28} />}
            title="No departments created yet"
            description="Create your first organization-scoped department to assign employees and manage licenses."
            action={
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setShowCreateModal(true)}
              >
                <Plus size={15} />
                <span>Create Department</span>
              </button>
            }
          />
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Department Name</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th className="align-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredDepartments.map((dept) => {
                  const isCurrent = selected === dept.id;
                  return (
                    <tr
                      key={dept.id}
                      className={isCurrent ? "row-highlight" : ""}
                    >
                      <td>
                        <button
                          type="button"
                          className="table-link-btn"
                          onClick={() => void showMembers(dept.id)}
                          title="View team members"
                        >
                          <Building2 size={16} className="table-row-icon" />
                          <span className="font-semibold">{dept.name}</span>
                        </button>
                      </td>
                      <td>
                        <span className="text-secondary">{dept.description || "—"}</span>
                      </td>
                      <td>
                        <StatusBadge
                          variant={dept.is_active ? "success" : "neutral"}
                          size="sm"
                        >
                          {dept.is_active ? "Active" : "Inactive"}
                        </StatusBadge>
                      </td>
                      <td className="align-right">
                        <div className="table-actions-inline">
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => void showMembers(dept.id)}
                          >
                            <Users size={13} />
                            <span>Members</span>
                          </button>
                          <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            onClick={() => void toggleStatus(dept)}
                            title={dept.is_active ? "Deactivate" : "Activate"}
                          >
                            <Power size={13} />
                            <span>{dept.is_active ? "Deactivate" : "Activate"}</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Selected Department Members Drawer / Section */}
      {selected !== null && (
        <section className="dashboard-content-card mt-6">
          <div className="card-header-bar">
            <div>
              <div className="flex-items-center gap-2">
                <h2 className="card-heading">{selectedDepartment?.name} — Team Members</h2>
                <StatusBadge
                  variant={selectedDepartment?.is_active ? "success" : "neutral"}
                  size="sm"
                >
                  {selectedDepartment?.is_active ? "Active Unit" : "Inactive"}
                </StatusBadge>
              </div>
              <p className="card-subheading">
                Assign existing employees or review active membership tenure.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setSelected(null)}
            >
              Close
            </button>
          </div>

          {/* Quick Add Member Form */}
          <form className="inline-add-bar" onSubmit={addMember}>
            <div className="flex-1">
              <select
                className="form-select"
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
                required
              >
                <option value="">Select employee to assign…</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.display_name || emp.email}
                    {emp.employee_id ? ` (${emp.employee_id})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={addingMember || !memberId}
            >
              <UserPlus size={14} />
              <span>{addingMember ? "Assigning…" : "Assign to Department"}</span>
            </button>
          </form>

          {/* Members List */}
          {members.length === 0 ? (
            <div className="empty-subpanel">
              <Users size={22} className="text-muted" />
              <p>No active or historical employees assigned to this department yet.</p>
            </div>
          ) : (
            <div className="members-grid mt-4">
              {members.map((member) => (
                <Link
                  href={`/dashboard/employees/${member.user_id}`}
                  key={member.id}
                  className="member-card"
                >
                  <div className="member-avatar">
                    {(member.display_name || member.email || "U").slice(0, 1).toUpperCase()}
                  </div>
                  <div className="member-info">
                    <h4 className="member-name">
                      {member.display_name || member.email || `User #${member.user_id}`}
                    </h4>
                    <span className="member-email">{member.email || "No email"}</span>
                    <div className="member-meta-row">
                      <StatusBadge
                        variant={member.is_active ? "success" : "neutral"}
                        size="sm"
                      >
                        {member.is_active ? "Active" : "Historical"}
                      </StatusBadge>
                      <span className="member-date">Since {member.effective_from}</span>
                    </div>
                  </div>
                  <ArrowRight size={14} className="member-card-arrow" />
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Add Department Modal Dialog */}
      {showCreateModal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !saving) setShowCreateModal(false);
          }}
        >
          <div className="modal-dialog" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-header-title-row">
                <Building2 size={20} className="text-accent" />
                <h3>Create New Department</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowCreateModal(false)}
                disabled={saving}
              >
                <X size={17} />
              </button>
            </div>

            <form onSubmit={submit}>
              <div className="modal-body space-y-4">
                <div className="form-group">
                  <label htmlFor="dept-name" className="form-label">
                    Department Name <span className="text-danger">*</span>
                  </label>
                  <input
                    id="dept-name"
                    type="text"
                    className="form-input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    placeholder="e.g. Engineering, Sales, Human Resources"
                    autoFocus
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="dept-desc" className="form-label">
                    Description
                  </label>
                  <textarea
                    id="dept-desc"
                    className="form-textarea"
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Brief description of the department's role and function…"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving || !name.trim()}
                >
                  <Plus size={15} />
                  <span>{saving ? "Creating…" : "Create Department"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardFrame>
  );
}

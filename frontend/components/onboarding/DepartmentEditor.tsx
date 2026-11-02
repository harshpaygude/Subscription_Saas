"use client";

import { useState } from "react";
import { Plus, Trash2, Edit2, Check, X } from "lucide-react";
import { DepartmentInput } from "@/lib/api";

interface Props {
  departments: DepartmentInput[];
  onChange: (departments: DepartmentInput[]) => void;
}

const COMMON_DEPTS = [
  "Human Resources",
  "Finance",
  "IT & Engineering",
  "Operations",
  "Marketing",
  "Sales",
  "Administration",
  "Legal & Compliance",
];

export function DepartmentEditor({ departments, onChange }: Props) {
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [editIndex, setEditIndex] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [error, setError] = useState("");

  function addDepartment() {
    const name = newName.trim();
    if (!name) return;
    if (departments.some((d) => d.name.toLowerCase() === name.toLowerCase())) {
      setError(`"${name}" is already added.`);
      return;
    }
    setError("");
    onChange([...departments, { name, description: newDesc.trim() || undefined }]);
    setNewName("");
    setNewDesc("");
  }

  function addCommon(name: string) {
    if (departments.some((d) => d.name.toLowerCase() === name.toLowerCase())) return;
    onChange([...departments, { name }]);
  }

  function removeDept(i: number) {
    onChange(departments.filter((_, idx) => idx !== i));
  }

  function startEdit(i: number) {
    setEditIndex(i);
    setEditName(departments[i].name);
    setEditDesc(departments[i].description || "");
  }

  function saveEdit() {
    if (editIndex === null) return;
    const name = editName.trim();
    if (!name) return;
    const updated = departments.map((d, i) =>
      i === editIndex ? { name, description: editDesc.trim() || undefined } : d
    );
    onChange(updated);
    setEditIndex(null);
  }

  return (
    <div className="ob-dept-editor">
      <div className="ob-dept-add">
        <div className="ob-dept-add-fields">
          <input
            type="text"
            placeholder="Department name (e.g. Finance) *"
            value={newName}
            onChange={(e) => {
              setNewName(e.target.value);
              setError("");
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addDepartment();
              }
            }}
            className="ob-dept-input ob-dept-input-name"
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addDepartment();
              }
            }}
            className="ob-dept-input ob-dept-input-desc"
          />
          <button type="button" className="ob-dept-add-btn" onClick={addDepartment}>
            <Plus size={15} /> Add
          </button>
        </div>
        {error && <p className="ob-dept-error">{error}</p>}
      </div>

      <div className="ob-dept-suggestions">
        <p className="ob-dept-suggestions-label">Quick-add common departments:</p>
        <div className="ob-dept-chips">
          {COMMON_DEPTS.map((name) => {
            const added = departments.some((d) => d.name.toLowerCase() === name.toLowerCase());
            return (
              <button
                key={name}
                type="button"
                className={`ob-dept-chip ${added ? "ob-dept-chip-added" : ""}`}
                onClick={() => !added && addCommon(name)}
                disabled={added}
              >
                {added ? "✓ " : "+ "} {name}
              </button>
            );
          })}
        </div>
      </div>

      {departments.length > 0 && (
        <div className="ob-dept-list">
          {departments.map((dept, i) => (
            <div key={i} className="ob-dept-item">
              {editIndex === i ? (
                <div className="ob-dept-edit-row">
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="ob-dept-input ob-dept-input-name"
                    autoFocus
                  />
                  <input
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    placeholder="Description"
                    className="ob-dept-input ob-dept-input-desc"
                  />
                  <button type="button" className="ob-dept-icon-btn ob-dept-save" onClick={saveEdit} title="Save">
                    <Check size={14} />
                  </button>
                  <button type="button" className="ob-dept-icon-btn" onClick={() => setEditIndex(null)} title="Cancel">
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <>
                  <div className="ob-dept-info">
                    <strong>{dept.name}</strong>
                    {dept.description && <span>{dept.description}</span>}
                  </div>
                  <div className="ob-dept-actions">
                    <button type="button" className="ob-dept-icon-btn" onClick={() => startEdit(i)} aria-label="Edit">
                      <Edit2 size={13} />
                    </button>
                    <button
                      type="button"
                      className="ob-dept-icon-btn ob-dept-remove"
                      onClick={() => removeDept(i)}
                      aria-label="Remove"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

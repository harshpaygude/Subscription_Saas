"use client";

import { FormEvent, useEffect, useState } from "react";
import { CircleDollarSign, Plus, X, Search, TrendingUp, Receipt } from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { createManualSpend, getMonthlySpend, type MonthlySpendResponse } from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function UsagePage() {
  const [data, setData] = useState<MonthlySpendResponse | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");

  async function load() {
    try {
      setData(await getMonthlySpend());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load spending data.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      await createManualSpend({
        provider: String(form.get("provider")),
        amount: String(form.get("amount")),
        currency: String(form.get("currency")),
        billing_interval: String(form.get("billing_interval")),
        period_start: String(form.get("period_start")),
        note: String(form.get("note") || ""),
      });
      setShowForm(false);
      setNotice("Manual cost entry recorded.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save manual spend.");
    } finally {
      setSaving(false);
    }
  }

  const currencies = data ? Object.entries(data.totals_by_currency) : [];
  const total =
    currencies.length === 1
      ? `${currencies[0][0]} ${Number(currencies[0][1]).toLocaleString()}`
      : currencies.length > 1
      ? "Multiple Currencies"
      : "—";

  const highestService = data?.services
    .slice()
    .sort((a, b) => Number(b.monthly_spend) - Number(a.monthly_spend))[0];

  const filteredServices = (data?.services || []).filter(
    (s) =>
      !search.trim() ||
      s.service.toLowerCase().includes(search.toLowerCase()) ||
      s.billing_source.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <DashboardFrame
      title="Usage & Costs"
      description="Normalized monthly spend across recurring SaaS subscriptions, live cloud integrations, and manual cost entries."
      actions={
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => setShowForm(true)}
        >
          <Plus size={15} />
          <span>Add Manual Cost</span>
        </button>
      }
    >
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

      {/* KPI Metrics */}
      <section className="overview-metrics-grid" aria-label="Cost Breakdown">
        <MetricCard
          label="Total Monthly Run Rate"
          value={total}
          subtext={
            currencies.length === 1
              ? "Normalized 30-day run rate"
              : currencies.length > 1
              ? "See currency breakdown below"
              : "No eligible spend data"
          }
          icon={<CircleDollarSign size={20} />}
        />
        <MetricCard
          label="Highest Spend Provider"
          value={highestService?.service || "—"}
          subtext={
            highestService
              ? `${highestService.currency} ${Number(highestService.monthly_spend).toLocaleString()}/mo`
              : "No provider data"
          }
          icon={<TrendingUp size={20} />}
        />
        <MetricCard
          label="Tracked Cost Sources"
          value={data?.services.length ?? 0}
          subtext="Active subscriptions & invoices"
          icon={<Receipt size={20} />}
        />
      </section>

      {/* Spend Data Table Section */}
      <section className="dashboard-content-card mt-6">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Cost Analysis Ledger</h2>
            <p className="card-subheading">
              Original billed amounts normalized to 30-day intervals without synthetic currency skew.
            </p>
          </div>

          <div className="card-header-actions">
            <div className="filter-search-box table-search-box">
              <Search size={15} className="search-icon" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by service or source…"
                aria-label="Search cost records"
              />
            </div>
          </div>
        </div>

        {!data ? (
          <div className="hub-data-empty">
            <div className="hub-spinner" />
            <span>Aggregating cost telemetry…</span>
          </div>
        ) : filteredServices.length === 0 ? (
          <EmptyState
            icon={<CircleDollarSign size={28} />}
            title="No spending data available"
            description="Connect a cloud provider (AWS, Azure, OpenAI) or add manual monthly cost entries."
            action={
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setShowForm(true)}
              >
                <Plus size={15} />
                <span>Add Cost Record</span>
              </button>
            }
          />
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Service / Provider</th>
                  <th>Monthly Spend</th>
                  <th>Currency</th>
                  <th>Source</th>
                  <th>Billing Interval</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredServices.map((row, idx) => (
                  <tr key={`${row.service}-${row.billing_period}-${idx}`}>
                    <td>
                      <span className="font-semibold text-primary">{row.service}</span>
                    </td>
                    <td>
                      <span className="font-semibold text-primary">
                        {Number(row.monthly_spend).toLocaleString()}
                      </span>
                    </td>
                    <td>
                      <span className="badge-tag">{row.currency}</span>
                    </td>
                    <td>
                      <span className="text-secondary">{row.billing_source}</span>
                    </td>
                    <td>
                      <span className="text-muted capitalize">
                        {String(row.billing_period)}
                      </span>
                    </td>
                    <td>
                      <StatusBadge
                        variant={row.status === "ACTIVE" ? "success" : "neutral"}
                        size="sm"
                      >
                        {row.status}
                      </StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Add Manual Cost Modal */}
      {showForm && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !saving) setShowForm(false);
          }}
        >
          <div className="modal-dialog modal-dialog-lg" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-header-title-row">
                <Plus size={20} className="text-accent" />
                <h3>Add Manual Cost Entry</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowForm(false)}
                disabled={saving}
              >
                <X size={17} />
              </button>
            </div>

            <form onSubmit={submit}>
              <div className="modal-body space-y-4">
                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Provider or Service Name <span className="text-danger">*</span></label>
                    <input
                      name="provider"
                      required
                      placeholder="e.g. Snowflake, Datadog, GitHub"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Billing Amount <span className="text-danger">*</span></label>
                    <input
                      name="amount"
                      type="number"
                      min="0"
                      step="0.000001"
                      required
                      placeholder="e.g. 450.00"
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Currency <span className="text-danger">*</span></label>
                    <input
                      name="currency"
                      defaultValue="USD"
                      maxLength={3}
                      required
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Billing Interval <span className="text-danger">*</span></label>
                    <select name="billing_interval" defaultValue="monthly" className="form-select">
                      <option value="monthly">Monthly</option>
                      <option value="annual">Annual</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="weekly">Weekly</option>
                    </select>
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Period Start Date <span className="text-danger">*</span></label>
                    <input name="period_start" type="date" required className="form-input" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Note / Invoice Reference</label>
                    <input
                      name="note"
                      placeholder="PO #49281, Annual commit"
                      className="form-input"
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowForm(false)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  <Plus size={15} />
                  <span>{saving ? "Saving…" : "Save Cost Entry"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardFrame>
  );
}

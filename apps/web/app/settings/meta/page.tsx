"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Activity, ArrowLeft, CheckCircle2, CircleAlert, ClipboardList, LoaderCircle,
  RefreshCw, ShieldAlert, Webhook, Wrench,
} from "lucide-react";
import { Alert } from "@/components/ui";
import { useToast } from "@/components/toast";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type {
  MetaDiagnostics,
  MetaHealth,
  MetaHealthSection,
  MetaMcpStatus,
  MetaWebhookRepairPreview,
  MetaWebhookTestHistory,
} from "@/types";

type TimeRange = "1h" | "24h" | "7d" | "30d";

function statusClass(status?: string) {
  const s = (status || "UNKNOWN").toUpperCase();
  if (s === "HEALTHY" || s === "OK") return "healthy";
  if (s === "WARNING" || s === "THROTTLED" || s === "INFO") return "warning";
  if (s === "CRITICAL" || s === "UNAVAILABLE") return "critical";
  return "unknown";
}

function StatusChip({ status }: { status?: string }) {
  const value = (status || "UNKNOWN").toUpperCase();
  return <span className={`meta-status ${statusClass(value)}`}>{value}</span>;
}

function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="meta-progress" role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}>
      <div className={`meta-progress-fill ${clamped >= 90 ? "critical" : clamped >= 70 ? "warning" : "ok"}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}

function MetaCard({
  title,
  hint,
  section,
  children,
}: {
  title: string;
  hint?: string;
  section?: MetaHealthSection | null;
  children?: ReactNode;
}) {
  const pct = section?.percentage;
  return (
    <article className="meta-card">
      <header>
        <div>
          <h3>{title}</h3>
          {hint && <p>{hint}</p>}
        </div>
        <StatusChip status={section?.status} />
      </header>
      {typeof pct === "number" && (
        <div className="meta-pct">
          <strong>{Math.round(pct)}%</strong>
          <ProgressBar value={pct} />
        </div>
      )}
      {children}
    </article>
  );
}

export default function MetaSettingsPage() {
  const t = useT();
  const toast = useToast();
  const [status, setStatus] = useState<MetaMcpStatus | null>(null);
  const [health, setHealth] = useState<MetaHealth | null>(null);
  const [diagnostics, setDiagnostics] = useState<MetaDiagnostics | null>(null);
  const [tests, setTests] = useState<MetaWebhookTestHistory[]>([]);
  const [repairPreview, setRepairPreview] = useState<MetaWebhookRepairPreview | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>("24h");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadStatus = useCallback(async () => {
    const s = await api<MetaMcpStatus>("/meta/status");
    setStatus(s);
    return s;
  }, []);

  const loadHealth = useCallback(async (range: TimeRange, force = false) => {
    const q = new URLSearchParams({ time_range: range, force: String(force) });
    const h = await api<MetaHealth>(`/meta/health?${q}`);
    setHealth(h);
    return h;
  }, []);

  const loadTests = useCallback(async () => {
    try {
      setTests(await api<MetaWebhookTestHistory[]>("/meta/webhooks/tests"));
    } catch {
      setTests([]);
    }
  }, []);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError("");
      try {
        const s = await loadStatus();
        if (s.enabled) {
          await Promise.all([loadHealth(timeRange), loadTests()]);
        }
      } catch (err) {
        setError(messageFrom(err));
      } finally {
        setLoading(false);
      }
    })();
    // initial load only; timeRange changes handled by select handler
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onTimeRange(next: TimeRange) {
    setTimeRange(next);
    if (!status?.enabled) return;
    setBusy(true);
    try {
      await loadHealth(next);
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    setBusy(true);
    try {
      const h = await api<MetaHealth>(`/meta/health/refresh?time_range=${timeRange}`, { method: "POST" });
      setHealth(h);
      toast.success(t("meta.refreshDone"));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function runDiagnostics() {
    setBusy(true);
    try {
      const d = await api<MetaDiagnostics>("/meta/diagnostics", { method: "POST" });
      setDiagnostics(d);
      if (d.health) setHealth(d.health);
      toast.success(t("meta.diagnosticsDone"));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function testWebhook() {
    setBusy(true);
    try {
      const result = await api<{ status: string; error: string | null }>("/meta/webhooks/test", {
        method: "POST",
        body: JSON.stringify({ field: "messages" }),
      });
      await loadTests();
      if (result.error || result.status === "failed") {
        toast.error(result.error || t("meta.webhookTestFailed"));
      } else {
        toast.success(t("meta.webhookTestDone"));
      }
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function openRepairPreview() {
    setBusy(true);
    try {
      setRepairPreview(await api<MetaWebhookRepairPreview>("/meta/webhooks/repair/preview"));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function confirmRepair() {
    setBusy(true);
    try {
      await api("/meta/webhooks/repair", { method: "POST", body: JSON.stringify({ confirm: true }) });
      setRepairPreview(null);
      await loadHealth(timeRange, true);
      toast.success(t("meta.repairDone"));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <div className="page-loading"><LoaderCircle className="spin" /> {t("meta.loading")}</div>;
  }

  const disabled = status && !status.enabled;

  return (
    <div className="page wa-page meta-page">
      <div className="wa-header">
        <Link className="button ghost" href="/settings"><ArrowLeft size={16} /></Link>
        <div>
          <span>{t("meta.eyebrow")}</span>
          <h1>{t("meta.title")}</h1>
          <p>{t("meta.description")}</p>
        </div>
        {health && <StatusChip status={health.overall_status} />}
      </div>

      {error && <Alert>{error}</Alert>}

      {disabled ? (
        <section className="wa-panel">
          <div className="wa-panel-head">
            <span><ShieldAlert size={19} /></span>
            <div>
              <h2>{t("meta.disabledTitle")}</h2>
              <p>{t("meta.disabledCopy")}</p>
            </div>
          </div>
        </section>
      ) : (
        <>
          <section className="wa-panel meta-toolbar">
            <div className="meta-toolbar-row">
              <label>
                {t("meta.timeRange")}
                <select value={timeRange} disabled={busy} onChange={(e) => onTimeRange(e.target.value as TimeRange)}>
                  <option value="1h">{t("meta.range1h")}</option>
                  <option value="24h">{t("meta.range24h")}</option>
                  <option value="7d">{t("meta.range7d")}</option>
                  <option value="30d">{t("meta.range30d")}</option>
                </select>
              </label>
              <div className="meta-fetched">
                <small>{t("meta.lastFetched")}</small>
                <strong>
                  {health?.fetched_at ? new Date(health.fetched_at).toLocaleString() : t("meta.neverFetched")}
                </strong>
              </div>
              {(status?.mock_mode || health?.mock_mode) && <span className="meta-badge">{t("meta.mockBadge")}</span>}
            </div>
            {status && !status.manage_enabled && <p className="meta-note">{t("meta.manageOff")}</p>}
            <div className="wa-actions">
              <button type="button" className="button secondary" disabled={busy} onClick={refresh}>
                {busy ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={16} />} {t("meta.refresh")}
              </button>
              <button type="button" className="button secondary" disabled={busy} onClick={runDiagnostics}>
                <ClipboardList size={16} /> {t("meta.runDiagnostics")}
              </button>
              <button type="button" className="button secondary" disabled={busy} onClick={testWebhook}>
                <Webhook size={16} /> {t("meta.testWebhook")}
              </button>
              <button type="button" className="button primary" disabled={busy} onClick={openRepairPreview}>
                <Wrench size={16} /> {t("meta.compareRepair")}
              </button>
            </div>
          </section>

          {health?.message && <Alert type="info">{health.message}</Alert>}

          {!!health?.alerts?.length && (
            <section className="wa-panel">
              <div className="wa-panel-head"><span><CircleAlert size={19} /></span><div><h2>{t("meta.alerts")}</h2></div></div>
              <ul className="meta-alert-list">
                {health.alerts.map((a, i) => (
                  <li key={`${a.code || "a"}-${i}`}><StatusChip status={a.level} /> {a.message}</li>
                ))}
              </ul>
            </section>
          )}

          <div className="meta-grid">
            <MetaCard title={t("meta.cardApp")} section={health?.app}>
              {health?.app_id && <p className="meta-detail"><small>App ID</small><strong>{health.app_id}</strong></p>}
            </MetaCard>

            <MetaCard
              title={t("meta.cardApiUsage")}
              hint={health?.api_usage?.label || t("meta.cardApiUsageHint")}
              section={health?.api_usage}
            >
              <div className="meta-kv">
                <div><small>{t("meta.callVolume")}</small><strong>{health?.api_usage?.call_volume ?? "—"}</strong></div>
                <div><small>{t("meta.limit")}</small><strong>{health?.api_usage?.limit ?? "—"}</strong></div>
                <div><small>{t("meta.window")}</small><strong>{health?.api_usage?.window ?? timeRange}</strong></div>
              </div>
            </MetaCard>

            <MetaCard title={t("meta.cardRateLimits")} section={health?.rate_limits}>
              <div className="meta-kv">
                <div><small>{t("meta.throttle")}</small><strong>{health?.rate_limits?.throttle_status ?? "—"}</strong></div>
                <div>
                  <small>{t("meta.recovery")}</small>
                  <strong>
                    {health?.rate_limits?.estimated_recovery_minutes != null
                      ? t("meta.minutes", { n: health.rate_limits.estimated_recovery_minutes })
                      : "—"}
                  </strong>
                </div>
              </div>
            </MetaCard>

            <MetaCard title={t("meta.cardWebhooks")} section={health?.webhooks}>
              <div className="meta-kv">
                <div>
                  <small>{t("meta.missingFields")}</small>
                  <strong>{(health?.webhooks?.missing || []).join(", ") || t("meta.none")}</strong>
                </div>
                <div>
                  <small>{t("meta.presentFields")}</small>
                  <strong>{(health?.webhooks?.present || []).join(", ") || t("meta.none")}</strong>
                </div>
              </div>
            </MetaCard>

            <MetaCard title={t("meta.cardAppReview")} section={health?.app_review}>
              {(health?.app_review?.items || []).length ? (
                <ul className="meta-mini-list">
                  {health!.app_review.items!.map((item, i) => (
                    <li key={i}>
                      <span>{String(item.permission || item.name || "—")}</span>
                      <StatusChip status={String(item.status || "")} />
                    </li>
                  ))}
                </ul>
              ) : <p className="meta-empty">{t("meta.noPermissions")}</p>}
            </MetaCard>

            <MetaCard title={t("meta.cardCompliance")} section={health?.compliance}>
              {(health?.compliance?.actions || []).length ? (
                <ul className="meta-mini-list">
                  {health!.compliance.actions!.map((action, i) => (
                    <li key={i}><span>{typeof action === "string" ? action : JSON.stringify(action)}</span></li>
                  ))}
                </ul>
              ) : <p className="meta-empty">{t("meta.noActions")}</p>}
            </MetaCard>

            <MetaCard title={t("meta.cardDeprecations")} section={health?.deprecations}>
              <p className="meta-detail">
                <small>{t("meta.items")}</small>
                <strong>{t("meta.count", { n: health?.deprecations?.count ?? 0 })}</strong>
              </p>
              {(health?.deprecations?.items || []).length ? (
                <ul className="meta-mini-list">
                  {health!.deprecations.items!.map((item, i) => (
                    <li key={i}><span>{typeof item === "string" ? item : JSON.stringify(item)}</span></li>
                  ))}
                </ul>
              ) : <p className="meta-empty">{t("meta.noDeprecations")}</p>}
            </MetaCard>
          </div>

          {repairPreview && (
            <section className="wa-panel">
              <div className="wa-panel-head">
                <span><Wrench size={19} /></span>
                <div>
                  <h2>{t("meta.repairPreviewTitle")}</h2>
                  <p>{repairPreview.note || t("meta.repairExtraNote")}</p>
                </div>
              </div>
              {repairPreview.changes.length === 0 ? (
                <p className="meta-empty">{t("meta.repairPreviewEmpty")}</p>
              ) : (
                <>
                  <p><strong>{t("meta.repairChanges")}</strong></p>
                  <ul className="meta-mini-list">
                    {repairPreview.changes.map((c, i) => (
                      <li key={i}><span>{c.op || "add"} · {c.field}</span></li>
                    ))}
                  </ul>
                </>
              )}
              <div className="wa-actions">
                <button type="button" className="button ghost" disabled={busy} onClick={() => setRepairPreview(null)}>
                  {t("meta.repairCancel")}
                </button>
                {repairPreview.changes.length > 0 && (
                  <button type="button" className="button primary" disabled={busy || !repairPreview.manage_enabled} onClick={confirmRepair}>
                    {busy ? <LoaderCircle className="spin" size={16} /> : <CheckCircle2 size={16} />} {t("meta.repairConfirm")}
                  </button>
                )}
              </div>
            </section>
          )}

          {diagnostics && (
            <section className="wa-panel">
              <div className="wa-panel-head">
                <span><Activity size={19} /></span>
                <div>
                  <h2>{t("meta.diagnosticsTitle")}</h2>
                  <p>
                    {t("meta.diagnosticsSummary", {
                      healthy: diagnostics.summary.healthy,
                      attention: diagnostics.summary.attention,
                      total: diagnostics.summary.total,
                    })}
                  </p>
                </div>
                <StatusChip status={diagnostics.status} />
              </div>
              <ul className="meta-mini-list">
                {diagnostics.checks.map((c) => (
                  <li key={c.name}>
                    <span>{c.name}{c.message ? ` — ${c.message}` : ""}</span>
                    <StatusChip status={c.status} />
                  </li>
                ))}
              </ul>
            </section>
          )}

          {!!tests.length && (
            <section className="wa-panel">
              <div className="wa-panel-head"><span><Webhook size={19} /></span><div><h2>{t("meta.webhookTests")}</h2></div></div>
              <ul className="meta-mini-list">
                {tests.map((row) => (
                  <li key={row.id}>
                    <span>
                      {row.event_type} · {row.test_id.slice(0, 8)}…
                      {row.latency_ms != null ? ` · ${t("meta.ms", { n: row.latency_ms })}` : ""}
                    </span>
                    <StatusChip status={row.status} />
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

    </div>
  );
}

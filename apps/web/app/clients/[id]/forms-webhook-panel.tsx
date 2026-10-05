"use client";

import { useEffect, useMemo, useState } from "react";
import { Copy, LoaderCircle, Webhook } from "lucide-react";
import { useToast } from "@/components/toast";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { LeadCaptureSettings } from "@/types";

const SAMPLE = `{
  "source": "form",
  "name": "...",
  "email": "...",
  "phone": "...",
  "channel_identifier": "..."
}`;

export function FormsWebhookPanel({ clientId }: { clientId: string }) {
  const t = useT();
  const toast = useToast();
  const [settings, setSettings] = useState<LeadCaptureSettings | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  function load() {
    api<LeadCaptureSettings>(`/clients/${clientId}/lead-capture`)
      .then(setSettings)
      .catch((err) => toast.error(messageFrom(err)));
  }

  useEffect(() => {
    load();
  }, [clientId]);

  const ingestUrl = useMemo(() => {
    if (!settings) return "";
    const origin = typeof window === "undefined" ? "" : window.location.origin;
    return `${origin}/api/public/lead-capture/${settings.ingest_token}`;
  }, [settings]);

  async function copyUrl() {
    await navigator.clipboard.writeText(ingestUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function rotate() {
    setBusy(true);
    try {
      const saved = await api<LeadCaptureSettings>(`/clients/${clientId}/lead-capture/token`, { method: "POST" });
      setSettings(saved);
      toast.success(t("channels.formsWebhook.tokenRotated"));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (!settings) {
    return (
      <div className="page-loading">
        <LoaderCircle className="spin" /> {t("common.loading")}
      </div>
    );
  }

  const last = settings.last_ingest_at ? new Date(settings.last_ingest_at).toLocaleString() : t("channels.formsWebhook.never");
  const status = settings.last_ingest_status || t("channels.formsWebhook.idle");

  return (
    <section className="form-section" id="forms-webhooks">
      <div className="section-copy">
        <h2>{t("channels.formsWebhook.title")}</h2>
        <p>{t("channels.formsWebhook.description")}</p>
      </div>
      <div className="form-fields">
        <details className="guide-accordion" open>
          <summary>{t("channels.formsWebhook.guideTitle")}</summary>
          <p>{t("channels.formsWebhook.guideIntro")}</p>
          <ol className="guide-steps">
            <li>{t("channels.formsWebhook.step1")}</li>
            <li>{t("channels.formsWebhook.step2")}</li>
            <li>{t("channels.formsWebhook.step3")}</li>
            <li>{t("channels.formsWebhook.step4")}</li>
            <li>{t("channels.formsWebhook.step5")}</li>
          </ol>
        </details>
        <div className="metrics-grid">
          <article className="metric-card">
            <div>
              <small>{t("channels.formsWebhook.statusLabel")}</small>
              <strong>{status}</strong>
            </div>
          </article>
          <article className="metric-card">
            <div>
              <small>{t("channels.formsWebhook.lastReceived")}</small>
              <strong style={{ fontSize: 16 }}>{last}</strong>
            </div>
          </article>
          <article className="metric-card">
            <div>
              <small>{t("channels.formsWebhook.leadsCreated")}</small>
              <strong>{settings.leads_created_count ?? 0}</strong>
            </div>
          </article>
        </div>
        <label>
          {t("channels.formsWebhook.endpoint")}
          <div className="slug-input">
            <code style={{ flex: 1, overflow: "auto" }}>{ingestUrl}</code>
            <button type="button" className="button secondary" onClick={copyUrl}>
              <Copy size={15} /> {copied ? t("channels.formsWebhook.copied") : t("channels.formsWebhook.copyUrl")}
            </button>
          </div>
        </label>
        <label>
          {t("channels.formsWebhook.token")}
          <input readOnly value={settings.ingest_token} />
        </label>
        <label>
          {t("channels.formsWebhook.payloadTitle")}
          <textarea readOnly rows={8} value={SAMPLE} />
          <span className="field-help">{t("channels.formsWebhook.payloadHint")}</span>
        </label>
        <div className="form-footer">
          <button type="button" className="button secondary" disabled={busy} onClick={rotate}>
            {busy ? <LoaderCircle className="spin" size={17} /> : <Webhook size={17} />} {t("channels.formsWebhook.rotate")}
          </button>
        </div>
      </div>
    </section>
  );
}

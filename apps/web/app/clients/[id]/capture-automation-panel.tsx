"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { LoaderCircle, Save } from "lucide-react";
import { useToast } from "@/components/toast";
import { api, messageFrom } from "@/lib/api";
import { useT, type I18nKey } from "@/lib/i18n";
import type { LeadCaptureSettings } from "@/types";

const CHANNELS: { id: string; label: I18nKey }[] = [
  { id: "whatsapp", label: "leads.sourceWhatsapp" },
  { id: "instagram", label: "leads.sourceInstagram" },
  { id: "facebook", label: "leads.sourceFacebook" },
  { id: "widget", label: "leads.sourceWidget" },
  { id: "form", label: "leads.sourceForm" },
  { id: "webhook", label: "leads.sourceWebhook" },
];

const TRIGGERS: { id: string; label: I18nKey }[] = [
  { id: "new_contact", label: "automations.triggerNewContact" },
  { id: "new_message", label: "automations.triggerNewMessage" },
  { id: "form", label: "automations.triggerForm" },
  { id: "webhook", label: "automations.triggerWebhook" },
];

export function CaptureAutomationPanel({ clientId, showClientLink = false }: { clientId: string; showClientLink?: boolean }) {
  const t = useT();
  const toast = useToast();
  const [settings, setSettings] = useState<LeadCaptureSettings | null>(null);
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<LeadCaptureSettings>(`/clients/${clientId}/lead-capture`)
      .then((next) => {
        setSettings(next);
        setTags((next.auto_tags || []).join(", "));
      })
      .catch((err) => toast.error(messageFrom(err)));
  }, [clientId]);

  const triggers = settings?.automation_config?.triggers || ["new_contact", "form", "webhook"];

  function toggleSource(source: string) {
    if (!settings) return;
    const current = settings.sources || [];
    const next = current.includes(source) ? current.filter((item) => item !== source) : [...current, source];
    setSettings({ ...settings, sources: next });
  }

  function toggleTrigger(trigger: string) {
    if (!settings) return;
    const current = triggers;
    const next = current.includes(trigger) ? current.filter((item) => item !== trigger) : [...current, trigger];
    setSettings({
      ...settings,
      automation_config: { ...settings.automation_config, triggers: next },
    });
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!settings) return;
    setBusy(true);
    try {
      const saved = await api<LeadCaptureSettings>(`/clients/${clientId}/lead-capture`, {
        method: "PUT",
        body: JSON.stringify({
          enabled: settings.enabled,
          sources: settings.sources,
          default_pipeline_id: settings.default_pipeline_id,
          default_stage_id: settings.default_stage_id,
          default_assignee_user_id: settings.default_assignee_user_id,
          auto_tags: tags.split(",").map((item) => item.trim()).filter(Boolean),
          notify_on_new_lead: settings.notify_on_new_lead,
          automation_config: {
            triggers,
            require_commercial_intent: Boolean(settings.automation_config?.require_commercial_intent),
          },
        }),
      });
      setSettings(saved);
      setTags((saved.auto_tags || []).join(", "));
      toast.success(t("leads.saved"));
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

  const stages = settings.pipeline?.stages || [];

  return (
    <form className="page-form" onSubmit={save}>
      <section className="form-section">
        <div className="section-copy">
          <h2>{t("automations.captureTitle")}</h2>
          <p>{t("automations.captureCopy")}</p>
          {showClientLink && (
            <p>
              <Link href={`/clients/${clientId}?tab=automations`}>{t("automations.captureOpenClient")}</Link>
            </p>
          )}
        </div>
        <div className="form-fields">
          <label className="switch-row">
            <span>
              <strong>{t("leads.captureTitle")}</strong>
              <small>{t("leads.captureHint")}</small>
            </span>
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
            />
          </label>
          <fieldset>
            <legend>{t("automations.triggerTitle")}</legend>
            {TRIGGERS.map((item) => (
              <label key={item.id} className="switch-row">
                <span>{t(item.label)}</span>
                <input type="checkbox" checked={triggers.includes(item.id)} onChange={() => toggleTrigger(item.id)} />
              </label>
            ))}
          </fieldset>
          <fieldset>
            <legend>{t("automations.conditionsTitle")}</legend>
            <p className="field-help">{t("automations.conditionChannel")}</p>
            {CHANNELS.map((item) => (
              <label key={item.id} className="switch-row">
                <span>{t(item.label)}</span>
                <input type="checkbox" checked={(settings.sources || []).includes(item.id)} onChange={() => toggleSource(item.id)} />
              </label>
            ))}
            <p className="field-help">{t("automations.conditionOrigin")}</p>
            <label className="switch-row">
              <span>{t("automations.conditionIntent")}</span>
              <input
                type="checkbox"
                checked={Boolean(settings.automation_config?.require_commercial_intent)}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    automation_config: { ...settings.automation_config, require_commercial_intent: e.target.checked },
                  })
                }
              />
            </label>
            <label>
              {t("automations.conditionTags")}
              <input value={tags} onChange={(e) => setTags(e.target.value)} />
            </label>
          </fieldset>
          <fieldset>
            <legend>{t("automations.actionsTitle")}</legend>
            <p className="field-help">{t("automations.actionCreate")}</p>
            <label>
              {t("leads.initialStage")}
              <select
                value={settings.default_stage_id || ""}
                onChange={(e) => setSettings({ ...settings, default_stage_id: e.target.value || null })}
              >
                {stages.map((stage) => (
                  <option key={stage.id} value={stage.id}>
                    {stage.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t("automations.actionAssign")}
              <select
                value={settings.default_assignee_user_id || ""}
                onChange={(e) => setSettings({ ...settings, default_assignee_user_id: e.target.value || null })}
              >
                <option value="">{t("leads.assigneeNone")}</option>
                {settings.assignees.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="switch-row">
              <span>{t("automations.actionNotify")}</span>
              <input
                type="checkbox"
                checked={settings.notify_on_new_lead}
                onChange={(e) => setSettings({ ...settings, notify_on_new_lead: e.target.checked })}
              />
            </label>
          </fieldset>
          <p className="field-help">
            {t("automations.laterTitle")}: {t("automations.laterScoring")}, {t("automations.laterFollowup")}, {t("automations.laterCalendar")}, {t("automations.laterDocuments")}, {t("automations.laterOnboarding")}.
          </p>
        </div>
      </section>
      <div className="form-footer">
        <button className="button primary" disabled={busy}>
          {busy ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />} {t("common.save")}
        </button>
      </div>
    </form>
  );
}

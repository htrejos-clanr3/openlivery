"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { LoaderCircle, Plus, Save, UserRound } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { useToast } from "@/components/toast";
import { api, messageFrom } from "@/lib/api";
import { useT, type I18nKey } from "@/lib/i18n";
import type { LeadCaptureSettings, LeadRecord, LeadStats } from "@/types";

const SIMPLE_SOURCES: { id: string; label: I18nKey }[] = [
  { id: "whatsapp", label: "leads.sourceWhatsapp" },
  { id: "instagram", label: "leads.sourceInstagram" },
  { id: "facebook", label: "leads.sourceFacebook" },
  { id: "widget", label: "leads.sourceWidget" },
  { id: "form", label: "leads.sourceForm" },
];

const SOURCE_LABELS: Record<string, I18nKey> = {
  whatsapp: "leads.sourceWhatsapp",
  instagram: "leads.sourceInstagram",
  facebook: "leads.sourceFacebook",
  form: "leads.sourceForm",
  webhook: "leads.sourceWebhook",
  widget: "leads.sourceWidget",
};

function when(iso?: string | null) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

export function LeadsPanel({ clientId }: { clientId: string }) {
  const t = useT();
  const toast = useToast();
  const [settings, setSettings] = useState<LeadCaptureSettings | null>(null);
  const [stats, setStats] = useState<LeadStats | null>(null);
  const [leadsList, setLeadsList] = useState<LeadRecord[]>([]);
  const [q, setQ] = useState("");
  const [stageId, setStageId] = useState("");
  const [owner, setOwner] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<LeadRecord | null>(null);
  const [creating, setCreating] = useState(false);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (stageId) params.set("stage_id", stageId);
    if (owner === "unassigned") params.set("unassigned", "true");
    else if (owner) params.set("assigned_user_id", owner);
    const text = params.toString();
    return text ? `?${text}` : "";
  }, [q, stageId, owner]);

  function loadList() {
    Promise.all([
      api<LeadCaptureSettings>(`/clients/${clientId}/lead-capture`),
      api<LeadStats>(`/clients/${clientId}/leads/stats`),
      api<LeadRecord[]>(`/clients/${clientId}/leads${query}`),
    ])
      .then(([nextSettings, nextStats, nextLeads]) => {
        setSettings(nextSettings);
        setStats(nextStats);
        setLeadsList(nextLeads);
      })
      .catch((err) => toast.error(messageFrom(err)));
  }

  useEffect(() => {
    loadList();
  }, [clientId, query]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    api<LeadRecord>(`/clients/${clientId}/leads/${selectedId}`)
      .then(setDetail)
      .catch((err) => toast.error(messageFrom(err)));
  }, [clientId, selectedId]);

  if (!settings) {
    return (
      <div className="page-loading">
        <LoaderCircle className="spin" /> {t("common.loading")}
      </div>
    );
  }

  const stages = settings.pipeline?.stages || [];
  const filtered = Boolean(q || stageId || owner);

  return (
    <div className="page-form">
      <section className="form-section">
        <div className="section-copy">
          <h2>{t("leads.title")}</h2>
          <p>{t("leads.copy")}</p>
        </div>
        <div className="form-fields">
          <div className="toolbar filters">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("leads.search")} />
            <select value={stageId} onChange={(e) => setStageId(e.target.value)}>
              <option value="">{t("leads.allStages")}</option>
              {stages.map((stage) => (
                <option key={stage.id} value={stage.id}>
                  {stage.name}
                </option>
              ))}
            </select>
            <select value={owner} onChange={(e) => setOwner(e.target.value)}>
              <option value="">{t("leads.allOwners")}</option>
              <option value="unassigned">{t("leads.unassigned")}</option>
              {settings.assignees.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name}
                </option>
              ))}
            </select>
            <button type="button" className="button primary" onClick={() => { setCreating(true); setSelectedId(null); }}>
              <Plus size={16} /> {t("leads.newLead")}
            </button>
          </div>
          {stats && (
            <div className="metrics-grid">
              <article className="metric-card"><div><small>{t("leads.statNew")}</small><strong>{stats.new_count}</strong></div></article>
              <article className="metric-card"><div><small>{t("leads.statQualified")}</small><strong>{stats.qualified_count}</strong></div></article>
              <article className="metric-card"><div><small>{t("leads.statUnassigned")}</small><strong>{stats.unassigned_count}</strong></div></article>
              <article className="metric-card"><div><small>{t("leads.statStale")}</small><strong>{stats.stale_count}</strong></div></article>
            </div>
          )}
        </div>
      </section>

      {creating && (
        <CreateLeadForm
          clientId={clientId}
          settings={settings}
          onCancel={() => setCreating(false)}
          onCreated={(lead) => {
            setCreating(false);
            setSelectedId(lead.id);
            loadList();
          }}
        />
      )}

      {detail && !creating && (
        <LeadDetail
          clientId={clientId}
          settings={settings}
          lead={detail}
          onClose={() => setSelectedId(null)}
          onChange={(next) => {
            setDetail(next);
            loadList();
          }}
        />
      )}

      {leadsList.length ? (
        <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("leads.colContact")}</th>
                <th>{t("leads.colStage")}</th>
                <th>{t("leads.colScore")}</th>
                <th>{t("leads.colSource")}</th>
                <th>{t("leads.colOwner")}</th>
                <th>{t("leads.colActivity")}</th>
                <th>{t("leads.colCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {leadsList.map((lead) => (
                <tr key={lead.id} className="lead-row" onClick={() => { setCreating(false); setSelectedId(lead.id); }}>
                  <td>
                    <strong>{lead.contact.name || t("leads.none")}</strong>
                    <div className="field-help">{lead.contact.email || lead.contact.phone || lead.contact.company}</div>
                  </td>
                  <td>{lead.stage_name || t("leads.none")}</td>
                  <td>{lead.score == null ? t("leads.noScore") : lead.score}</td>
                  <td>{t(SOURCE_LABELS[lead.source] || "leads.sourceForm")}</td>
                  <td>{lead.assignee_name || t("leads.noOwner")}</td>
                  <td>{when(lead.last_activity_at)}</td>
                  <td>{when(lead.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          icon={<UserRound />}
          title={filtered ? t("leads.emptyFiltered") : t("leads.empty")}
          description={t("leads.copy")}
        />
      )}

      <SimpleCapture clientId={clientId} settings={settings} onSaved={(next) => setSettings(next)} />
    </div>
  );
}

function SimpleCapture({
  clientId,
  settings,
  onSaved,
}: {
  clientId: string;
  settings: LeadCaptureSettings;
  onSaved: (next: LeadCaptureSettings) => void;
}) {
  const t = useT();
  const toast = useToast();
  const [local, setLocal] = useState(settings);
  const [busy, setBusy] = useState(false);
  useEffect(() => setLocal(settings), [settings]);
  const stages = local.pipeline?.stages || [];

  function toggleSource(source: string) {
    const current = local.sources || [];
    const next = current.includes(source) ? current.filter((item) => item !== source) : [...current, source];
    setLocal({ ...local, sources: next });
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const sources = [...local.sources];
      if ((settings.sources || []).includes("webhook") && !sources.includes("webhook")) sources.push("webhook");
      const saved = await api<LeadCaptureSettings>(`/clients/${clientId}/lead-capture`, {
        method: "PUT",
        body: JSON.stringify({
          enabled: local.enabled,
          sources,
          default_pipeline_id: local.default_pipeline_id,
          default_stage_id: local.default_stage_id,
          default_assignee_user_id: local.default_assignee_user_id,
        }),
      });
      onSaved(saved);
      toast.success(t("leads.saved"));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="page-form" onSubmit={save}>
      <section className="form-section">
        <div className="section-copy">
          <h2>{t("leads.captureTitle")}</h2>
          <p>{t("leads.captureHint")}</p>
        </div>
        <div className="form-fields">
          <label className="switch-row">
            <span>
              <strong>{t("leads.captureTitle")}</strong>
              <small>{local.enabled ? t("common.active") : t("common.inactive")}</small>
            </span>
            <input type="checkbox" checked={local.enabled} onChange={(e) => setLocal({ ...local, enabled: e.target.checked })} />
          </label>
          <fieldset>
            <legend>{t("leads.sources")}</legend>
            {SIMPLE_SOURCES.map((item) => (
              <label key={item.id} className="switch-row">
                <span>{t(item.label)}</span>
                <input type="checkbox" checked={(local.sources || []).includes(item.id)} onChange={() => toggleSource(item.id)} />
              </label>
            ))}
          </fieldset>
          <div className="form-grid">
            <label>
              {t("leads.pipeline")}
              <input readOnly value={local.pipeline?.name || "Principal"} />
            </label>
            <label>
              {t("leads.initialStage")}
              <select value={local.default_stage_id || ""} onChange={(e) => setLocal({ ...local, default_stage_id: e.target.value || null })}>
                {stages.map((stage) => (
                  <option key={stage.id} value={stage.id}>{stage.name}</option>
                ))}
              </select>
            </label>
            <label>
              {t("leads.assignee")}
              <select
                value={local.default_assignee_user_id || ""}
                onChange={(e) => setLocal({ ...local, default_assignee_user_id: e.target.value || null })}
              >
                <option value="">{t("leads.assigneeNone")}</option>
                {local.assignees.map((user) => (
                  <option key={user.id} value={user.id}>{user.name}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="form-footer">
            <button className="button primary" disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />} {t("leads.captureSave")}
            </button>
          </div>
        </div>
      </section>
    </form>
  );
}

function CreateLeadForm({
  clientId,
  settings,
  onCancel,
  onCreated,
}: {
  clientId: string;
  settings: LeadCaptureSettings;
  onCancel: () => void;
  onCreated: (lead: LeadRecord) => void;
}) {
  const t = useT();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const stages = settings.pipeline?.stages || [];

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    try {
      const lead = await api<LeadRecord>(`/clients/${clientId}/leads`, {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          company: data.get("company") || null,
          email: data.get("email") || null,
          phone: data.get("phone") || null,
          source: data.get("source") || "form",
          stage_id: data.get("stage_id") || null,
          assigned_user_id: data.get("assigned_user_id") || null,
          notes: data.get("notes") || "",
        }),
      });
      toast.success(t("leads.leadCreated"));
      onCreated(lead);
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="page-form" onSubmit={save}>
      <section className="form-section">
        <div className="section-copy">
          <h2>{t("leads.createTitle")}</h2>
          <p>{t("leads.createCopy")}</p>
        </div>
        <div className="form-fields">
          <div className="form-grid">
            <label>{t("leads.name")}<input name="name" required /></label>
            <label>{t("leads.company")}<input name="company" /></label>
            <label>{t("leads.email")}<input name="email" type="email" /></label>
            <label>{t("leads.phone")}<input name="phone" /></label>
            <label>
              {t("leads.origin")}
              <select name="source" defaultValue="form">
                {Object.entries(SOURCE_LABELS).map(([id, key]) => (
                  <option key={id} value={id}>{t(key)}</option>
                ))}
              </select>
            </label>
            <label>
              {t("leads.stage")}
              <select name="stage_id" defaultValue={settings.default_stage_id || ""}>
                {stages.map((stage) => (
                  <option key={stage.id} value={stage.id}>{stage.name}</option>
                ))}
              </select>
            </label>
            <label>
              {t("leads.owner")}
              <select name="assigned_user_id" defaultValue={settings.default_assignee_user_id || ""}>
                <option value="">{t("leads.assigneeNone")}</option>
                {settings.assignees.map((user) => (
                  <option key={user.id} value={user.id}>{user.name}</option>
                ))}
              </select>
            </label>
          </div>
          <label>{t("leads.notes")}<textarea name="notes" rows={3} /></label>
          <div className="form-footer split">
            <button type="button" className="button secondary" onClick={onCancel}>{t("leads.cancel")}</button>
            <button className="button primary" disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={17} /> : <Plus size={16} />} {t("leads.create")}
            </button>
          </div>
        </div>
      </section>
    </form>
  );
}

function LeadDetail({
  clientId,
  settings,
  lead,
  onClose,
  onChange,
}: {
  clientId: string;
  settings: LeadCaptureSettings;
  lead: LeadRecord;
  onClose: () => void;
  onChange: (lead: LeadRecord) => void;
}) {
  const t = useT();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const stages = settings.pipeline?.stages || [];

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    try {
      const next = await api<LeadRecord>(`/clients/${clientId}/leads/${lead.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: data.get("name"),
          company: data.get("company") || "",
          email: data.get("email") || null,
          phone: data.get("phone") || null,
          stage_id: data.get("stage_id") || null,
          assigned_user_id: data.get("assigned_user_id") || null,
          tags: String(data.get("tags") || "").split(",").map((item) => item.trim()).filter(Boolean),
          notes: data.get("notes") || "",
          next_action: data.get("next_action") || "",
        }),
      });
      toast.success(t("leads.leadSaved"));
      onChange(next);
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function addNote() {
    if (!note.trim()) return;
    try {
      const next = await api<LeadRecord>(`/clients/${clientId}/leads/${lead.id}/activities`, {
        method: "POST",
        body: JSON.stringify({ message: note.trim(), kind: "note" }),
      });
      setNote("");
      onChange(next);
    } catch (err) {
      toast.error(messageFrom(err));
    }
  }

  return (
    <form className="page-form" onSubmit={save}>
      <section className="form-section">
        <div className="section-copy">
          <h2>{t("leads.detailTitle")}</h2>
          <p>
            <button type="button" className="text-link" onClick={onClose}>{t("leads.closeDetail")}</button>
          </p>
        </div>
        <div className="form-fields">
          <div className="form-grid">
            <label>{t("leads.name")}<input name="name" defaultValue={lead.contact.name} required /></label>
            <label>{t("leads.company")}<input name="company" defaultValue={lead.contact.company || ""} /></label>
            <label>{t("leads.phone")}<input name="phone" defaultValue={lead.contact.phone || ""} /></label>
            <label>{t("leads.email")}<input name="email" type="email" defaultValue={lead.contact.email || ""} /></label>
            <label>
              {t("leads.origin")}
              <input readOnly value={t(SOURCE_LABELS[lead.source] || "leads.sourceForm")} />
            </label>
            <label>
              {t("leads.conversation")}
              {lead.conversation_id ? (
                <Link href={`/clients/${clientId}?tab=inbox`}>{t("leads.openChat")}</Link>
              ) : (
                <input readOnly value={t("leads.noConversation")} />
              )}
            </label>
            <label>
              {t("leads.stage")}
              <select name="stage_id" defaultValue={lead.stage_id || ""}>
                {stages.map((stage) => (
                  <option key={stage.id} value={stage.id}>{stage.name}</option>
                ))}
              </select>
            </label>
            <label>
              {t("leads.owner")}
              <select name="assigned_user_id" defaultValue={lead.assigned_user_id || ""}>
                <option value="">{t("leads.assigneeNone")}</option>
                {settings.assignees.map((user) => (
                  <option key={user.id} value={user.id}>{user.name}</option>
                ))}
              </select>
            </label>
            <label>
              {t("leads.tags")}
              <input name="tags" defaultValue={(lead.tags || []).join(", ")} />
              <span className="field-help">{t("leads.tagsHint")}</span>
            </label>
            <label>
              {t("leads.score")}
              <input readOnly value={lead.score == null ? t("leads.noScore") : String(lead.score)} />
              <span className="field-help">{t("leads.scoreHint")}</span>
            </label>
          </div>
          <label>{t("leads.notes")}<textarea name="notes" rows={4} defaultValue={lead.notes || ""} /></label>
          <label>{t("leads.nextAction")}<input name="next_action" defaultValue={lead.next_action || ""} /></label>
          <div className="form-footer">
            <button className="button primary" disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />} {t("leads.saveLead")}
            </button>
          </div>
          <h3>{t("leads.history")}</h3>
          {(lead.activities || []).length ? (
            <ul className="lead-activity">
              {(lead.activities || []).map((item) => (
                <li key={item.id}>
                  <strong>{item.kind}</strong>
                  <span>{item.message}</span>
                  <small>{when(item.created_at)}</small>
                </li>
              ))}
            </ul>
          ) : (
            <p className="field-help">{t("leads.historyEmpty")}</p>
          )}
          <label>
            {t("leads.addNote")}
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder={t("leads.notePlaceholder")} />
          </label>
          <button type="button" className="button secondary" onClick={addNote}>{t("leads.addNote")}</button>
        </div>
      </section>
    </form>
  );
}

"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { LoaderCircle, Workflow } from "lucide-react";
import { Alert, PageHead } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { CaptureAutomationPanel } from "@/app/clients/[id]/capture-automation-panel";
import type { Client } from "@/types";

type AutoStatus = { deepseek_configured: boolean; model: string; user_id: string; user_name: string };
type AutomationRun = {
  id: string;
  user_id: string;
  kind: "normalize" | "score" | "document" | "copy" | string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  created_at: string;
};

function kindLabel(t: ReturnType<typeof useT>, kind: string) {
  if (kind === "normalize") return t("automations.kindNormalize");
  if (kind === "score") return t("automations.kindScore");
  if (kind === "document") return t("automations.kindDocument");
  return t("automations.kindCopy");
}

function pretty(value: unknown) {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatWhen(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

function ResultBox({ value }: { value: unknown }) {
  const t = useT();
  const [copied, setCopied] = useState(false);
  const text = JSON.stringify(value, null, 2);
  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }
  return (
    <div className="form-fields">
      <div className="form-footer split">
        <strong>{t("automations.result")}</strong>
        <button type="button" className="button secondary" onClick={copy}>
          {copied ? t("automations.copied") : t("automations.copyJson")}
        </button>
      </div>
      <pre className="wa-tech-error" style={{ maxHeight: 360, overflow: "auto" }}>{text}</pre>
    </div>
  );
}

export default function AutomationsPage() {
  const t = useT();
  const [ready, setReady] = useState<AutoStatus | null>(null);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [captureClientId, setCaptureClientId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [payload, setPayload] = useState(t("automations.auto1Sample"));
  const [normalizeOut, setNormalizeOut] = useState<unknown>(null);
  const [scoreOut, setScoreOut] = useState<unknown>(null);
  const [template, setTemplate] = useState(t("automations.auto3Template"));
  const [variables, setVariables] = useState(t("automations.auto3Vars"));
  const [docType, setDocType] = useState("proposal");
  const [docOut, setDocOut] = useState<unknown>(null);
  const [copyKind, setCopyKind] = useState("reminder_24h");
  const [copyContext, setCopyContext] = useState(t("automations.auto4Context"));
  const [copyOut, setCopyOut] = useState<unknown>(null);
  const [onboardingContext, setOnboardingContext] = useState(t("automations.auto5Context"));
  const [onboardingOut, setOnboardingOut] = useState<unknown>(null);

  useEffect(() => {
    Promise.all([
      api<AutoStatus>("/automations/status"),
      api<AutomationRun[]>("/automations/runs"),
      api<Client[]>("/clients"),
    ])
      .then(([status, history, nextClients]) => {
        setReady(status);
        setRuns(history);
        setClients(nextClients);
        setCaptureClientId((current) => current || nextClients[0]?.id || "");
      })
      .catch((err) => setError(messageFrom(err)));
  }, []);

  function parseJson(raw: string, fallback: unknown) {
    try {
      return JSON.parse(raw);
    } catch {
      return fallback;
    }
  }

  async function run(id: string, fn: () => Promise<void>) {
    setBusy(id);
    setError("");
    try {
      await fn();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(null);
    }
  }

  const blocked = ready && !ready.deepseek_configured;

  async function remember(saved: AutomationRun) {
    setRuns((current) => [saved, ...current.filter((item) => item.id !== saved.id)].slice(0, 50));
    return saved.result;
  }

  function openSaved(saved: AutomationRun) {
    const data = saved.payload;
    if (saved.kind === "normalize") {
      setPayload(pretty(data.payload ?? data));
      setNormalizeOut(saved.result);
      return;
    }
    if (saved.kind === "score") {
      setPayload(pretty(data.payload ?? data));
      setScoreOut(saved.result);
      return;
    }
    if (saved.kind === "document") {
      if (typeof data.template === "string") setTemplate(data.template);
      if (data.variables != null) setVariables(pretty(data.variables));
      if (typeof data.doc_type === "string") setDocType(data.doc_type);
      setDocOut(saved.result);
      return;
    }
    const emailKind = typeof data.kind === "string" ? data.kind : "reminder_24h";
    if (emailKind === "onboarding") {
      setOnboardingContext(pretty(data.context ?? {}));
      setOnboardingOut(saved.result);
      return;
    }
    setCopyKind(emailKind);
    setCopyContext(pretty(data.context ?? {}));
    setCopyOut(saved.result);
  }

  async function onNormalize(event: FormEvent) {
    event.preventDefault();
    await run("normalize", async () => {
      const body = parseJson(payload, payload);
      const saved = await api<AutomationRun>("/automations/normalize", {
        method: "POST",
        body: JSON.stringify({ payload: body }),
      });
      setNormalizeOut(await remember(saved));
    });
  }

  async function onScore(event: FormEvent) {
    event.preventDefault();
    await run("score", async () => {
      const body = parseJson(payload, payload);
      const saved = await api<AutomationRun>("/automations/score", {
        method: "POST",
        body: JSON.stringify({ payload: body }),
      });
      setScoreOut(await remember(saved));
    });
  }

  async function onDocument(event: FormEvent) {
    event.preventDefault();
    await run("document", async () => {
      const saved = await api<AutomationRun>("/automations/document", {
        method: "POST",
        body: JSON.stringify({ template, variables: parseJson(variables, {}), doc_type: docType }),
      });
      setDocOut(await remember(saved));
    });
  }

  async function onCopy(event: FormEvent) {
    event.preventDefault();
    await run("copy", async () => {
      const saved = await api<AutomationRun>("/automations/copy", {
        method: "POST",
        body: JSON.stringify({ kind: copyKind, context: parseJson(copyContext, { notes: copyContext }) }),
      });
      setCopyOut(await remember(saved));
    });
  }

  async function onOnboarding(event: FormEvent) {
    event.preventDefault();
    await run("onboarding", async () => {
      const saved = await api<AutomationRun>("/automations/copy", {
        method: "POST",
        body: JSON.stringify({ kind: "onboarding", context: parseJson(onboardingContext, { notes: onboardingContext }) }),
      });
      setOnboardingOut(await remember(saved));
    });
  }

  return (
    <div className="page">
      <PageHead eyebrow={t("automations.eyebrow")} title={t("automations.title")} description={t("automations.description")} />
      {error && <Alert>{error}</Alert>}
      {blocked && (
        <Alert type="warning">
          <div>
            <p>{t("automations.needKey")}</p>
            <Link className="button primary" href="/settings" style={{ marginTop: 12 }}>{t("automations.openSettings")}</Link>
          </div>
        </Alert>
      )}

      <section className="form-section">
        <div className="section-copy">
          <h2>{t("automations.captureTitle")}</h2>
          <p>{t("automations.captureCopy")}</p>
        </div>
        <div className="form-fields">
          <label>
            {t("automations.captureClient")}
            <select value={captureClientId} onChange={(e) => setCaptureClientId(e.target.value)}>
              <option value="">{t("automations.captureSelectClient")}</option>
              {clients.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>
        </div>
      </section>
      {captureClientId && <CaptureAutomationPanel clientId={captureClientId} showClientLink />}

      <section className="form-section">
        <div className="section-copy">
          <h2>{t("automations.historyTitle")}</h2>
          <p>{ready ? t("automations.historyFor", { name: ready.user_name }) : t("automations.historyEmpty")}</p>
        </div>
        <div className="form-fields">
          {runs.length === 0 ? (
            <p className="field-help">{t("automations.historyEmpty")}</p>
          ) : (
            runs.map((saved) => (
              <div className="form-footer split" key={saved.id} style={{ paddingTop: 0 }}>
                <div>
                  <strong>{kindLabel(t, saved.kind)}</strong>
                  <p className="field-help">{formatWhen(saved.created_at)}</p>
                </div>
                <button type="button" className="button secondary" onClick={() => openSaved(saved)}>
                  {t("automations.openRun")}
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      <form className="page-form" onSubmit={onNormalize}>
        <section className="form-section">
          <div className="section-copy">
            <h2><Workflow size={18} /> {t("automations.auto1Title")}</h2>
            <p>{t("automations.auto1Copy")}</p>
            <p className="field-help">{t("automations.skipHubspot")}</p>
          </div>
          <div className="form-fields">
            <label>
              {t("automations.payload")}
              <textarea rows={10} value={payload} onChange={(e) => setPayload(e.target.value)} />
            </label>
            <div className="form-footer">
              <button className="button primary" disabled={Boolean(busy) || Boolean(blocked)}>
                {busy === "normalize" ? <LoaderCircle className="spin" size={17} /> : null}
                {busy === "normalize" ? t("automations.running") : t("automations.run")}
              </button>
            </div>
            {normalizeOut != null && <ResultBox value={normalizeOut} />}
          </div>
        </section>
      </form>

      <form className="page-form" onSubmit={onScore}>
        <section className="form-section">
          <div className="section-copy">
            <h2>{t("automations.auto2Title")}</h2>
            <p>{t("automations.auto2Copy")}</p>
          </div>
          <div className="form-fields">
            <p className="field-help">{t("automations.payload")} — {t("automations.auto1Title")}</p>
            <div className="form-footer">
              <button className="button primary" disabled={Boolean(busy) || Boolean(blocked)}>
                {busy === "score" ? <LoaderCircle className="spin" size={17} /> : null}
                {busy === "score" ? t("automations.running") : t("automations.run")}
              </button>
            </div>
            {scoreOut != null && <ResultBox value={scoreOut} />}
          </div>
        </section>
      </form>

      <form className="page-form" onSubmit={onDocument}>
        <section className="form-section">
          <div className="section-copy">
            <h2>{t("automations.auto3Title")}</h2>
            <p>{t("automations.auto3Copy")}</p>
          </div>
          <div className="form-fields">
            <label>
              {t("automations.docType")}
              <select value={docType} onChange={(e) => setDocType(e.target.value)}>
                <option value="proposal">{t("automations.proposal")}</option>
                <option value="contract">{t("automations.contract")}</option>
                <option value="invoice">{t("automations.invoice")}</option>
                <option value="report">{t("automations.report")}</option>
              </select>
            </label>
            <label>
              {t("automations.template")}
              <textarea rows={8} value={template} onChange={(e) => setTemplate(e.target.value)} />
            </label>
            <label>
              {t("automations.variables")}
              <textarea rows={8} value={variables} onChange={(e) => setVariables(e.target.value)} />
            </label>
            <div className="form-footer">
              <button className="button primary" disabled={Boolean(busy) || Boolean(blocked)}>
                {busy === "document" ? <LoaderCircle className="spin" size={17} /> : null}
                {busy === "document" ? t("automations.running") : t("automations.run")}
              </button>
            </div>
            {docOut != null && <ResultBox value={docOut} />}
          </div>
        </section>
      </form>

      <form className="page-form" onSubmit={onCopy}>
        <section className="form-section">
          <div className="section-copy">
            <h2>{t("automations.auto4Title")}</h2>
            <p>{t("automations.auto4Copy")}</p>
          </div>
          <div className="form-fields">
            <label>
              {t("automations.copyKind")}
              <select value={copyKind} onChange={(e) => setCopyKind(e.target.value)}>
                <option value="reminder_24h">{t("automations.reminder24")}</option>
                <option value="reminder_1h">{t("automations.reminder1")}</option>
                <option value="followup">{t("automations.followup")}</option>
              </select>
            </label>
            <label>
              {t("automations.copyContext")}
              <textarea rows={7} value={copyContext} onChange={(e) => setCopyContext(e.target.value)} />
            </label>
            <div className="form-footer">
              <button className="button primary" disabled={Boolean(busy) || Boolean(blocked)}>
                {busy === "copy" ? <LoaderCircle className="spin" size={17} /> : null}
                {busy === "copy" ? t("automations.running") : t("automations.run")}
              </button>
            </div>
            {copyOut != null && <ResultBox value={copyOut} />}
          </div>
        </section>
      </form>

      <form className="page-form" onSubmit={onOnboarding}>
        <section className="form-section">
          <div className="section-copy">
            <h2>{t("automations.auto5Title")}</h2>
            <p>{t("automations.auto5Copy")}</p>
          </div>
          <div className="form-fields">
            <label>
              {t("automations.copyContext")}
              <textarea rows={7} value={onboardingContext} onChange={(e) => setOnboardingContext(e.target.value)} />
            </label>
            <div className="form-footer">
              <button className="button primary" disabled={Boolean(busy) || Boolean(blocked)}>
                {busy === "onboarding" ? <LoaderCircle className="spin" size={17} /> : null}
                {busy === "onboarding" ? t("automations.running") : t("automations.run")}
              </button>
            </div>
            {onboardingOut != null && <ResultBox value={onboardingOut} />}
          </div>
        </section>
      </form>
    </div>
  );
}

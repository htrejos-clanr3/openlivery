"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useState } from "react";
import {
  ArrowLeft, BadgeCheck, BookOpen, Bot, CheckCircle2, ChevronDown, CircleAlert, ClipboardCopy, Circle,
  ExternalLink, Inbox, KeyRound, LoaderCircle, Plug, Power, RefreshCw, ShieldCheck, Smartphone, Sparkles, Webhook,
} from "lucide-react";
import { ChannelConnectConsentModal, buildChannelConsent } from "@/components/channel-connect-consent-modal";
import { Alert } from "@/components/ui";
import { api, ApiError, messageFrom } from "@/lib/api";
import { useT, type I18nKey } from "@/lib/i18n";
import type {
  Client,
  WhatsAppCloudChannel,
  WhatsAppCloudHealth,
  WhatsAppCloudTemplate,
  WhatsAppSignupOptions,
  WhatsAppSignupSession,
  WhatsAppWebhookRegistration,
} from "@/types";

type ProgressStep = { id: string; label: string; done: boolean };

type FacebookSdk = {
  init: (cfg: object) => void;
  login: (cb: (res: { authResponse?: { code?: string } }) => void, opts: object) => void;
};

function loadFacebookSdk(appId: string, version: string): Promise<FacebookSdk> {
  const existing = (window as unknown as { FB?: FacebookSdk }).FB;
  if (existing) return Promise.resolve(existing);
  return new Promise((resolve, reject) => {
    const previous = (window as unknown as { fbAsyncInit?: () => void }).fbAsyncInit;
    (window as unknown as { fbAsyncInit?: () => void }).fbAsyncInit = () => {
      previous?.();
      const fb = (window as unknown as { FB?: FacebookSdk }).FB;
      if (!fb) {
        reject(new Error("Facebook SDK failed to initialize"));
        return;
      }
      fb.init({ appId, autoLogAppEvents: true, xfbml: true, version });
      resolve(fb);
    };
    if (!document.getElementById("facebook-jssdk")) {
      const script = document.createElement("script");
      script.id = "facebook-jssdk";
      script.async = true;
      script.src = "https://connect.facebook.net/en_US/sdk.js";
      script.onerror = () => reject(new Error("Facebook SDK script failed to load"));
      document.body.appendChild(script);
    }
    window.setTimeout(() => {
      if (!(window as unknown as { FB?: FacebookSdk }).FB) {
        reject(new Error("Facebook SDK load timeout"));
      }
    }, 15000);
  });
}

function CopyField({ label, value }: { label: string; value: string }) {
  const t = useT();
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }
  return (
    <div className="wa-copy-field">
      <label>{label}<input readOnly value={value} onFocus={(event) => event.currentTarget.select()} /></label>
      <button type="button" className="button secondary" onClick={copy}>
        <ClipboardCopy size={15} /> {copied ? t("clients.whatsappCloud.copied") : t("clients.whatsappCloud.copy")}
      </button>
    </div>
  );
}

function StatusChip({ status }: { status: WhatsAppCloudChannel["status"] }) {
  const t = useT();
  const map: Record<WhatsAppCloudChannel["status"], { label: I18nKey; icon: typeof CheckCircle2 }> = {
    connected: { label: "clients.whatsappCloud.statusConnectedLabel", icon: CheckCircle2 },
    error: { label: "clients.whatsappCloud.statusErrorLabel", icon: CircleAlert },
    disconnected: { label: "clients.whatsappCloud.statusDisconnectedLabel", icon: RefreshCw },
  };
  const item = map[status];
  const Icon = item.icon;
  return <div className={`wa-state ${status}`}><Icon size={17} /> {t(item.label)}</div>;
}

function WhatsAppCloudChannelPageInner() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const [client, setClient] = useState<Client | null>(null);
  const [channel, setChannel] = useState<WhatsAppCloudChannel | null>(null);
  const [health, setHealth] = useState<WhatsAppCloudHealth | null>(null);
  const [options, setOptions] = useState<WhatsAppSignupOptions | null>(null);
  const [agentId, setAgentId] = useState("");
  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [wabaId, setWabaId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [guideManagedOpen, setGuideManagedOpen] = useState(false);
  const [guideByoOpen, setGuideByoOpen] = useState(false);
  const [guideCompareOpen, setGuideCompareOpen] = useState(false);
  const [guideMcpOpen, setGuideMcpOpen] = useState(false);
  const [showSecrets, setShowSecrets] = useState(false);
  const [showTechnical, setShowTechnical] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<ProgressStep[] | null>(null);
  const [offerAgentHelp, setOfferAgentHelp] = useState(false);
  const [consentOpen, setConsentOpen] = useState(false);
  const [webhookReg, setWebhookReg] = useState<WhatsAppWebhookRegistration | null>(null);
  const [templates, setTemplates] = useState<WhatsAppCloudTemplate[]>([]);
  const [templateTo, setTemplateTo] = useState("");
  const [templateNote, setTemplateNote] = useState("");

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await api<WhatsAppCloudHealth>(`/whatsapp-cloud/channels/${id}/health`));
    } catch {
      setHealth(null);
    }
  }, [id]);

  const applyChannel = useCallback((current: WhatsAppCloudChannel) => {
    setChannel(current);
    if (current.webhook_registration) setWebhookReg(current.webhook_registration);
    setAgentId(current.agent_id);
    setPhoneNumberId(current.phone_number_id);
    setWabaId(current.waba_id || "");
  }, []);

  useEffect(() => {
    const loadChannel = api<WhatsAppCloudChannel>(`/whatsapp-cloud/channels/${id}`)
      .then(applyChannel)
      .catch((err) => {
        if (!(err instanceof ApiError && err.status === 404)) throw err;
        setChannel(null);
      });
    Promise.all([
      api<Client>(`/clients/${id}`).then((item) => {
        setClient(item);
        setAgentId((value) => value || item.agents[0]?.id || "");
      }),
      loadChannel,
      api<WhatsAppSignupOptions>("/whatsapp-cloud/signup/options").then(setOptions).catch(() => setOptions(null)),
    ])
      .then(() => refreshHealth())
      .catch((err) => setError(messageFrom(err)))
      .finally(() => setLoading(false));
  }, [id, applyChannel, refreshHealth]);

  useEffect(() => {
    const code = search.get("oauth_code");
    const state = search.get("oauth_state");
    if (!code || !state || !agentId) return;
    (async () => {
      setBusy(true);
      setError("");
      setProgress([
        { id: "auth", label: t("clients.whatsappCloud.stepAuth"), done: true },
        { id: "waba", label: t("clients.whatsappCloud.stepWaba"), done: false },
        { id: "phone", label: t("clients.whatsappCloud.stepPhone"), done: false },
        { id: "permissions", label: t("clients.whatsappCloud.stepPermissions"), done: false },
        { id: "credentials", label: t("clients.whatsappCloud.stepCredentials"), done: false },
        { id: "webhook", label: t("clients.whatsappCloud.stepWebhook"), done: false },
      ]);
      try {
        const result = await api<{ channel: WhatsAppCloudChannel; steps: ProgressStep[] }>(
          `/whatsapp-cloud/channels/${id}/signup/complete`,
          { method: "POST", body: JSON.stringify({ state, code, agent_id: agentId }) },
        );
        applyChannel(result.channel);
        setProgress(result.steps);
        setOfferAgentHelp(true);
        await refreshHealth();
        window.history.replaceState({}, "", `/clients/${id}/channels/whatsapp-cloud`);
      } catch (err) {
        setError(messageFrom(err));
        setProgress(null);
      } finally {
        setBusy(false);
      }
    })();
  }, [search, agentId, id, applyChannel, refreshHealth, t]);

  async function saveAgentOnly() {
    if (!agentId) return;
    setBusy(true); setError("");
    try {
      applyChannel(await api<WhatsAppCloudChannel>(`/whatsapp-cloud/channels/${id}/agent`, {
        method: "PATCH",
        body: JSON.stringify({ agent_id: agentId }),
      }));
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveAdvanced(event?: FormEvent) {
    event?.preventDefault();
    if (!agentId) return;
    setBusy(true); setError("");
    try {
      const payload: Record<string, string> = {
        agent_id: agentId,
        phone_number_id: phoneNumberId.trim(),
        waba_id: wabaId.trim(),
        connection_mode: "manual",
      };
      if (accessToken.trim()) payload.access_token = accessToken.trim();
      if (appSecret.trim()) payload.app_secret = appSecret.trim();
      const saved = await api<WhatsAppCloudChannel>(`/whatsapp-cloud/channels/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      applyChannel(saved);
      setAccessToken("");
      setAppSecret("");
      const connectedChannel = await api<WhatsAppCloudChannel>(`/whatsapp-cloud/channels/${id}/connect`, { method: "POST" });
      applyChannel(connectedChannel);
      await refreshHealth();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function registerWebhookInMeta() {
    setBusy(true); setError("");
    try {
      const result = await api<WhatsAppWebhookRegistration>(`/whatsapp-cloud/channels/${id}/register-webhook`, { method: "POST" });
      setWebhookReg(result);
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function refreshTemplates() {
    setBusy(true); setError(""); setTemplateNote("");
    try {
      const result = await api<{ templates: WhatsAppCloudTemplate[]; count: number }>(`/whatsapp-cloud/channels/${id}/templates`);
      setTemplates(result.templates);
      if (!result.count) setTemplateNote(t("clients.whatsappCloud.templatesEmpty"));
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function sendTemplateTest(name: string, language: string) {
    if (!templateTo.trim()) {
      setError(t("clients.whatsappCloud.templatesSendTo"));
      return;
    }
    setBusy(true); setError(""); setTemplateNote("");
    try {
      await api(`/whatsapp-cloud/channels/${id}/templates/send`, {
        method: "POST",
        body: JSON.stringify({ to: templateTo.trim(), name, language: language || "en_US" }),
      });
      setTemplateNote(t("clients.whatsappCloud.templatesSent"));
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  function requestConnect() {
    if (!agentId) {
      setError(t("clients.whatsapp.needsAgent"));
      return;
    }
    setConsentOpen(true);
  }

  async function connectWithMeta() {
    if (!agentId) {
      setError(t("clients.whatsapp.needsAgent"));
      return;
    }
    setBusy(true); setError(""); setProgress(null);
    try {
      await api(`/whatsapp-cloud/channels/${id}/agent`, { method: "PATCH", body: JSON.stringify({ agent_id: agentId }) });
      const session = await api<WhatsAppSignupSession>(`/whatsapp-cloud/channels/${id}/signup/session`, {
        method: "POST",
        body: JSON.stringify(buildChannelConsent("whatsapp_cloud", id)),
      });
      if (session.mock_mode || options?.mock_mode) {
        setProgress([
          { id: "auth", label: t("clients.whatsappCloud.stepAuth"), done: true },
          { id: "waba", label: t("clients.whatsappCloud.stepWaba"), done: false },
          { id: "phone", label: t("clients.whatsappCloud.stepPhone"), done: false },
          { id: "permissions", label: t("clients.whatsappCloud.stepPermissions"), done: false },
          { id: "credentials", label: t("clients.whatsappCloud.stepCredentials"), done: false },
          { id: "webhook", label: t("clients.whatsappCloud.stepWebhook"), done: false },
        ]);
        const result = await api<{ channel: WhatsAppCloudChannel; steps: ProgressStep[] }>(
          `/whatsapp-cloud/channels/${id}/signup/complete`,
          { method: "POST", body: JSON.stringify({ state: session.state, agent_id: agentId, use_mock: true }) },
        );
        applyChannel(result.channel);
        setProgress(result.steps);
        setOfferAgentHelp(true);
        await refreshHealth();
        return;
      }
      if (session.blocked_reason || !session.meta_app_id) {
        setAdvancedOpen(true);
        setError(t("clients.whatsappCloud.managedUnavailable"));
        return;
      }
      const graphVersion = options?.graph_version || "v23.0";
      let fb: FacebookSdk;
      try {
        fb = await loadFacebookSdk(session.meta_app_id, graphVersion);
      } catch {
        setAdvancedOpen(true);
        setError(t("clients.whatsappCloud.sdkMissing"));
        return;
      }
      fb.login(async (response) => {
        try {
          const code = response.authResponse?.code;
          if (!code) throw new Error(t("clients.whatsappCloud.authCancelled"));
          setProgress([
            { id: "auth", label: t("clients.whatsappCloud.stepAuth"), done: true },
            { id: "waba", label: t("clients.whatsappCloud.stepWaba"), done: false },
            { id: "phone", label: t("clients.whatsappCloud.stepPhone"), done: false },
            { id: "permissions", label: t("clients.whatsappCloud.stepPermissions"), done: false },
            { id: "credentials", label: t("clients.whatsappCloud.stepCredentials"), done: false },
            { id: "webhook", label: t("clients.whatsappCloud.stepWebhook"), done: false },
          ]);
          const result = await api<{ channel: WhatsAppCloudChannel; steps: ProgressStep[] }>(
            `/whatsapp-cloud/channels/${id}/signup/complete`,
            { method: "POST", body: JSON.stringify({ state: session.state, code, agent_id: agentId }) },
          );
          applyChannel(result.channel);
          setProgress(result.steps);
          setOfferAgentHelp(true);
          await refreshHealth();
        } catch (err) {
          setError(messageFrom(err));
          setProgress(null);
        } finally {
          setBusy(false);
        }
      }, { config_id: session.meta_config_id, response_type: "code", override_default_response_type: true });
      return;
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function testConnection() {
    setBusy(true); setError("");
    try {
      setHealth(await api<WhatsAppCloudHealth>(`/whatsapp-cloud/channels/${id}/test`, { method: "POST" }));
      const updated = await api<WhatsAppCloudChannel>(`/whatsapp-cloud/channels/${id}`);
      applyChannel(updated);
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    if (!confirm(t("clients.whatsappCloud.confirmDisconnect"))) return;
    setBusy(true); setError("");
    try {
      applyChannel(await api<WhatsAppCloudChannel>(`/whatsapp-cloud/channels/${id}/disconnect`, { method: "POST" }));
      setProgress(null);
      setOfferAgentHelp(false);
      await refreshHealth();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading || !client) {
    return <div className="page-loading"><LoaderCircle className="spin" /> {t("clients.whatsappCloud.loading")}</div>;
  }

  const connected = channel?.status === "connected" && channel.is_enabled;
  const uiStatus = health?.ui_status || (connected ? "connected" : channel?.status === "error" ? "needs_attention" : "not_configured");
  const oauthRedirectExample = typeof window !== "undefined"
    ? `${window.location.origin}/api/whatsapp-cloud/oauth/callback`
    : "/api/whatsapp-cloud/oauth/callback";
  const setupChecks: { id: string; label: string; done: boolean }[] = [
    { id: "agent", label: t("clients.whatsappCloud.guideCheckAgent"), done: Boolean(agentId) },
    { id: "phone", label: t("clients.whatsappCloud.guideCheckPhone"), done: Boolean(health?.phone_number_id || phoneNumberId.trim()) },
    { id: "token", label: t("clients.whatsappCloud.guideCheckToken"), done: Boolean(health?.token_configured || channel?.has_access_token) },
    { id: "webhook", label: t("clients.whatsappCloud.guideCheckWebhook"), done: Boolean(channel?.webhook_url && channel?.webhook_verify_token) },
    { id: "graph", label: t("clients.whatsappCloud.guideCheckGraph"), done: Boolean(health?.graph_reachable || health?.permissions_valid) },
    { id: "connected", label: t("clients.whatsappCloud.guideCheckConnected"), done: Boolean(connected && health?.connected !== false) },
  ];

  return (
    <div className="page wa-page">
      <Link href={`/clients/${client.id}`} className="back-link">
        <ArrowLeft size={17} /> {t("clients.whatsapp.back", { name: client.name })}
      </Link>
      <header className="wa-header">
        <div className="wa-mark"><BadgeCheck size={26} /></div>
        <div>
          <span>{t("clients.whatsapp.channelOf", { name: client.name })}</span>
          <h1>{t("clients.whatsappCloud.title")}</h1>
          <p>{t("clients.whatsappCloud.heroCopy")}</p>
        </div>
        {channel && <StatusChip status={channel.status} />}
      </header>
      {error && <Alert>{error}</Alert>}

      <div className="wa-layout">
        <main>
          {progress && (
            <section className="wa-panel">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, marginBottom: 14, flexWrap: "wrap" }}>
                <div>
                  <strong>Paso a paso guiado</strong>
                  <p className="field-help" style={{ margin: "4px 0 0" }}>
                    Los diez pasos con el enlace, el valor a pegar y su comprobación después de cada uno.
                  </p>
                </div>
                <Link className="button primary" href={`/clients/${id}/channels/meta-setup`}>
                  Abrir el paso a paso
                </Link>
              </div>

              <div className="wa-panel-head"><span><Sparkles size={19} /></span><div><h2>{t("clients.whatsappCloud.configuringTitle")}</h2><p>{t("clients.whatsappCloud.configuringCopy")}</p></div></div>
              <ul className="wa-progress">
                {progress.map((step) => (
                  <li key={step.id} className={step.done ? "done" : ""}>
                    {step.done ? <CheckCircle2 size={16} /> : <LoaderCircle size={16} className={busy ? "spin" : ""} />}
                    <span>{step.label}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {connected ? (
            <section className="wa-panel wa-status-card">
              <div className="wa-panel-head">
                <span><Smartphone size={19} /></span>
                <div>
                  <h2>{t("clients.whatsappCloud.connectedTitle")}</h2>
                  <p className="wa-live-dot">● {t("clients.whatsappCloud.statusConnectedLabel")}</p>
                </div>
              </div>
              <div className="wa-status-grid">
                <div><small>{t("clients.whatsapp.connectedNumber")}</small><strong>{channel?.phone_number || channel?.phone_number_id}</strong></div>
                <div><small>{t("clients.whatsappCloud.accountLabel")}</small><strong>{channel?.display_name || "—"}</strong></div>
                <div><small>{t("clients.whatsapp.assignedAgent")}</small><strong>{client.agents.find((a) => a.id === channel?.agent_id)?.name || "—"}</strong></div>
                <div><small>{t("clients.whatsappCloud.webhookTitle")}</small><strong>{health?.webhook_configured ? t("clients.whatsappCloud.webhookOk") : t("clients.whatsappCloud.webhookPending")}</strong></div>
                <div><small>{t("clients.whatsappCloud.lastActivity")}</small><strong>{health?.last_inbound_message_at ? new Date(health.last_inbound_message_at).toLocaleString() : t("clients.whatsappCloud.noActivity")}</strong></div>
              </div>
              {(channel?.error_message || health?.error?.message) && (
                <Alert type="info">
                  {channel?.error_message || health?.error?.message}
                  <button type="button" className="text-button" onClick={() => setShowTechnical((v) => !v)}>
                    {t("clients.whatsappCloud.viewTechnical")}
                  </button>
                  {showTechnical && <pre className="wa-tech-error">{channel?.last_error || health?.error?.technical}</pre>}
                </Alert>
              )}
              {health?.meta_platform && (
                <div className="meta-platform-note">
                  <small>{t("meta.channelNoteTitle")}</small>
                  <p>{health.meta_platform.label}</p>
                  <p>{health.meta_platform.message}</p>
                  {health.meta_platform.diagnostics_available && (
                    <Link className="text-button" href="/settings/meta">{t("meta.channelNoteLink")}</Link>
                  )}
                </div>
              )}
              {webhookReg && (
                <Alert type={webhookReg.ok ? "info" : "info"}>
                  <strong>
                    {webhookReg.ok
                      ? webhookReg.code === "skipped_waba_override"
                        ? t("clients.whatsappCloud.webhookRegisterSkipped")
                        : t("clients.whatsappCloud.webhookRegisterOk")
                      : t("clients.whatsappCloud.webhookRegisterFailed")}
                  </strong>
                  <p>{webhookReg.message}</p>
                </Alert>
              )}
              <div className="wa-actions">
                <button className="button primary" onClick={testConnection} disabled={busy}>
                  {busy ? <LoaderCircle className="spin" size={17} /> : <Plug size={17} />} {t("clients.whatsappCloud.testConnection")}
                </button>
                <button className="button secondary" onClick={registerWebhookInMeta} disabled={busy}>
                  {busy ? <LoaderCircle className="spin" size={17} /> : <RefreshCw size={17} />} {t("clients.whatsappCloud.registerWebhook")}
                </button>
                <Link className="button secondary" href="/inbox"><Inbox size={17} /> {t("clients.whatsappCloud.openInbox")}</Link>
                <button className="button danger" onClick={disconnect} disabled={busy}><Power size={17} /> {t("clients.whatsappCloud.disconnect")}</button>
              </div>
              <div className="wa-panel" style={{ marginTop: 16, padding: 0, border: "none", boxShadow: "none" }}>
                <div className="wa-panel-head">
                  <div>
                    <h3>{t("clients.whatsappCloud.templatesTitle")}</h3>
                    <p>{t("clients.whatsappCloud.templatesCopy")}</p>
                  </div>
                </div>
                <label>
                  {t("clients.whatsappCloud.templatesSendTo")}
                  <input value={templateTo} onChange={(e) => setTemplateTo(e.target.value)} placeholder="573001112233" />
                </label>
                <div className="wa-actions">
                  <button type="button" className="button secondary" onClick={refreshTemplates} disabled={busy}>
                    {t("clients.whatsappCloud.templatesRefresh")}
                  </button>
                </div>
                {templateNote && <p className="hint">{templateNote}</p>}
                {templates.length > 0 && (
                  <ul className="wa-progress">
                    {templates.slice(0, 12).map((tpl) => (
                      <li key={`${tpl.name}-${tpl.language}-${tpl.id || ""}`}>
                        <span>
                          <strong>{tpl.name}</strong> · {tpl.language || "—"} · {tpl.status || "—"}
                        </span>
                        <button
                          type="button"
                          className="text-button"
                          disabled={busy || (tpl.status || "").toUpperCase() !== "APPROVED"}
                          onClick={() => sendTemplateTest(tpl.name, tpl.language || "en_US")}
                        >
                          {t("clients.whatsappCloud.templatesSend")}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
          ) : (
            <section className="wa-panel">
              <div className="wa-panel-head">
                <span><BadgeCheck size={19} /></span>
                <div>
                  <h2>{t("clients.whatsappCloud.connectTitle")}</h2>
                  <p>{t("clients.whatsappCloud.connectCopy")}</p>
                </div>
              </div>
              {uiStatus === "needs_attention" && (
                <Alert>
                  {channel?.error_message || health?.error?.message || t("clients.whatsappCloud.statusErrorCopy")}
                  <div className="wa-actions" style={{ marginTop: 12 }}>
                    <button className="button primary" onClick={requestConnect} disabled={busy || !agentId}>
                      {busy ? <LoaderCircle className="spin" size={17} /> : <RefreshCw size={17} />} {t("clients.whatsappCloud.reconnectMeta")}
                    </button>
                  </div>
                </Alert>
              )}
              <div className="wa-actions">
                <button className="button primary" onClick={requestConnect} disabled={busy || !agentId}>
                  {busy ? <LoaderCircle className="spin" size={17} /> : <BadgeCheck size={17} />} {t("clients.whatsappCloud.connectMeta")}
                </button>
              </div>
              <div className="wa-advanced-toggle" style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
                <button type="button" className="text-button" onClick={() => setAdvancedOpen(true)}>
                  {t("clients.whatsappCloud.advancedHint")}
                </button>
                <Link className="button primary" href={`/clients/${id}/channels/meta-setup`}>
                  Abrir el paso a paso guiado
                </Link>
              </div>
              <div className="wa-benefits">
                <h3>{t("clients.whatsappCloud.benefitsTitle")}</h3>
                <ul>
                  <li>✓ {t("clients.whatsappCloud.benefit1")}</li>
                  <li>✓ {t("clients.whatsappCloud.benefit2")}</li>
                  <li>✓ {t("clients.whatsappCloud.benefit3")}</li>
                  <li>✓ {t("clients.whatsappCloud.benefit4")}</li>
                </ul>
              </div>
            </section>
          )}

          <section className="wa-panel wa-accordion-panel">
            <button type="button" className="wa-accordion-trigger" onClick={() => setGuideOpen((v) => !v)} aria-expanded={guideOpen}>
              <span><BookOpen size={19} /></span>
              <div>
                <h2>{t("clients.whatsappCloud.guideTitle")}</h2>
                <p>{t("clients.whatsappCloud.guideCopy")}</p>
              </div>
              <ChevronDown size={18} className={guideOpen ? "open" : ""} />
            </button>
            {guideOpen && (
              <div className="wa-accordion-body wa-guide">
                <a
                  className="button secondary wa-guide-link"
                  href="https://developers.facebook.com/apps/"
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink size={16} /> {t("clients.whatsappCloud.guideOpenMeta")}
                </a>

                <div className="wa-guide-block">
                  <h3>{t("clients.whatsappCloud.guideChecklistTitle")}</h3>
                  <ul className="wa-guide-checklist">
                    {setupChecks.map((item) => (
                      <li key={item.id} className={item.done ? "done" : ""}>
                        {item.done ? <CheckCircle2 size={16} /> : <Circle size={16} />}
                        <span>{item.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="wa-nested-accordion">
                  <button
                    type="button"
                    className="wa-nested-trigger"
                    onClick={() => setGuideByoOpen((v) => !v)}
                    aria-expanded={guideByoOpen}
                  >
                    <strong>{t("clients.whatsappCloud.guideByoTitle")}</strong>
                    <ChevronDown size={16} className={guideByoOpen ? "open" : ""} />
                  </button>
                  {guideByoOpen && (
                    <div className="wa-nested-body">
                      <p>{t("clients.whatsappCloud.guideByoIntro")}</p>
                      <div className="wa-guide-block">
                        <h3>{t("clients.whatsappCloud.guideByoNeedTitle")}</h3>
                        <ul className="wa-guide-checklist">
                          <li><Circle size={16} /><span>{t("clients.whatsappCloud.guideByoNeedPhone")}</span></li>
                          <li><Circle size={16} /><span>{t("clients.whatsappCloud.guideByoNeedWaba")}</span></li>
                          <li><Circle size={16} /><span>{t("clients.whatsappCloud.guideByoNeedToken")}</span></li>
                          <li><Circle size={16} /><span>{t("clients.whatsappCloud.guideByoNeedSecret")}</span></li>
                        </ul>
                      </div>
                      <div className="wa-guide-block">
                        <h3>{t("clients.whatsappCloud.guideByoWhereTitle")}</h3>
                        <p>{t("clients.whatsappCloud.guideByoWhereCopy")}</p>
                        <img
                          className="wa-guide-diagram"
                          src="/whatsapp-meta-guide/api-setup-ids.svg"
                          alt={t("clients.whatsappCloud.guideByoImageAlt")}
                        />
                        <p className="wa-guide-note">
                          <a href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started/" target="_blank" rel="noreferrer">
                            {t("clients.whatsappCloud.guideDocsHint")}
                          </a>
                        </p>
                      </div>
                      <ol className="wa-guide-steps">
                        <li>{t("clients.whatsappCloud.guideByo1")}</li>
                        <li>{t("clients.whatsappCloud.guideByo2")}</li>
                        <li>{t("clients.whatsappCloud.guideByo3")}</li>
                        <li>{t("clients.whatsappCloud.guideByo4")}</li>
                        <li>{t("clients.whatsappCloud.guideByo5")}</li>
                        <li>
                          {t("clients.whatsappCloud.guideByo6")}{" "}
                          <button type="button" className="text-button" onClick={() => setAdvancedOpen(true)}>
                            {t("clients.whatsappCloud.advancedTitle")}
                          </button>
                        </li>
                        <li>{t("clients.whatsappCloud.guideByo7")}</li>
                      </ol>
                      <p className="wa-guide-note">{t("clients.whatsappCloud.guideWebhookNote")}</p>
                    </div>
                  )}
                </div>

                <div className="wa-nested-accordion">
                  <button
                    type="button"
                    className="wa-nested-trigger"
                    onClick={() => setGuideManagedOpen((v) => !v)}
                    aria-expanded={guideManagedOpen}
                  >
                    <strong>{t("clients.whatsappCloud.guideManagedTitle")}</strong>
                    <ChevronDown size={16} className={guideManagedOpen ? "open" : ""} />
                  </button>
                  {guideManagedOpen && (
                    <div className="wa-nested-body">
                      <p>{t("clients.whatsappCloud.guideManagedIntro")}</p>
                      {!options?.managed_available && (
                        <Alert type="info">{t("clients.whatsappCloud.managedUnavailable")}</Alert>
                      )}
                      <ol className="wa-guide-steps">
                        <li>{t("clients.whatsappCloud.guideManaged1")}</li>
                        <li>{t("clients.whatsappCloud.guideManaged2")}</li>
                        <li>{t("clients.whatsappCloud.guideManaged3")}</li>
                        <li>{t("clients.whatsappCloud.guideManaged4", { url: oauthRedirectExample })}</li>
                        <li>{t("clients.whatsappCloud.guideManaged5")}</li>
                        <li>{t("clients.whatsappCloud.guideManaged6")}</li>
                      </ol>
                    </div>
                  )}
                </div>

                <div className="wa-nested-accordion">
                  <button
                    type="button"
                    className="wa-nested-trigger"
                    onClick={() => setGuideCompareOpen((v) => !v)}
                    aria-expanded={guideCompareOpen}
                  >
                    <strong>{t("clients.whatsappCloud.guideCompareTitle")}</strong>
                    <ChevronDown size={16} className={guideCompareOpen ? "open" : ""} />
                  </button>
                  {guideCompareOpen && (
                    <div className="wa-nested-body">
                      <p>{t("clients.whatsappCloud.guideCompareIntro")}</p>
                      <ul className="wa-guide-steps">
                        <li>{t("clients.whatsappCloud.guideCompareQr")}</li>
                        <li>{t("clients.whatsappCloud.guideCompareCloud")}</li>
                      </ul>
                    </div>
                  )}
                </div>

                <div className="wa-nested-accordion">
                  <button
                    type="button"
                    className="wa-nested-trigger"
                    onClick={() => setGuideMcpOpen((v) => !v)}
                    aria-expanded={guideMcpOpen}
                  >
                    <strong>{t("clients.whatsappCloud.guideMcpTitle")}</strong>
                    <ChevronDown size={16} className={guideMcpOpen ? "open" : ""} />
                  </button>
                  {guideMcpOpen && (
                    <div className="wa-nested-body">
                      <p>{t("clients.whatsappCloud.guideMcpIntro")}</p>
                      <a
                        className="button secondary wa-guide-link"
                        href="https://developers.facebook.com/documentation/mcp/devtools-mcp"
                        target="_blank"
                        rel="noreferrer"
                      >
                        <ExternalLink size={16} /> {t("clients.whatsappCloud.guideMcpLink")}
                      </a>
                      <p className="wa-guide-note">{t("clients.whatsappCloud.guideDocsRepo")}</p>
                    </div>
                  )}
                </div>

                <p className="wa-guide-note">{t("clients.whatsappCloud.guideDocsRepo")}</p>
              </div>
            )}
          </section>

          <section className="wa-panel">
            <div className="wa-panel-head"><span><Bot size={19} /></span><div><h2>{t("clients.whatsapp.assignedAgent")}</h2><p>{t("clients.whatsappCloud.agentAfterConnect")}</p></div></div>
            <div className="wa-agent-row">
              <label>
                {t("clients.whatsapp.agentToRespond")}
                <select value={agentId} onChange={(event) => setAgentId(event.target.value)} disabled={busy}>
                  <option value="">{t("clients.whatsapp.selectAgent")}</option>
                  {client.agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name}{agent.is_active ? "" : t("clients.whatsapp.inactiveSuffix")}</option>
                  ))}
                </select>
              </label>
              <button type="button" className="button secondary" onClick={saveAgentOnly} disabled={!agentId || busy}>{t("clients.whatsappCloud.saveAgent")}</button>
            </div>
            {!client.agents.length && <Alert>{t("clients.whatsapp.needsAgent")}</Alert>}
            {offerAgentHelp && (
              <div className="wa-agent-help">
                <p>{t("clients.whatsappCloud.agentHelpPrompt", { name: client.agents.find((a) => a.id === agentId)?.name || "" })}</p>
                <div className="wa-actions">
                  <Link className="button primary" href={`/agents/${agentId}`}>{t("clients.whatsappCloud.configureAgent")}</Link>
                  <button type="button" className="button ghost" onClick={() => setOfferAgentHelp(false)}>{t("clients.whatsappCloud.agentHelpLater")}</button>
                </div>
              </div>
            )}
          </section>

          <section className="wa-panel wa-accordion-panel">
            <button type="button" className="wa-accordion-trigger" onClick={() => setAdvancedOpen((v) => !v)} aria-expanded={advancedOpen}>
              <span><KeyRound size={19} /></span>
              <div><h2>{t("clients.whatsappCloud.advancedTitle")}</h2><p>{t("clients.whatsappCloud.advancedCopy")}</p></div>
              <ChevronDown size={18} className={advancedOpen ? "open" : ""} />
            </button>
            {advancedOpen && (
              <form className="wa-accordion-body wa-cloud-form" onSubmit={saveAdvanced}>
                <label>{t("clients.whatsappCloud.phoneNumberIdLabel")}<input value={phoneNumberId} onChange={(event) => setPhoneNumberId(event.target.value)} disabled={busy} /></label>
                <label>{t("clients.whatsappCloud.wabaIdLabel")}<input value={wabaId} onChange={(event) => setWabaId(event.target.value)} disabled={busy} /></label>
                <label>
                  {t("clients.whatsappCloud.accessTokenLabel")}
                  <input
                    type={showSecrets ? "text" : "password"}
                    value={accessToken}
                    onChange={(event) => setAccessToken(event.target.value)}
                    placeholder={channel?.has_access_token ? t("clients.whatsappCloud.secretSavedPlaceholder") : ""}
                    disabled={busy}
                  />
                </label>
                <label>
                  {t("clients.whatsappCloud.appSecretLabel")}
                  <input
                    type={showSecrets ? "text" : "password"}
                    value={appSecret}
                    onChange={(event) => setAppSecret(event.target.value)}
                    placeholder={channel?.has_app_secret ? t("clients.whatsappCloud.secretSavedPlaceholder") : ""}
                    disabled={busy}
                  />
                </label>
                <label className="switch-row">
                  <span>{t("clients.whatsappCloud.showSecrets")}</span>
                  <input type="checkbox" checked={showSecrets} onChange={(event) => setShowSecrets(event.target.checked)} />
                </label>
                {channel?.last_error && <Alert>{channel.error_message || channel.last_error}</Alert>}
                <div className="wa-actions">
                  <button className="button primary" disabled={!agentId || busy}>
                    {busy ? <LoaderCircle className="spin" size={17} /> : <Plug size={17} />} {t("clients.whatsappCloud.saveAndVerify")}
                  </button>
                </div>
              </form>
            )}
          </section>

          {channel && (
            <section className="wa-panel">
              <div className="wa-panel-head"><span><Webhook size={19} /></span><div><h2>{t("clients.whatsappCloud.webhookTitle")}</h2><p>{t("clients.whatsappCloud.webhookCopy")}</p></div></div>
              <CopyField label={t("clients.whatsappCloud.webhookUrlLabel")} value={channel.webhook_url} />
              <CopyField label={t("clients.whatsappCloud.verifyTokenLabel")} value={channel.webhook_verify_token} />
              <ol className="wa-webhook-steps">
                <li>{t("clients.whatsappCloud.webhookStep1")}</li>
                <li>{t("clients.whatsappCloud.webhookStep2")}</li>
                <li>{t("clients.whatsappCloud.webhookStep3")}</li>
              </ol>
            </section>
          )}
        </main>
        <aside className="wa-side">
          <ShieldCheck size={22} />
          <h3>{t("clients.whatsapp.separationTitle")}</h3>
          <p>{t("clients.whatsapp.separationCopy")}<strong>{client.name}</strong>.</p>
          <hr />
          <h3>{t("clients.whatsapp.humanControlTitle")}</h3>
          <p>{t("clients.whatsapp.humanControlCopy")}</p>
        </aside>
      </div>
      <ChannelConnectConsentModal
        open={consentOpen}
        channel="whatsapp_cloud"
        clientId={id}
        providerTermsUrl="https://developers.facebook.com/terms/"
        onClose={() => setConsentOpen(false)}
        onConfirmed={() => {
          setConsentOpen(false);
          void connectWithMeta();
        }}
      />
    </div>
  );
}

export default function WhatsAppCloudChannelPage() {
  return (
    <Suspense fallback={<div className="page-loading"><LoaderCircle className="spin" /></div>}>
      <WhatsAppCloudChannelPageInner />
    </Suspense>
  );
}

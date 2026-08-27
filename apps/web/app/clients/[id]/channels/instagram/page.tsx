"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft, BookOpen, CheckCircle2, ChevronDown, Circle, CircleAlert, ExternalLink,
  Instagram, LoaderCircle, Plus, Power, RefreshCw, Sparkles,
} from "lucide-react";
import { Alert } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useT, type I18nKey } from "@/lib/i18n";
import type {
  Client,
  InstagramChannel,
  InstagramContentItem,
  InstagramDashboardStats,
  InstagramHealth,
  InstagramOAuthOptions,
  InstagramOAuthSession,
  InstagramPublication,
  InstagramPublishingLimit,
} from "@/types";

function StatusChip({ status }: { status: string }) {
  const t = useT();
  const normalized = status === "connected" ? "connected" : status === "error" ? "error" : "disconnected";
  const map: Record<string, { label: I18nKey; icon: typeof CheckCircle2 }> = {
    connected: { label: "instagram.statusConnected", icon: CheckCircle2 },
    error: { label: "instagram.statusError", icon: CircleAlert },
    disconnected: { label: "instagram.statusDisconnected", icon: RefreshCw },
  };
  const item = map[normalized];
  const Icon = item.icon;
  return (
    <div className={`wa-state ${normalized}`}>
      <Icon size={17} /> {t(item.label)}
    </div>
  );
}

function healthLabel(ui: string): I18nKey {
  if (ui === "ok") return "instagram.healthOk";
  if (ui === "partial") return "instagram.healthPartial";
  if (ui === "error") return "instagram.healthError";
  return "instagram.healthDisconnected";
}

function InstagramChannelPageInner() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const oauthHandled = useRef(false);

  const [client, setClient] = useState<Client | null>(null);
  const [channel, setChannel] = useState<InstagramChannel | null>(null);
  const [options, setOptions] = useState<InstagramOAuthOptions | null>(null);
  const [health, setHealth] = useState<InstagramHealth | null>(null);
  const [limit, setLimit] = useState<InstagramPublishingLimit | null>(null);
  const [stats, setStats] = useState<InstagramDashboardStats | null>(null);
  const [content, setContent] = useState<InstagramContentItem[]>([]);
  const [publications, setPublications] = useState<InstagramPublication[]>([]);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(true);
  const [guideByoOpen, setGuideByoOpen] = useState(true);
  const [guideOauthOpen, setGuideOauthOpen] = useState(false);
  const [guideMockOpen, setGuideMockOpen] = useState(false);
  const [guideTroubleOpen, setGuideTroubleOpen] = useState(false);
  const [igUserId, setIgUserId] = useState("");
  const [pageId, setPageId] = useState("");
  const [username, setUsername] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [errorDetail, setErrorDetail] = useState("");
  const [showTechnical, setShowTechnical] = useState(false);
  const [info, setInfo] = useState("");

  const applyChannel = useCallback((current: InstagramChannel) => {
    setChannel(current);
    setIgUserId(current.instagram_user_id || "");
    setPageId(current.page_id || "");
    setUsername(current.username || "");
  }, []);

  const refreshConnectedData = useCallback(async () => {
    try {
      const [h, lim, dash, items, pubs] = await Promise.all([
        api<InstagramHealth>(`/instagram/channels/${id}/health`).catch(() => null),
        api<InstagramPublishingLimit>(`/instagram/channels/${id}/publishing-limit`).catch(() => null),
        api<InstagramDashboardStats>(`/instagram/channels/${id}/dashboard`).catch(() => null),
        api<InstagramContentItem[]>(`/instagram/channels/${id}/content`).catch(() => []),
        api<InstagramPublication[]>(`/instagram/channels/${id}/publications`).catch(() => []),
      ]);
      setHealth(h);
      setLimit(lim);
      setStats(dash);
      setContent(items);
      setPublications(pubs);
    } catch {
      /* ignore secondary load failures */
    }
  }, [id]);

  useEffect(() => {
    (async () => {
      try {
        const [c, ch, opts] = await Promise.all([
          api<Client>(`/clients/${id}`),
          api<InstagramChannel>(`/instagram/channels/${id}`),
          api<InstagramOAuthOptions>("/instagram/oauth/options").catch(() => null),
        ]);
        setClient(c);
        applyChannel(ch);
        setOptions(opts);
        const isConnected = ch.status === "connected";
        setGuideOpen(!isConnected);
        setGuideByoOpen(!isConnected);
        if (isConnected) await refreshConnectedData();
      } catch (err) {
        setError(messageFrom(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [id, applyChannel, refreshConnectedData]);

  function openGuide() {
    setGuideOpen(true);
    setGuideByoOpen(true);
    requestAnimationFrame(() => {
      document.getElementById("ig-connect-guide")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function openAdvancedFromGuide() {
    setAdvancedOpen(true);
    requestAnimationFrame(() => {
      document.getElementById("ig-advanced-setup")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function isExternalConfigBlock(message: string) {
    return message.includes("BLOCKED_BY_EXTERNAL_CONFIGURATION");
  }

  function showBlockedOauthNotice(detail?: string | null) {
    setError(t("instagram.oauthBlocked"));
    setErrorDetail(detail || options?.blocked_reason || "");
    setShowTechnical(false);
    openGuide();
  }

  useEffect(() => {
    const code = search.get("oauth_code");
    const state = search.get("oauth_state");
    if (!code || !state || oauthHandled.current) return;
    oauthHandled.current = true;
    (async () => {
      setBusy(true);
      setError("");
      setInfo(t("instagram.oauthCompleting"));
      try {
        const updated = await api<InstagramChannel>(`/instagram/channels/${id}/oauth/complete`, {
          method: "POST",
          body: JSON.stringify({ code, state }),
        });
        applyChannel(updated);
        await refreshConnectedData();
        window.history.replaceState({}, "", `/clients/${id}/channels/instagram`);
        setInfo("");
      } catch (err) {
        setError(messageFrom(err));
        setInfo("");
      } finally {
        setBusy(false);
      }
    })();
  }, [search, id, applyChannel, refreshConnectedData, t]);

  async function connectWithMeta(useMock = false) {
    setBusy(true);
    setError("");
    setErrorDetail("");
    setInfo("");
    try {
      if (!useMock && !options?.oauth_available && !options?.mock_mode) {
        showBlockedOauthNotice(options?.blocked_reason);
        return;
      }
      const session = await api<InstagramOAuthSession>(`/instagram/channels/${id}/oauth/session`, {
        method: "POST",
      });
      if (useMock || session.mock_mode || options?.mock_mode) {
        const updated = await api<InstagramChannel>(`/instagram/channels/${id}/oauth/complete`, {
          method: "POST",
          body: JSON.stringify({ state: session.state, use_mock: true }),
        });
        applyChannel(updated);
        await refreshConnectedData();
        return;
      }
      if (!session.dialog_url) {
        showBlockedOauthNotice(options?.blocked_reason);
        return;
      }
      window.location.assign(session.dialog_url);
    } catch (err) {
      const msg = messageFrom(err);
      if (isExternalConfigBlock(msg)) {
        showBlockedOauthNotice(msg);
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  async function saveAdvanced(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setErrorDetail("");
    try {
      const payload: Record<string, string | null> = {
        instagram_user_id: igUserId.trim(),
        page_id: pageId.trim() || null,
        username: username.trim() || null,
      };
      if (accessToken.trim()) payload.access_token = accessToken.trim();
      const updated = await api<InstagramChannel>(`/instagram/channels/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      applyChannel(updated);
      setAccessToken("");
      if (updated.status === "connected") await refreshConnectedData();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    if (!window.confirm(t("instagram.confirmDisconnect"))) return;
    setBusy(true);
    setError("");
    setErrorDetail("");
    try {
      const updated = await api<InstagramChannel>(`/instagram/channels/${id}/disconnect`, { method: "POST" });
      applyChannel(updated);
      setHealth(null);
      setLimit(null);
      setStats(null);
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading || !client) {
    return (
      <div className="page-loading">
        <LoaderCircle className="spin" /> {t("instagram.loading")}
      </div>
    );
  }

  const connected = channel?.status === "connected";
  const uiStatus = health?.ui_status || (connected ? "ok" : "disconnected");
  const setupChecks = [
    { id: "pro", label: t("instagram.guideCheckPro"), done: connected },
    { id: "page", label: t("instagram.guideCheckPage"), done: Boolean(channel?.page_id) },
    { id: "token", label: t("instagram.guideCheckToken"), done: Boolean(channel?.access_token_configured) },
    { id: "igid", label: t("instagram.guideCheckIgId"), done: Boolean(channel?.instagram_user_id) },
    { id: "saved", label: t("instagram.guideCheckSaved"), done: connected },
  ];

  return (
    <div className="page wa-page ig-page">
      <Link href={`/clients/${client.id}`} className="back-link">
        <ArrowLeft size={17} /> {t("instagram.back", { name: client.name })}
      </Link>
      <header className="wa-header">
        <div className="wa-mark ig-mark"><Instagram size={26} /></div>
        <div>
          <span>{t("instagram.channelOf", { name: client.name })}</span>
          <h1>{t("instagram.title")}</h1>
          <p>{t("instagram.heroCopy")}</p>
        </div>
        {channel && <StatusChip status={channel.status} />}
      </header>
      {error && (
        <Alert type={errorDetail ? "info" : "error"}>
          <div>
            {error}
            {errorDetail && (
              <>
                <button type="button" className="text-button" onClick={() => setShowTechnical((v) => !v)}>
                  {t("instagram.viewTechnical")}
                </button>
                {showTechnical && <pre className="wa-tech-error">{errorDetail}</pre>}
              </>
            )}
          </div>
        </Alert>
      )}
      {info && <Alert type="info">{info}</Alert>}

      <div className="wa-layout">
        <main>
          {connected ? (
            <>
              <section className="wa-panel wa-status-card">
                <div className="wa-panel-head">
                  <span><Instagram size={19} /></span>
                  <div>
                    <h2>{t("instagram.connectedTitle")}</h2>
                    <p className="wa-live-dot">
                      ● @{channel?.username || channel?.instagram_user_id || "—"}
                      {(health?.mock_mode || channel?.connection_mode === "mock") && (
                        <> · {t("instagram.mockModeBadge")}</>
                      )}
                    </p>
                  </div>
                </div>
                <div className="wa-status-grid">
                  <div>
                    <small>{t("instagram.username")}</small>
                    <strong>@{channel?.username || "—"}</strong>
                  </div>
                  <div>
                    <small>{t("instagram.displayName")}</small>
                    <strong>{channel?.display_name || "—"}</strong>
                  </div>
                  <div>
                    <small>{t("instagram.healthTitle")}</small>
                    <strong>{t(healthLabel(uiStatus))}</strong>
                  </div>
                  <div>
                    <small>{t("instagram.igUserId")}</small>
                    <strong>{channel?.instagram_user_id || "—"}</strong>
                  </div>
                </div>
                {channel?.last_error && (
                  <Alert type="info">
                    {t("instagram.lastError")}: {channel.last_error}
                  </Alert>
                )}
                <div className="wa-actions">
                  <Link className="button primary" href={`/clients/${id}/channels/instagram/compose`}>
                    <Plus size={17} /> {t("instagram.newPost")}
                  </Link>
                  <button className="button danger" type="button" onClick={disconnect} disabled={busy}>
                    <Power size={17} /> {t("instagram.disconnect")}
                  </button>
                </div>
              </section>

              {limit?.available && (
                <section className="wa-panel">
                  <div className="wa-panel-head">
                    <span><Sparkles size={19} /></span>
                    <div>
                      <h2>{t("instagram.limitTitle")}</h2>
                      <p>
                        {t("instagram.limitUsage", {
                          used: String(limit.quota_usage ?? 0),
                          total: String(limit.quota_total ?? "—"),
                        })}
                        {limit.quota_duration
                          ? ` · ${t("instagram.limitDuration", { hours: String(Math.round(limit.quota_duration / 3600)) })}`
                          : ""}
                      </p>
                    </div>
                  </div>
                </section>
              )}

              {stats && (
                <section className="wa-panel">
                  <div className="wa-panel-head">
                    <span><CheckCircle2 size={19} /></span>
                    <div>
                      <h2>{t("instagram.statsTitle")}</h2>
                    </div>
                  </div>
                  <div className="wa-status-grid ig-stats-grid">
                    <div><small>{t("instagram.drafts")}</small><strong>{stats.drafts}</strong></div>
                    <div><small>{t("instagram.scheduled")}</small><strong>{stats.scheduled}</strong></div>
                    <div><small>{t("instagram.published")}</small><strong>{stats.published_month}</strong></div>
                    <div><small>{t("instagram.failed")}</small><strong>{stats.failed}</strong></div>
                  </div>
                </section>
              )}

              <section className="wa-panel">
                <div className="wa-panel-head">
                  <span><Plus size={19} /></span>
                  <div>
                    <h2>{t("instagram.recentContent")}</h2>
                  </div>
                </div>
                {content.length === 0 ? (
                  <p className="ig-muted">{t("instagram.emptyContent")}</p>
                ) : (
                  <ul className="ig-list">
                    {content.slice(0, 8).map((item) => (
                      <li key={item.id}>
                        <div>
                          <strong>{item.title || item.content_type}</strong>
                          <small>{item.status} · {item.content_type}</small>
                        </div>
                        {(item.status === "DRAFT" || item.status === "READY" || item.status === "FAILED") && (
                          <Link
                            className="button secondary"
                            href={`/clients/${id}/channels/instagram/compose?content=${item.id}`}
                          >
                            {t("instagram.editDraft")}
                          </Link>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="wa-panel">
                <div className="wa-panel-head">
                  <span><CheckCircle2 size={19} /></span>
                  <div>
                    <h2>{t("instagram.recentPublications")}</h2>
                  </div>
                </div>
                {publications.length === 0 ? (
                  <p className="ig-muted">{t("instagram.emptyPublications")}</p>
                ) : (
                  <ul className="ig-list">
                    {publications.slice(0, 8).map((pub) => (
                      <li key={pub.id}>
                        <div>
                          <strong>{pub.status}</strong>
                          <small>
                            {pub.published_at
                              ? new Date(pub.published_at).toLocaleString()
                              : pub.scheduled_at
                                ? new Date(pub.scheduled_at).toLocaleString()
                                : pub.error_message || "—"}
                          </small>
                        </div>
                        {pub.provider_permalink && (
                          <a className="button secondary" href={pub.provider_permalink} target="_blank" rel="noreferrer">
                            {t("instagram.openPermalink")}
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </>
          ) : (
            <section className="wa-panel">
              <div className="wa-panel-head">
                <span><Instagram size={19} /></span>
                <div>
                  <h2>{t("instagram.connectTitle")}</h2>
                  <p>{t("instagram.connectCopy")}</p>
                </div>
              </div>
              {channel?.status === "error" && (
                <Alert>
                  {channel.last_error || t("instagram.statusError")}
                  <div className="wa-actions" style={{ marginTop: 12 }}>
                    <button className="button primary" type="button" onClick={() => connectWithMeta(false)} disabled={busy}>
                      {busy ? <LoaderCircle className="spin" size={17} /> : <RefreshCw size={17} />} {t("instagram.reconnectMeta")}
                    </button>
                    <button className="button secondary" type="button" onClick={openGuide}>
                      <BookOpen size={17} /> {t("instagram.openGuide")}
                    </button>
                  </div>
                </Alert>
              )}
              {!options?.oauth_available && !options?.mock_mode ? (
                <Alert type="info">
                  <div>
                    <strong>{t("instagram.oauthUnavailableTitle")}</strong>
                    <p style={{ margin: "8px 0 0" }}>{t("instagram.oauthUnavailableCopy")}</p>
                    {options?.blocked_reason && (
                      <>
                        <button type="button" className="text-button" onClick={() => setShowTechnical((v) => !v)}>
                          {t("instagram.viewTechnical")}
                        </button>
                        {showTechnical && <pre className="wa-tech-error">{options.blocked_reason}</pre>}
                      </>
                    )}
                  </div>
                </Alert>
              ) : (
                <p className="ig-muted" style={{ marginBottom: 12 }}>{t("instagram.oauthAvailableHint")}</p>
              )}
              <div className="wa-actions">
                <button className="button primary" type="button" onClick={() => connectWithMeta(false)} disabled={busy}>
                  {busy ? <LoaderCircle className="spin" size={17} /> : <Instagram size={17} />} {t("instagram.connectMeta")}
                </button>
                {options?.mock_mode && (
                  <button className="button secondary" type="button" onClick={() => connectWithMeta(true)} disabled={busy}>
                    {t("instagram.connectMock")}
                  </button>
                )}
                <button className="button secondary" type="button" onClick={openGuide}>
                  <BookOpen size={17} /> {t("instagram.openGuide")}
                </button>
                <button className="button secondary" type="button" onClick={openAdvancedFromGuide}>
                  {t("instagram.openAdvanced")}
                </button>
              </div>
              <div className="wa-benefits">
                <h3>{t("instagram.benefitsTitle")}</h3>
                <ul>
                  <li>✓ {t("instagram.benefit1")}</li>
                  <li>✓ {t("instagram.benefit2")}</li>
                  <li>✓ {t("instagram.benefit3")}</li>
                  <li>✓ {t("instagram.benefit4")}</li>
                </ul>
              </div>
            </section>
          )}

          <section className="wa-panel wa-accordion-panel" id="ig-connect-guide">
            <button type="button" className="wa-accordion-trigger" onClick={() => setGuideOpen((v) => !v)} aria-expanded={guideOpen}>
              <span><BookOpen size={19} /></span>
              <div>
                <h2>{t("instagram.guideTitle")}</h2>
                <p>{t("instagram.guideCopy")}</p>
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
                  <ExternalLink size={16} /> {t("instagram.guideOpenMeta")}
                </a>

                <div className="wa-guide-block">
                  <h3>{t("instagram.guideChecklistTitle")}</h3>
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
                    <strong>{t("instagram.guideByoTitle")}</strong>
                    <ChevronDown size={16} className={guideByoOpen ? "open" : ""} />
                  </button>
                  {guideByoOpen && (
                    <div className="wa-nested-body">
                      <p>{t("instagram.guideByoIntro")}</p>
                      <div className="wa-guide-block">
                        <h3>{t("instagram.guideByoNeedTitle")}</h3>
                        <ul className="wa-guide-checklist">
                          <li><Circle size={16} /><span>{t("instagram.guideByoNeedIg")}</span></li>
                          <li><Circle size={16} /><span>{t("instagram.guideByoNeedPage")}</span></li>
                          <li><Circle size={16} /><span>{t("instagram.guideByoNeedUser")}</span></li>
                          <li><Circle size={16} /><span>{t("instagram.guideByoNeedToken")}</span></li>
                        </ul>
                      </div>
                      <div className="wa-guide-block">
                        <h3>{t("instagram.guideByoWhereTitle")}</h3>
                        <p>{t("instagram.guideByoWhereCopy")}</p>
                        <p className="wa-guide-note">
                          <a href="https://developers.facebook.com/docs/instagram-platform/content-publishing" target="_blank" rel="noreferrer">
                            {t("instagram.guideDocsHint")}
                          </a>
                        </p>
                      </div>
                      <ol className="wa-guide-steps">
                        <li>{t("instagram.guideByo1")}</li>
                        <li>{t("instagram.guideByo2")}</li>
                        <li>{t("instagram.guideByo3")}</li>
                        <li>{t("instagram.guideByo4")}</li>
                        <li>{t("instagram.guideByo5")}</li>
                        <li>
                          {t("instagram.guideByo6")}{" "}
                          <button type="button" className="text-button" onClick={openAdvancedFromGuide}>
                            {t("instagram.advancedTitle")}
                          </button>
                        </li>
                        <li>{t("instagram.guideByo7")}</li>
                      </ol>
                    </div>
                  )}
                </div>

                <div className="wa-nested-accordion">
                  <button
                    type="button"
                    className="wa-nested-trigger"
                    onClick={() => setGuideOauthOpen((v) => !v)}
                    aria-expanded={guideOauthOpen}
                  >
                    <strong>{t("instagram.guideOauthTitle")}</strong>
                    <ChevronDown size={16} className={guideOauthOpen ? "open" : ""} />
                  </button>
                  {guideOauthOpen && (
                    <div className="wa-nested-body">
                      <p>{t("instagram.guideOauthIntro")}</p>
                      {!options?.oauth_available && !options?.mock_mode ? (
                        <Alert type="info">{t("instagram.guideOauthUnavailable")}</Alert>
                      ) : (
                        <ol className="wa-guide-steps">
                          <li>{t("instagram.guideOauth1")}</li>
                          <li>{t("instagram.guideOauth2")}</li>
                          <li>{t("instagram.guideOauth3")}</li>
                          <li>{t("instagram.guideOauth4")}</li>
                        </ol>
                      )}
                    </div>
                  )}
                </div>

                {options?.mock_mode && (
                  <div className="wa-nested-accordion">
                    <button
                      type="button"
                      className="wa-nested-trigger"
                      onClick={() => setGuideMockOpen((v) => !v)}
                      aria-expanded={guideMockOpen}
                    >
                      <strong>{t("instagram.guideMockTitle")}</strong>
                      <ChevronDown size={16} className={guideMockOpen ? "open" : ""} />
                    </button>
                    {guideMockOpen && (
                      <div className="wa-nested-body">
                        <p>{t("instagram.guideMockIntro")}</p>
                      </div>
                    )}
                  </div>
                )}

                <div className="wa-nested-accordion">
                  <button
                    type="button"
                    className="wa-nested-trigger"
                    onClick={() => setGuideTroubleOpen((v) => !v)}
                    aria-expanded={guideTroubleOpen}
                  >
                    <strong>{t("instagram.guideTroubleshootTitle")}</strong>
                    <ChevronDown size={16} className={guideTroubleOpen ? "open" : ""} />
                  </button>
                  {guideTroubleOpen && (
                    <div className="wa-nested-body">
                      <ol className="wa-guide-steps">
                        <li>{t("instagram.guideTroubleshoot1")}</li>
                        <li>{t("instagram.guideTroubleshoot2")}</li>
                        <li>{t("instagram.guideTroubleshoot3")}</li>
                        <li>{t("instagram.guideTroubleshoot4")}</li>
                      </ol>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>

          <section className="wa-panel wa-accordion-panel" id="ig-advanced-setup">
            <button
              type="button"
              className="wa-accordion-trigger"
              onClick={() => setAdvancedOpen((v) => !v)}
              aria-expanded={advancedOpen}
            >
              <span><Sparkles size={19} /></span>
              <div>
                <h2>{t("instagram.advancedTitle")}</h2>
                <p>{t("instagram.advancedCopy")}</p>
              </div>
              <ChevronDown size={18} className={advancedOpen ? "open" : ""} />
            </button>
            {advancedOpen && (
              <form className="wa-accordion-body wa-cloud-form" onSubmit={saveAdvanced}>
                <label>
                  {t("instagram.fieldIgUserId")}
                  <input value={igUserId} onChange={(e) => setIgUserId(e.target.value)} required />
                </label>
                <label>
                  {t("instagram.fieldPageId")}
                  <input value={pageId} onChange={(e) => setPageId(e.target.value)} />
                </label>
                <label>
                  {t("instagram.fieldUsername")}
                  <input value={username} onChange={(e) => setUsername(e.target.value)} />
                </label>
                <label>
                  {t("instagram.fieldAccessToken")}
                  <input
                    type="password"
                    value={accessToken}
                    onChange={(e) => setAccessToken(e.target.value)}
                    placeholder={channel?.access_token_configured ? t("instagram.fieldAccessTokenKeep") : undefined}
                    autoComplete="off"
                  />
                </label>
                <div className="wa-actions" style={{ gridColumn: "1 / -1" }}>
                  <button className="button primary" type="submit" disabled={busy}>
                    {busy ? <LoaderCircle className="spin" size={17} /> : null} {t("instagram.saveAdvanced")}
                  </button>
                </div>
              </form>
            )}
          </section>
        </main>

        <aside className="wa-side">
          <Instagram size={22} />
          <h3>{t("instagram.healthTitle")}</h3>
          {connected && health ? (
            <>
              <p><strong>{t("instagram.accountOk")}:</strong> {health.account_ok ? t("instagram.yes") : t("instagram.no")}</p>
              <p><strong>{t("instagram.tokenOk")}:</strong> {health.token_ok ? t("instagram.yes") : t("instagram.no")}</p>
              <p><strong>{t("instagram.publishOk")}:</strong> {health.publish_permission_ok ? t("instagram.yes") : t("instagram.no")}</p>
              <p><strong>{t("instagram.apiOk")}:</strong> {health.api_ok ? t("instagram.yes") : t("instagram.no")}</p>
              {limit && !limit.available && <p>{t("instagram.limitUnavailable")}</p>}
            </>
          ) : (
            <>
              <p>{t("instagram.connectCopy")}</p>
              <button type="button" className="button secondary" style={{ marginTop: 12 }} onClick={openGuide}>
                <BookOpen size={16} /> {t("instagram.openGuide")}
              </button>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}

export default function InstagramChannelPage() {
  return (
    <Suspense fallback={<div className="page-loading"><LoaderCircle className="spin" /></div>}>
      <InstagramChannelPageInner />
    </Suspense>
  );
}

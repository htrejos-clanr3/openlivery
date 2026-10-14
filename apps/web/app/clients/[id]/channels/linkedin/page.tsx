"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, BookOpen, CheckCircle2, ChevronDown, Copy, ExternalLink, Linkedin, LoaderCircle, LogOut, Send, Sparkles } from "lucide-react";
import { ChannelConnectConsentModal, buildChannelConsent } from "@/components/channel-connect-consent-modal";
import { SwitchRow } from "@/components/switch-row";
import { Alert, PageHead } from "@/components/ui";
import { useToast } from "@/components/toast";
import { api, messageFrom } from "@/lib/api";
import { useLanguage, useT } from "@/lib/i18n";
import type {
  LinkedInChannel,
  LinkedInDraft,
  LinkedInOAuthOptions,
  LinkedInOAuthSession,
  LinkedInPostResult,
  LinkedInProfileResult,
  LinkedInPublication,
} from "@/types";

type Tab = "post" | "profile" | "drafts";

export default function LinkedInDeskPage() {
  const t = useT();
  const { lang } = useLanguage();
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const oauthHandled = useRef(false);
  const [channel, setChannel] = useState<LinkedInChannel | null>(null);
  const [options, setOptions] = useState<LinkedInOAuthOptions | null>(null);
  const [guideOpen, setGuideOpen] = useState(true);
  const [advancedOpen, setAdvancedOpen] = useState(true);
  const [tab, setTab] = useState<Tab>("post");
  const [busy, setBusy] = useState(false);
  const [idea, setIdea] = useState("");
  const [post, setPost] = useState<LinkedInPostResult | null>(null);
  const [pasted, setPasted] = useState("");
  const [profile, setProfile] = useState<LinkedInProfileResult | null>(null);
  const [drafts, setDrafts] = useState<LinkedInDraft[]>([]);
  const [raw, setRaw] = useState("");
  const [cleaned, setCleaned] = useState("");
  const [publishApproved, setPublishApproved] = useState(false);
  const [publication, setPublication] = useState<LinkedInPublication | null>(null);
  const [consentOpen, setConsentOpen] = useState(false);

  const load = useCallback(async () => {
    const [row, oauth, rows] = await Promise.all([
      api<LinkedInChannel>(`/linkedin/channels/${id}`),
      api<LinkedInOAuthOptions>("/linkedin/oauth/options"),
      api<LinkedInDraft[]>(`/linkedin/channels/${id}/drafts`).catch(() => []),
    ]);
    setChannel(row);
    setOptions(oauth);
    setDrafts(rows);
  }, [id]);

  useEffect(() => { load().catch((err) => toast.error(messageFrom(err))); }, [load, toast]);

  useEffect(() => {
    const code = search.get("oauth_code");
    const state = search.get("oauth_state");
    const error = search.get("linkedin_error");
    if (error && !oauthHandled.current) {
      oauthHandled.current = true;
      toast.error(t("linkedin.oauthError"));
      window.history.replaceState({}, "", window.location.pathname);
      return;
    }
    if (!code || !state || oauthHandled.current) return;
    oauthHandled.current = true;
    setBusy(true);
    api<LinkedInChannel>(`/linkedin/channels/${id}/oauth/complete`, {
      method: "POST",
      body: JSON.stringify({ code, state }),
    })
      .then((row) => {
        setChannel(row);
        toast.success(t("linkedin.saved"));
        window.history.replaceState({}, "", window.location.pathname);
      })
      .catch((err) => toast.error(messageFrom(err)))
      .finally(() => setBusy(false));
  }, [id, search, t, toast]);

  function openGuide() {
    setGuideOpen(true);
    requestAnimationFrame(() => {
      document.getElementById("li-guide")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function openAdvanced() {
    setAdvancedOpen(true);
    requestAnimationFrame(() => {
      document.getElementById("li-advanced")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function requestConnect() {
    setConsentOpen(true);
  }

  async function connectLinkedIn() {
    setBusy(true);
    try {
      const session = await api<LinkedInOAuthSession>(`/linkedin/channels/${id}/oauth/session`, {
        method: "POST",
        body: JSON.stringify(buildChannelConsent("linkedin", id)),
      });
      if (session.mock_mode) {
        const row = await api<LinkedInChannel>(`/linkedin/channels/${id}/oauth/complete`, {
          method: "POST",
          body: JSON.stringify({ state: session.state, use_mock: true }),
        });
        setChannel(row);
        toast.success(t("linkedin.saved"));
      } else if (session.dialog_url) {
        window.location.assign(session.dialog_url);
      }
    } catch (err) {
      toast.error(messageFrom(err));
      if (!options?.oauth_available) openGuide();
    } finally {
      setBusy(false);
    }
  }

  async function disconnectLinkedIn() {
    setBusy(true);
    try {
      setChannel(await api<LinkedInChannel>(`/linkedin/channels/${id}/disconnect`, { method: "POST" }));
      setPublication(null);
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveVoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!channel) return;
    setBusy(true);
    try {
      setChannel(await api<LinkedInChannel>(`/linkedin/channels/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          profile_url: channel.profile_url,
          display_name: channel.display_name,
          voice_notes: channel.voice_notes,
        }),
      }));
      toast.success(t("linkedin.saved"));
    } catch (err) { toast.error(messageFrom(err)); } finally { setBusy(false); }
  }

  async function generatePost(event: FormEvent) {
    event.preventDefault();
    if (idea.trim().length < 8) { toast.error(t("linkedin.needIdea")); return; }
    setBusy(true);
    try {
      const result = await api<LinkedInPostResult>(`/linkedin/channels/${id}/posts`, {
        method: "POST",
        body: JSON.stringify({ idea, language: lang }),
      });
      setPost(result);
      setPublication(null);
      setPublishApproved(false);
      await load();
    } catch (err) { toast.error(messageFrom(err)); } finally { setBusy(false); }
  }

  async function rewriteProfile(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await api<LinkedInProfileResult>(`/linkedin/channels/${id}/profile`, {
        method: "POST",
        body: JSON.stringify({ pasted, language: lang }),
      });
      setProfile(result);
      await load();
    } catch (err) { toast.error(messageFrom(err)); } finally { setBusy(false); }
  }

  async function humanizeDraft(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await api<{ text: string }>(`/linkedin/channels/${id}/humanize`, {
        method: "POST",
        body: JSON.stringify({ text: raw }),
      });
      setCleaned(result.text);
    } catch (err) { toast.error(messageFrom(err)); } finally { setBusy(false); }
  }

  async function copyText(value: string) {
    await navigator.clipboard.writeText(value);
    toast.success(t("linkedin.copied"));
  }

  async function publishPost() {
    if (!post?.draft_id || !publishApproved) return;
    setBusy(true);
    try {
      const result = await api<LinkedInPublication>(
        `/linkedin/channels/${id}/drafts/${post.draft_id}/publish`,
        {
          method: "POST",
          body: JSON.stringify({ approved: true, text: post.copy_ready }),
        },
      );
      setPublication(result);
      setPublishApproved(false);
      toast.success(t("linkedin.published"));
      await load();
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (!channel) return <div className="page-loading"><LoaderCircle className="spin" /> {t("linkedin.generating")}</div>;

  return (
    <div className="page">
      <Link href={`/clients/${id}?tab=channels`} className="back-link"><ArrowLeft size={17} /> {t("linkedin.back")}</Link>
      <PageHead eyebrow={t("linkedin.eyebrow")} title={t("linkedin.pageTitle")} description={t("linkedin.pageCopy")} />

      <div className="wa-layout">
        <main>
          <section className="wa-panel">
            <div className="wa-connect-head">
              <div className="channel-icon linkedin"><Linkedin size={22} /></div>
              <div>
                <h2>{t("linkedin.connectTitle")}</h2>
                <p>{t("linkedin.connectCopy")}</p>
              </div>
              <div className={`wa-state ${channel.status === "connected" ? "connected" : ""}`}>
                <CheckCircle2 size={17} /> {channel.status === "connected" ? t("linkedin.connectedAs", { name: channel.display_name }) : t("linkedin.status")}
              </div>
            </div>
            {!options?.oauth_available && (
              <Alert type="info">
                <div>
                  <strong>{t("linkedin.oauthUnavailableTitle")}</strong>
                  <p style={{ margin: "8px 0 0" }}>{t("linkedin.oauthUnavailableCopy")}</p>
                </div>
              </Alert>
            )}
            {channel.last_error && <Alert>{channel.last_error}</Alert>}
            <div className="wa-actions">
              {channel.status === "connected" ? (
                <button type="button" className="button secondary" onClick={disconnectLinkedIn} disabled={busy}>
                  <LogOut size={17} /> {t("linkedin.disconnect")}
                </button>
              ) : (
                <button type="button" className="button primary" onClick={requestConnect} disabled={busy || !options?.oauth_available}>
                  {busy ? <LoaderCircle className="spin" size={17} /> : <Linkedin size={17} />} {busy ? t("linkedin.connecting") : t("linkedin.connect")}
                </button>
              )}
              <button type="button" className="button secondary" onClick={openGuide}><BookOpen size={17} /> {t("linkedin.guideOpen")}</button>
              <Link className="button secondary" href="/playground?view=manual&lesson=linkedin"><BookOpen size={17} /> {t("linkedin.manualLink")}</Link>
              <button type="button" className="button secondary" onClick={openAdvanced}>{t("linkedin.openAdvanced")}</button>
            </div>
          </section>

          <section className="wa-panel wa-accordion-panel" id="li-guide">
            <button type="button" className="wa-accordion-trigger" onClick={() => setGuideOpen((v) => !v)} aria-expanded={guideOpen}>
              <span><BookOpen size={19} /></span>
              <div><h2>{t("linkedin.guideTitle")}</h2><p>{t("linkedin.guideIntro")}</p></div>
              <ChevronDown size={18} className={guideOpen ? "open" : ""} />
            </button>
            {guideOpen && (
              <div className="wa-accordion-body">
                <h3>{t("linkedin.prereqTitle")}</h3>
                <ol className="wa-steps">
                  <li>{t("linkedin.prereq1")}</li>
                  <li>{t("linkedin.prereq2")}</li>
                  <li>{t("linkedin.prereq3")}</li>
                </ol>
                <h3>{t("linkedin.stepsTitle")}</h3>
                <ol className="wa-steps">
                  <li>{t("linkedin.step1")}</li>
                  <li>{t("linkedin.step2")}</li>
                  <li>{t("linkedin.step3")}</li>
                  <li>{t("linkedin.step4")}</li>
                  <li>{t("linkedin.step5")}</li>
                </ol>
                <p>{t("linkedin.whereCopy")}</p>
                <a className="button secondary" href="https://www.linkedin.com/developers/apps" target="_blank" rel="noreferrer">
                  <ExternalLink size={16} /> LinkedIn Developer
                </a>
                <button type="button" className="button secondary" onClick={openAdvanced}>
                  {t("linkedin.openAdvanced")}
                </button>
              </div>
            )}
          </section>

          <section className="wa-panel wa-accordion-panel" id="li-advanced">
            <button type="button" className="wa-accordion-trigger" onClick={() => setAdvancedOpen((v) => !v)} aria-expanded={advancedOpen}>
              <span><Sparkles size={19} /></span>
              <div><h2>{t("linkedin.advancedTitle")}</h2><p>{t("linkedin.advancedCopy")}</p></div>
              <ChevronDown size={18} className={advancedOpen ? "open" : ""} />
            </button>
            {advancedOpen && (
              <form className="wa-accordion-body wa-cloud-form" onSubmit={saveVoice}>
                <label>{t("linkedin.profileUrl")}<input value={channel.profile_url} onChange={(e) => setChannel({ ...channel, profile_url: e.target.value })} /></label>
                <label>{t("linkedin.displayName")}<input value={channel.display_name} onChange={(e) => setChannel({ ...channel, display_name: e.target.value })} /></label>
                <label>{t("linkedin.voiceNotes")}<textarea rows={7} value={channel.voice_notes} onChange={(e) => setChannel({ ...channel, voice_notes: e.target.value })} /></label>
                <button className="button primary" disabled={busy}>{t("linkedin.saveVoice")}</button>
              </form>
            )}
          </section>

          <nav className="tabs client-tabs">
            <button className={tab === "post" ? "active" : ""} onClick={() => setTab("post")}>{t("linkedin.tabPost")}</button>
            <button className={tab === "profile" ? "active" : ""} onClick={() => setTab("profile")}>{t("linkedin.tabProfile")}</button>
            <button className={tab === "drafts" ? "active" : ""} onClick={() => setTab("drafts")}>{t("linkedin.tabDrafts")}</button>
          </nav>

          {tab === "post" && (
            <section className="wa-panel">
              <Alert type="info">{t("linkedin.fallbackHint")}</Alert>
              <form onSubmit={generatePost} className="page-form" style={{ padding: 0 }}>
                <label>{t("linkedin.ideaLabel")}<textarea rows={4} value={idea} onChange={(e) => setIdea(e.target.value)} placeholder={t("linkedin.ideaPlaceholder")} /></label>
                <button className="button primary" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : null} {t("linkedin.generate")}</button>
              </form>
              {post && (
                <div style={{ marginTop: 22 }}>
                  <h3>{t("linkedin.hooksTitle")}</h3>
                  <ol>
                    {post.hooks?.map((hook) => (
                      <li key={hook.id}><strong>#{hook.id} {hook.name}</strong> — {hook.line}{hook.id === post.chosen_hook_id ? ` (${t("linkedin.shipping")})` : ""}</li>
                    ))}
                  </ol>
                  <p><strong>{t("linkedin.humanScore")}:</strong> {post.humanize?.panel?.human_score} {post.humanize?.panel?.verdict} · {t("linkedin.stripped", { count: post.humanize?.stripped || 0 })}</p>
                  {(post.humanize?.structures || []).length > 0 && (
                    <p><strong>{t("linkedin.structures")}:</strong> {post.humanize.structures.map((s) => s.name).join(" · ")}</p>
                  )}
                  <textarea
                    className="li-copy-block li-copy-editor"
                    rows={14}
                    value={post.copy_ready}
                    maxLength={3000}
                    onChange={(event) => setPost({ ...post, copy_ready: event.target.value })}
                  />
                  <p>{post.post_at_hint || t("linkedin.postHint")}</p>
                  <div className="wa-actions">
                    <button type="button" className="button secondary" onClick={() => copyText(post.copy_ready)}><Copy size={16} /> {t("linkedin.copy")}</button>
                  </div>
                  {channel.publishes ? (
                    <div className="li-publish-box">
                      <SwitchRow
                        label={t("linkedin.publishConfirm")}
                        checked={publishApproved}
                        onChange={setPublishApproved}
                      />
                      <button type="button" className="button primary" disabled={busy || !publishApproved || !post.copy_ready.trim()} onClick={publishPost}>
                        {busy ? <LoaderCircle className="spin" size={17} /> : <Send size={17} />} {busy ? t("linkedin.publishing") : t("linkedin.publish")}
                      </button>
                    </div>
                  ) : (
                    <Alert type="info">{t("linkedin.connectFirst")}</Alert>
                  )}
                  {publication && (
                    <Alert type="success">
                      <strong>{t("linkedin.published")}</strong>
                      <p>{t("linkedin.publishedId", { id: publication.provider_post_id })}</p>
                    </Alert>
                  )}
                </div>
              )}
            </section>
          )}

          {tab === "profile" && (
            <section className="wa-panel">
              <form onSubmit={rewriteProfile} className="page-form" style={{ padding: 0 }}>
                <label>{t("linkedin.profilePaste")}<textarea rows={10} value={pasted} onChange={(e) => setPasted(e.target.value)} placeholder={t("linkedin.profilePlaceholder")} required minLength={20} /></label>
                <button className="button primary" disabled={busy}>{t("linkedin.scoreProfile")}</button>
              </form>
              {profile && (
                <div style={{ marginTop: 22 }}>
                  {profile.audit && <p><strong>{t("linkedin.audit")}:</strong> {profile.audit.total} / {profile.audit.max}</p>}
                  <h3>{t("linkedin.headline")}</h3>
                  <pre className="li-copy-block">{profile.headline}</pre>
                  <button type="button" className="button secondary" onClick={() => copyText(profile.headline)}><Copy size={16} /> {t("linkedin.copy")}</button>
                  <h3>{t("linkedin.about")}</h3>
                  <pre className="li-copy-block">{profile.about}</pre>
                  <button type="button" className="button secondary" onClick={() => copyText(profile.about)}><Copy size={16} /> {t("linkedin.copy")}</button>
                  {profile.featured && <p><strong>{t("linkedin.featured")}:</strong> {profile.featured.join(" · ")}</p>}
                  <p>{profile.copy_note}</p>
                </div>
              )}
            </section>
          )}

          {tab === "drafts" && (
            <section className="wa-panel">
              <h3>{t("linkedin.humanizeTitle")}</h3>
              <p>{t("linkedin.humanizeHint")}</p>
              <form onSubmit={humanizeDraft} className="page-form" style={{ padding: 0 }}>
                <textarea rows={6} value={raw} onChange={(e) => setRaw(e.target.value)} required />
                <button className="button secondary" disabled={busy}>{t("linkedin.humanizeRun")}</button>
              </form>
              {cleaned && <pre className="li-copy-block">{cleaned}</pre>}
              <h3 style={{ marginTop: 28 }}>{t("linkedin.tabDrafts")}</h3>
              {drafts.length ? drafts.map((item) => (
                <article key={item.id} style={{ marginBottom: 16 }}>
                  <small>{item.kind} · {item.status} · {item.verdict} {item.human_score ?? ""}</small>
                  <p>{item.body.slice(0, 280)}</p>
                  {item.provider_post_id && <small>{t("linkedin.publishedId", { id: item.provider_post_id })}</small>}
                </article>
              )) : <p>{t("linkedin.emptyDrafts")}</p>}
            </section>
          )}
        </main>
      </div>
      <ChannelConnectConsentModal
        open={consentOpen}
        channel="linkedin"
        clientId={id}
        providerTermsUrl="https://www.linkedin.com/legal/l/api-terms"
        onClose={() => setConsentOpen(false)}
        onConfirmed={() => {
          setConsentOpen(false);
          void connectLinkedIn();
        }}
      />
    </div>
  );
}

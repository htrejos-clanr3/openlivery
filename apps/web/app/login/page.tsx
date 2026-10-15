"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bot, Building2, ExternalLink, LoaderCircle, MessageSquareText, ShieldCheck } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { SwitchRow } from "@/components/switch-row";
import { Alert } from "@/components/ui";

type AuthOptions = { google_enabled: boolean; google_client_id: string | null };
type ForgotResponse = { message: string; reset_token?: string | null; account_kind?: string | null };
type LegalDocuments = {
  tos_version: string;
  privacy_version: string;
  tos_url: string;
  privacy_url: string;
};

function LoginForm() {
  const t = useT();
  const router = useRouter();
  const search = useSearchParams();
  const [mode, setMode] = useState<"login" | "register" | "forgot" | "reset" | "set">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [options, setOptions] = useState<AuthOptions | null>(null);
  const [legalDocs, setLegalDocs] = useState<LegalDocuments | null>(null);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [acceptPrivacy, setAcceptPrivacy] = useState(false);
  const [token, setToken] = useState(search.get("token") || "");

  useEffect(() => {
    api<AuthOptions>("/auth/options").then(setOptions).catch(() => setOptions({ google_enabled: false, google_client_id: null }));
    const purpose = search.get("purpose");
    if (search.get("token") && purpose === "set") setMode("set");
    else if (search.get("token")) setMode("reset");
  }, [search]);

  useEffect(() => {
    if (mode !== "register") return;
    setAcceptTerms(false);
    setAcceptPrivacy(false);
    api<LegalDocuments>("/legal/documents")
      .then(setLegalDocs)
      .catch(() => setLegalDocs(null));
  }, [mode]);

  useEffect(() => {
    if (!options?.google_enabled || !options.google_client_id) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      // @ts-expect-error Google GIS global
      window.google?.accounts.id.initialize({
        client_id: options.google_client_id,
        callback: async (response: { credential: string }) => {
          setBusy(true);
          setError("");
          try {
            await api("/auth/google", { method: "POST", body: JSON.stringify({ id_token: response.credential }) });
            router.push("/");
            router.refresh();
          } catch (err) {
            setError(messageFrom(err));
          } finally {
            setBusy(false);
          }
        },
      });
      // @ts-expect-error Google GIS global
      window.google?.accounts.id.renderButton(document.getElementById("google-btn"), {
        theme: "outline",
        size: "large",
        width: 320,
        text: "continue_with",
      });
    };
    document.body.appendChild(script);
    return () => { script.remove(); };
  }, [options, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (mode === "forgot") {
        const res = await api<ForgotResponse>("/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email: data.email, audience: "agency" }),
        });
        setInfo(t("auth.forgotSent"));
        if (res.account_kind === "google_only") {
          setInfo(`${t("auth.googleOnlyTitle")}. ${t("auth.googleOnlyHint")}`);
          if (res.reset_token) {
            setToken(res.reset_token);
            setMode("set");
          }
        } else if (res.reset_token) {
          setToken(res.reset_token);
          setMode("reset");
        }
        return;
      }
      if (mode === "reset") {
        await api("/auth/reset-password", { method: "POST", body: JSON.stringify({ token, password: data.password }) });
        router.push("/");
        router.refresh();
        return;
      }
      if (mode === "set") {
        await api("/auth/set-password", { method: "POST", body: JSON.stringify({ token, password: data.password }) });
        router.push("/");
        router.refresh();
        return;
      }
      if (mode === "register") {
        if (!acceptTerms || !acceptPrivacy) {
          setError(t("legal.registerBlocked"));
          return;
        }
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify({ ...data, accept_terms: acceptTerms, accept_privacy: acceptPrivacy }),
        });
      } else {
        await api("/auth/login", { method: "POST", body: JSON.stringify(data) });
      }
      router.push("/");
      router.refresh();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  const title =
    mode === "register" ? t("auth.cardTitleRegister")
      : mode === "forgot" ? t("auth.forgotTitle")
        : mode === "set" ? t("auth.setPasswordTitle")
          : mode === "reset" ? t("auth.resetTitle")
            : t("auth.cardTitleLogin");

  return (
    <div className="access-card">
      <span className="access-card-label"><ShieldCheck size={15} /> {t("auth.cardLabel")}</span>
      <h2>{title}</h2>
      {(mode === "login" || mode === "register") && (
        <p>{mode === "register" ? t("auth.cardSubtitleRegister") : t("auth.cardSubtitleLogin")}</p>
      )}
      {mode === "forgot" && <p>{t("auth.forgotHint")}</p>}
      {(mode === "login" || mode === "register") && (
        <div className="auth-tabs">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setError(""); }}>{t("auth.tabLogin")}</button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => { setMode("register"); setError(""); }}>{t("auth.tabRegister2")}</button>
        </div>
      )}
      {options?.google_enabled && (mode === "login" || mode === "register") && (
        <>
          <div id="google-btn" style={{ display: "flex", justifyContent: "center", marginBottom: 12 }} />
          <p style={{ textAlign: "center", opacity: 0.7 }}>{t("auth.orDivider")}</p>
        </>
      )}
      <form onSubmit={submit} className="access-form">
        {mode === "register" && <>
          <label>{t("auth.agencyName")}<input name="agency_name" required minLength={2} placeholder={t("auth.agencyNamePlaceholder")} /></label>
          <label>{t("auth.yourName")}<input name="name" required minLength={2} placeholder={t("auth.yourNamePlaceholder")} /></label>
        </>}
        {(mode === "login" || mode === "register" || mode === "forgot") && (
          <label>{t("auth.email")}<input name="email" required type="email" placeholder={t("auth.emailPlaceholder")} /></label>
        )}
        {(mode === "login" || mode === "register" || mode === "reset" || mode === "set") && (
          <label>{mode === "login" || mode === "register" ? t("auth.password") : t("auth.newPassword")}
            <input name="password" required type="password" minLength={8} placeholder={t("auth.passwordPlaceholder")} />
          </label>
        )}
        {mode === "register" && legalDocs && (
          <fieldset className="stack-form" style={{ gap: 10 }}>
            <legend>{t("legal.platformTitle")}</legend>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 12 }}>{t("legal.platformDescription")}</p>
            <SwitchRow
              label={t("legal.acceptTerms")}
              hint={(
                <a href={legalDocs.tos_url} target="_blank" rel="noreferrer">
                  {t("legal.viewTerms")} <ExternalLink size={12} />
                </a>
              )}
              checked={acceptTerms}
              onChange={setAcceptTerms}
            />
            <SwitchRow
              label={t("legal.acceptPrivacy")}
              hint={(
                <a href={legalDocs.privacy_url} target="_blank" rel="noreferrer">
                  {t("legal.viewPrivacy")} <ExternalLink size={12} />
                </a>
              )}
              checked={acceptPrivacy}
              onChange={setAcceptPrivacy}
            />
          </fieldset>
        )}
        {error && <Alert>{error}</Alert>}
        {info && <Alert type="info">{info}</Alert>}
        <button className="button primary full" disabled={busy}>
          {busy && <LoaderCircle className="spin" size={17} />}
          {mode === "register" ? t("auth.submitRegister")
            : mode === "forgot" ? t("auth.forgotSubmit")
              : mode === "reset" || mode === "set" ? t("auth.savePassword")
                : t("auth.submitLogin")}
        </button>
      </form>
      {mode === "login" && (
        <button type="button" className="button ghost full" onClick={() => { setMode("forgot"); setError(""); setInfo(""); }}>
          {t("auth.forgotPassword")}
        </button>
      )}
      {(mode === "forgot" || mode === "reset" || mode === "set") && (
        <button type="button" className="button ghost full" onClick={() => { setMode("login"); setError(""); setInfo(""); }}>
          {t("common.back")}
        </button>
      )}
      <p className="access-security"><ShieldCheck size={14} /> {t("auth.securityNote")}</p>
    </div>
  );
}

export default function LoginPage() {
  const t = useT();
  return (
    <main className="access-page agency-access">
      <header className="access-topbar">
        <div className="access-brand"><span className="openlivery-icon"><img src="/brand/app-logo-icon.png" alt="" /></span><strong>Fast Livery</strong></div>
        <small>{t("auth.tagline")}</small>
      </header>
      <div className="access-layout">
        <section className="access-intro">
          <span className="access-eyebrow">{t("auth.introEyebrow")}</span>
          <h1>{t("auth.introTitle")}</h1>
          <p>{t("auth.introDescription")}</p>
          <div className="access-preview" aria-hidden="true">
            <header><div><span className="preview-logo openlivery-icon"><img src="/brand/app-logo-icon.png" alt="" /></span><strong>{t("auth.previewTitle")}</strong></div><small>{t("auth.previewToday")}</small></header>
            <div className="preview-metrics"><article><span>{t("auth.previewClientsActive")}</span><strong>12</strong></article><article><span>{t("auth.previewAgents")}</span><strong>28</strong></article><article><span>{t("auth.previewConversations")}</span><strong>846</strong></article></div>
            <div className="preview-list">
              <div><span className="preview-icon"><Building2 size={16} /></span><p><strong>{t("auth.previewClinicName")}</strong><small>{t("auth.previewClinicMeta")}</small></p><em>{t("auth.previewActive")}</em></div>
              <div><span className="preview-icon"><MessageSquareText size={16} /></span><p><strong>{t("auth.previewInboxTitle")}</strong><small>{t("auth.previewInboxMeta")}</small></p><em>{t("auth.previewInboxTag")}</em></div>
              <div><span className="preview-icon"><Bot size={16} /></span><p><strong>{t("auth.previewKnowledgeTitle")}</strong><small>{t("auth.previewKnowledgeMeta")}</small></p><em>{t("auth.previewReady")}</em></div>
            </div>
          </div>
        </section>
        <section className="access-form-wrap">
          <Suspense fallback={<div className="access-card"><p>{t("common.loading")}</p></div>}>
            <LoginForm />
          </Suspense>
        </section>
      </div>
    </main>
  );
}

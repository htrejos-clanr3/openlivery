"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ArrowRight, CheckCircle2, ExternalLink, Eye, EyeOff, ImagePlus, KeyRound, LoaderCircle, Save, ShieldCheck, Trash2 } from "lucide-react";
import { PageHead } from "@/components/ui";
import { FileDropzone, type FileDropzoneHandle } from "@/components/file-dropzone";
import { useToast } from "@/components/toast";
import { api, messageFrom } from "@/lib/api";
import { useT, type TranslateFn } from "@/lib/i18n";
import { PROVIDERS } from "@/lib/providers";
import type { Agency, ImageGenerationStatus, Provider, ProviderTest, User } from "@/types";

export default function SettingsPage() {
  const t = useT();
  const toast = useToast();
  const [agency, setAgency] = useState<Agency | null>(null);
  const [me, setMe] = useState<User | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [imageStatus, setImageStatus] = useState<ImageGenerationStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [logoVersion, setLogoVersion] = useState(0);
  const logoDropRef = useRef<FileDropzoneHandle>(null);

  const load = async () => {
    const [a, p, img, user] = await Promise.all([
      api<Agency>("/agency"),
      api<Provider[]>("/providers"),
      api<ImageGenerationStatus>("/providers/image-generation"),
      api<User>("/auth/me"),
    ]);
    setAgency(a); setProviders(p); setImageStatus(img); setMe(user);
  };
  useEffect(() => { load(); }, []);

  async function saveIdentity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      setAgency(await api<Agency>("/agency", { method: "PATCH", body: JSON.stringify({ name: data.get("name"), slug: data.get("slug"), brand_color: data.get("brand_color") }) }));
      toast.success(t("settings.index.agencySaved"));
    } catch (err) { toast.error(messageFrom(err)); } finally { setBusy(false); }
  }
  async function uploadLogo(file?: File) {
    if (!file) return;
    setBusy(true); const data = new FormData(); data.append("file", file);
    try { setAgency(await api<Agency>("/agency/logo", { method: "POST", body: data })); setLogoVersion((v) => v + 1); toast.success(t("settings.index.logoUpdated")); }
    catch (err) { toast.error(messageFrom(err)); } finally { setBusy(false); }
  }
  async function deleteLogo() { await api("/agency/logo", { method: "DELETE" }); setLogoVersion((v) => v + 1); await load(); }

  async function saveKey(provider: string, apiKey: string): Promise<boolean> {
    if (!apiKey.trim()) return false;
    setBusy(true);
    try {
      // Validate the connection before storing; on failure nothing is saved.
      const test = await api<ProviderTest>(`/providers/${provider}/validate`, { method: "POST", body: JSON.stringify({ api_key: apiKey }) });
      await api(`/providers/${provider}`, { method: "PUT", body: JSON.stringify({ api_key: apiKey }) });
      toast.success(test.message);
      await load();
      return true;
    } catch (err) { toast.error(messageFrom(err)); return false; }
    finally { setBusy(false); }
  }
  async function removeKey(provider: string) { await api(`/providers/${provider}`, { method: "DELETE" }); await load(); }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const current = String(data.get("current_password") || "");
    const next = String(data.get("new_password") || "");
    const confirm = String(data.get("confirm_password") || "");
    if (next !== confirm) {
      toast.error(t("settings.index.passwordMismatch"));
      return;
    }
    if (me?.password_configured && current && next === current) {
      toast.error(t("settings.index.passwordSameAsCurrent"));
      return;
    }
    setBusy(true);
    try {
      const updated = await api<User>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      setMe(updated);
      form.reset();
      toast.success(t("settings.index.passwordUpdated"));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (!agency) return <div className="page-loading"><LoaderCircle className="spin" /> {t("settings.index.loading")}</div>;
  const passwordConfigured = Boolean(me?.password_configured);
  return <div className="page"><PageHead eyebrow={t("settings.index.eyebrow")} title={t("settings.index.title")} description={t("settings.index.description")} />

    <form className="page-form" onSubmit={saveIdentity}><section className="form-section"><div className="section-copy"><h2>{t("settings.index.identityHeading")}</h2><p>{t("settings.index.identityCopy")}</p></div><div className="form-fields"><div className="logo-editor"><FileDropzone ref={logoDropRef} className="logo-preview" accept="image/png,image/jpeg,image/webp,image/svg+xml" disabled={busy} onFile={uploadLogo}>{agency.logo_url ? <img src={`${agency.logo_url}?v=${logoVersion}`} alt={t("settings.index.logoAlt")} /> : <ImagePlus size={24} />}</FileDropzone><div><strong>{t("settings.index.logoLabel")}</strong><small>{t("settings.index.logoHint")}</small><div><button type="button" className="text-button" onClick={() => logoDropRef.current?.open()}>{t("settings.index.change")}</button>{agency.logo_url && <button type="button" className="text-button danger-text" onClick={deleteLogo}><Trash2 size={14} /> {t("settings.index.remove")}</button>}</div></div></div><div className="form-grid"><label>{t("settings.index.agencyName")}<input name="name" required defaultValue={agency.name} /></label><label>{t("settings.index.identifier")}<input name="slug" required defaultValue={agency.slug} /></label></div><label>{t("settings.index.brandColor")}<div className="color-input"><input type="color" name="brand_color" defaultValue={agency.brand_color} /><input defaultValue={agency.brand_color} readOnly /></div></label><button className="button primary align-start" disabled={busy}>{busy ? <LoaderCircle size={17} className="spin" /> : <Save size={17} />} {t("settings.index.saveIdentity")}</button></div></section></form>

    <form className="page-form" onSubmit={changePassword}>
      <section className="form-section">
        <div className="section-copy">
          <h2>{t("settings.index.passwordHeading")}</h2>
          <p>{passwordConfigured ? t("settings.index.passwordCopy") : t("settings.index.passwordCreateCopy")}</p>
        </div>
        <div className="form-fields">
          {passwordConfigured ? (
            <label>
              {t("settings.index.currentPassword")}
              <input name="current_password" type="password" autoComplete="current-password" required minLength={1} />
            </label>
          ) : null}
          <div className="form-grid">
            <label>
              {t("settings.index.newPassword")}
              <input name="new_password" type="password" autoComplete="new-password" required minLength={8} placeholder={t("settings.index.passwordHint")} />
            </label>
            <label>
              {t("settings.index.confirmPassword")}
              <input name="confirm_password" type="password" autoComplete="new-password" required minLength={8} />
            </label>
          </div>
          <button className="button primary align-start" disabled={busy}>
            {busy ? <LoaderCircle size={17} className="spin" /> : <KeyRound size={17} />}
            {passwordConfigured ? t("settings.index.savePassword") : t("settings.index.createPassword")}
          </button>
        </div>
      </section>
    </form>

    <section className="section-block">
      <div className="section-heading"><div><h2>{t("meta.linkFromSettings")}</h2><p>{t("meta.linkFromSettingsCopy")}</p></div></div>
      <section className="form-section">
        <div className="section-copy">
          <h2>{t("meta.title")}</h2>
          <p>{t("meta.description")}</p>
        </div>
        <div className="form-fields">
          <Link className="button secondary align-start" href="/settings/meta">{t("meta.open")} <ArrowRight size={16} /></Link>
        </div>
      </section>
    </section>

    <section className="section-block"><div className="section-heading"><div><h2>{t("settings.providers.heading")}</h2><p>{t("settings.providers.copy")}</p></div></div>
      <div className="security-note"><ShieldCheck size={20} /><span><strong>{t("settings.index.privateCredentials")}</strong> {t("settings.index.privateCredentialsCopy")}</span></div>
      {PROVIDERS.map((preset) => (
        <ProviderKeyCard key={preset.id} preset={preset} state={providers.find((x) => x.provider === preset.id)} busy={busy} onSave={saveKey} onRemove={removeKey} t={t} />
      ))}
    </section>

    <section className="section-block">
      <div className="section-heading"><div><h2>{t("settings.images.heading")}</h2><p>{t("settings.images.copy")}</p></div></div>
      {imageStatus ? (
        <section className="form-section">
          <div className="section-copy">
            <h2>{imageStatus.ready ? t("settings.images.ready") : t("settings.images.notReady")}</h2>
            <p>{imageStatus.message}</p>
          </div>
          <div className="form-fields">
            <p><strong>{t("settings.images.provider")}:</strong> {imageStatus.resolved_provider || imageStatus.provider}</p>
            {imageStatus.model ? <p><strong>{t("settings.images.model")}:</strong> {imageStatus.model}</p> : null}
            {imageStatus.base_url ? <p><strong>{t("settings.images.endpoint")}:</strong> {imageStatus.base_url}</p> : null}
            <p><strong>{t("settings.images.size")}:</strong> {imageStatus.size}</p>
            <p><strong>{t("settings.images.productEdit")}:</strong> {imageStatus.supports_product_edit ? t("settings.images.productEditYes") : t("settings.images.productEditNo")}</p>
            <p><strong>{t("settings.images.ollamaNote")}:</strong> {t("settings.images.step4")}</p>
            <details open className="provider-setup-panel">
              <summary>{t("settings.images.howToSwitch")}</summary>
              <ol>
                <li>{t("settings.images.step1")}</li>
                <li>{t("settings.images.step2")}</li>
                <li>{t("settings.images.step3")}</li>
              </ol>
            </details>
            <details className="provider-setup-panel">
              <summary>{t("settings.images.hfStepsTitle")}</summary>
              <ol>
                <li>{t("settings.images.hfStep1")}</li>
                <li>{t("settings.images.hfStep2")}</li>
                <li>{t("settings.images.hfStep3")}</li>
                <li>{t("settings.images.hfStep4")}</li>
              </ol>
            </details>
            <details className="provider-setup-panel">
              <summary>{t("settings.images.fluxStepsTitle")}</summary>
              <ol>
                <li>{t("settings.images.fluxStep1")}</li>
                <li>{t("settings.images.fluxStep2")}</li>
                <li>{t("settings.images.fluxStep3")}</li>
                <li>{t("settings.images.fluxStep4")}</li>
                <li>{t("settings.images.fluxStep5")}</li>
                <li>{t("settings.images.fluxStep6")}</li>
              </ol>
            </details>
            {imageStatus.install_hint ? <pre className="provider-setup-hint">{imageStatus.install_hint}</pre> : null}
          </div>
        </section>
      ) : (
        <p className="page-loading"><LoaderCircle className="spin" /> {t("settings.images.loading")}</p>
      )}
    </section>
  </div>;
}

function ProviderKeyCard({ preset, state, busy, onSave, onRemove, t }: { preset: (typeof PROVIDERS)[number]; state?: Provider; busy: boolean; onSave: (p: string, k: string) => Promise<boolean>; onRemove: (p: string) => Promise<void>; t: TranslateFn }) {
  const [key, setKey] = useState("");
  const [reveal, setReveal] = useState(false);
  const [replacing, setReplacing] = useState(false);
  const configured = Boolean(state?.configured) && !replacing;

  async function save() {
    if (await onSave(preset.id, key)) { setKey(""); setReplacing(false); }
  }

  return (
    <section className="form-section"><div className="section-copy"><h2>{preset.label}</h2><p>{t("settings.providers.byo", { label: preset.label })}</p><a className="text-button" href={preset.keyUrl} target="_blank" rel="noreferrer">{t("settings.providers.getKey")} <ExternalLink size={14} /></a></div>
      <div className="form-fields">
        {configured ? (
          <div className="key-configured">
            <span className="key-configured-status"><CheckCircle2 size={18} /> {t("settings.providers.configured", { label: preset.label })}</span>
            <div className="key-configured-actions">
              <button type="button" className="button ghost" disabled={busy} onClick={() => { setKey(""); setReplacing(true); }}>{t("settings.providers.replace")}</button>
              <button type="button" className="button danger" disabled={busy} onClick={() => onRemove(preset.id)}><Trash2 size={15} /> {t("settings.providers.remove")}</button>
            </div>
          </div>
        ) : (
          <>
            <label>{t("settings.providers.apiKey", { label: preset.label })}
              <div className="key-input">
                <input type={reveal ? "text" : "password"} value={key} autoComplete="new-password" onChange={(e) => setKey(e.target.value)} placeholder={preset.keyPlaceholder} />
                <button type="button" className="reveal" onClick={() => setReveal((v) => !v)} aria-label={t(reveal ? "settings.providers.hide" : "settings.providers.reveal")}>{reveal ? <EyeOff size={16} /> : <Eye size={16} />}</button>
              </div>
            </label>
            <div className="form-footer split">
              {state?.configured ? <button type="button" className="button ghost" disabled={busy} onClick={() => { setKey(""); setReplacing(false); }}>{t("common.cancel")}</button> : <span />}
              <button type="button" className="button primary" disabled={busy || !key.trim()} onClick={save}>{busy ? <LoaderCircle className="spin" size={16} /> : <Save size={16} />} {t("settings.providers.save")}</button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}

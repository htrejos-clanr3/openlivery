"use client";

import { ExternalLink } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Modal } from "@/components/ui";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";

export type ChannelKind = "instagram" | "whatsapp_cloud" | "linkedin";

type LegalDocuments = {
  tos_version: string;
  privacy_version: string;
  tos_url: string;
  privacy_url: string;
};

type PlatformStatus = {
  documents: LegalDocuments;
  terms_accepted: boolean;
  privacy_accepted: boolean;
  platform_ready: boolean;
};

type Props = {
  open: boolean;
  channel: ChannelKind;
  clientId: string;
  providerTermsUrl: string;
  onClose: () => void;
  onConfirmed: () => void;
};

export function ChannelConnectConsentModal({
  open,
  channel,
  clientId,
  providerTermsUrl,
  onClose,
  onConfirmed,
}: Props) {
  const t = useT();
  const [platformReady, setPlatformReady] = useState(true);
  const [docs, setDocs] = useState<LegalDocuments | null>(null);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [acceptPrivacy, setAcceptPrivacy] = useState(false);
  const [adminConfirmed, setAdminConfirmed] = useState(false);
  const [noPassword, setNoPassword] = useState(false);
  const [aiDisclosure, setAiDisclosure] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setError("");
    setAdminConfirmed(false);
    setNoPassword(false);
    setAiDisclosure(false);
    api<PlatformStatus>("/legal/platform/status")
      .then((status) => {
        setDocs(status.documents);
        setPlatformReady(status.platform_ready);
        setAcceptTerms(status.terms_accepted);
        setAcceptPrivacy(status.privacy_accepted);
      })
      .catch(() => setPlatformReady(false));
  }, [open]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!platformReady && (!acceptTerms || !acceptPrivacy)) {
      setError(t("legal.platformBlocked"));
      return;
    }
    if (!adminConfirmed || !noPassword || (channel === "instagram" && !aiDisclosure)) {
      setError(t("legal.connectBlocked"));
      return;
    }
    setBusy(true);
    try {
      if (!platformReady) {
        await api("/legal/platform/accept", {
          method: "POST",
          body: JSON.stringify({ accept_terms: acceptTerms, accept_privacy: acceptPrivacy }),
        });
      }
      onConfirmed();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      title={t("legal.connectTitle")}
      description={t("legal.connectDescription")}
      onClose={onClose}
    >
      <form className="modal-form" onSubmit={submit}>
        {!platformReady && docs && (
          <fieldset className="stack-form" style={{ gap: 10 }}>
            <legend>{t("legal.platformTitle")}</legend>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 12 }}>{t("legal.platformDescription")}</p>
            <label>
              <input type="checkbox" checked={acceptTerms} onChange={(e) => setAcceptTerms(e.target.checked)} />
              {" "}{t("legal.acceptTerms")}{" "}
              <a href={docs.tos_url} target="_blank" rel="noreferrer">{t("legal.viewTerms")} <ExternalLink size={12} /></a>
            </label>
            <label>
              <input type="checkbox" checked={acceptPrivacy} onChange={(e) => setAcceptPrivacy(e.target.checked)} />
              {" "}{t("legal.acceptPrivacy")}{" "}
              <a href={docs.privacy_url} target="_blank" rel="noreferrer">{t("legal.viewPrivacy")} <ExternalLink size={12} /></a>
            </label>
          </fieldset>
        )}
        <label>
          <input type="checkbox" checked={adminConfirmed} onChange={(e) => setAdminConfirmed(e.target.checked)} required />
          {" "}{t("legal.adminConfirm")}
        </label>
        <label>
          <input type="checkbox" checked={noPassword} onChange={(e) => setNoPassword(e.target.checked)} required />
          {" "}{t("legal.noPassword")}
        </label>
        {channel === "instagram" && (
          <label>
            <input type="checkbox" checked={aiDisclosure} onChange={(e) => setAiDisclosure(e.target.checked)} required />
            {" "}{t("legal.aiDisclosure")}
          </label>
        )}
        <p style={{ margin: 0, fontSize: 12 }}>
          <a href={providerTermsUrl} target="_blank" rel="noreferrer">
            {channel === "linkedin" ? t("legal.linkedinTerms") : t("legal.metaTerms")}{" "}
            <ExternalLink size={12} />
          </a>
        </p>
        {error && <p className="alert alert-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="button secondary" onClick={onClose}>{t("common.cancel")}</button>
          <button type="submit" className="button primary" disabled={busy}>{t("legal.continueConnect")}</button>
        </div>
      </form>
    </Modal>
  );
}

export function buildChannelConsent(channel: ChannelKind, clientId: string) {
  return {
    consent: {
      channel,
      client_id: clientId,
      admin_confirmed: true,
      no_password_stored: true,
      ai_disclosure_acknowledged: channel === "instagram",
    },
  };
}

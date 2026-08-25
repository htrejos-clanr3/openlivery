"use client";

import Link from "next/link";
import { AlertCircle, CheckCircle2, ExternalLink } from "lucide-react";
import { useT } from "@/lib/i18n";
import { providerById } from "@/lib/providers";
import type { Provider } from "@/types";

type Props = {
  providerId: string;
  providers: Provider[];
};

export function ProviderSetupPanel({ providerId, providers }: Props) {
  const t = useT();
  const preset = providerById(providerId);
  if (!preset) return null;

  const configured = providers.find((item) => item.provider === providerId)?.configured;
  const setupHints: Record<string, string> = {
    openai: t("agents.providerSetup.openai"),
    anthropic: t("agents.providerSetup.anthropic"),
    deepseek: t("agents.providerSetup.deepseek"),
    moonshot: t("agents.providerSetup.moonshot"),
    dashscope: t("agents.providerSetup.dashscope"),
  };

  return (
    <div className="provider-setup-panel">
      {configured ? (
        <div className="provider-setup-status ok">
          <CheckCircle2 size={16} />
          <span>{t("agents.providerSetup.configured", { label: preset.label })}</span>
        </div>
      ) : (
        <div className="provider-setup-status warn">
          <AlertCircle size={16} />
          <span>{t("agents.providerSetup.missing", { label: preset.label })}</span>
        </div>
      )}
      <p className="provider-setup-hint">{setupHints[providerId] ?? ""}</p>
      <div className="provider-setup-actions">
        <a className="text-button" href={preset.keyUrl} target="_blank" rel="noreferrer">
          {t("agents.providerSetup.getKey")} <ExternalLink size={14} />
        </a>
        {!configured && (
          <Link className="button secondary compact" href="/settings">
            {t("agents.providerSetup.openSettings")}
          </Link>
        )}
      </div>
    </div>
  );
}

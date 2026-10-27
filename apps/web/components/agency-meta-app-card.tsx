"use client";

import { useEffect, useState } from "react";
import { Check, LoaderCircle } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useToast } from "@/components/toast";

type AgencyMetaApp = { app_id: string; has_secret: boolean };

export function AgencyMetaAppCard() {
  const toast = useToast();
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [hasSecret, setHasSecret] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<AgencyMetaApp>("/agency/meta-app")
      .then((value) => {
        setAppId(value.app_id);
        setHasSecret(value.has_secret);
      })
      .catch(() => {});
  }, []);

  async function save() {
    setBusy(true);
    try {
      const result = await api<{ verified: boolean | null }>("/agency/meta-app", {
        method: "PUT",
        body: JSON.stringify({ app_id: appId, app_secret: appSecret || null }),
      });
      setHasSecret(true);
      setAppSecret("");
      if (result.verified === false) toast.error("Meta no reconoce ese App ID con ese secret");
      else toast.success(result.verified ? "App verificada en Meta" : "Guardado");
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="wa-panel">
      <div className="wa-panel-head">
        <span><Check size={19} /></span>
        <div>
          <h2>App de Meta de la agencia</h2>
          <p>Se configura una vez y la usan todos los clientes. Cada cliente conserva su número y su token.</p>
        </div>
      </div>
      <div style={{ display: "grid", gap: 12, padding: "4px 0 12px", maxWidth: 640 }}>
        <label className="field">
          App ID
          <input value={appId} onChange={(event) => setAppId(event.target.value)} placeholder="1234567890" />
        </label>
        <label className="field">
          App Secret {hasSecret ? "(vacío = conservar el actual)" : ""}
          <input
            type="password"
            value={appSecret}
            onChange={(event) => setAppSecret(event.target.value)}
            placeholder={hasSecret ? "••••••••" : "EAAG…"}
          />
        </label>
        <div>
          <button type="button" className="button primary" onClick={save} disabled={busy || !appId}>
            {busy ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Guardar app de la agencia
          </button>
        </div>
      </div>
    </section>
  );
}

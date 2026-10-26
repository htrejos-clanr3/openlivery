"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Check, Copy, LoaderCircle, RefreshCw } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useToast } from "@/components/toast";

type Step = {
  id: string;
  title: string;
  status: string;
  detail: string;
  link: string;
  value: string;
  where: string;
  how: string[];
  scope: string;
};

type Setup = {
  client_id: string;
  steps: Step[];
  values: { callback_url: string; verify_token: string; webhook_fields: string };
  summary: { green: number; amber: number; red: number };
  can_close: boolean;
};

function tone(status: string) {
  if (status === "done") return { cls: "pill ok", mark: "✓", label: "Listo" };
  if (status === "todo") return { cls: "pill bad", mark: "!", label: "Falta" };
  if (status === "manual") return { cls: "pill warn", mark: "…", label: "Revisa Meta" };
  return { cls: "pill warn", mark: "?", label: "Sin comprobar" };
}

export default function MetaSetupPage() {
  const params = useParams<{ id: string }>();
  const clientId = params?.id ?? "";
  const toast = useToast();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [hasSecret, setHasSecret] = useState(false);
  const [savingApp, setSavingApp] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const next = await api<Setup>(`/clients/${clientId}/meta-setup`);
      setSetup(next);
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }, [clientId, toast]);

  useEffect(() => {
    if (clientId) void load();
  }, [clientId, load]);

  useEffect(() => {
    api<{ app_id: string; has_secret: boolean }>("/agency/meta-app")
      .then((value) => { setAppId(value.app_id); setHasSecret(value.has_secret); })
      .catch(() => {});
  }, []);

  async function saveApp() {
    setSavingApp(true);
    try {
      const result = await api<{ verified: boolean | null }>("/agency/meta-app", {
        method: "PUT",
        body: JSON.stringify({ app_id: appId, app_secret: appSecret || null }),
      });
      setHasSecret(true);
      setAppSecret("");
      if (result.verified === false) toast.error("Meta no reconoce ese App ID con ese secret");
      else toast.success(result.verified ? "App verificada en Meta" : "Guardado");
      void load();
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setSavingApp(false);
    }
  }

  async function copy(value: string) {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      toast.success("Copiado");
    } catch {
      toast.error("No se pudo copiar");
    }
  }

  if (!setup) {
    return (
      <div className="page-loading">
        <LoaderCircle className="spin" /> Cargando…
      </div>
    );
  }

  const step = setup.steps[selected] ?? setup.steps[0];
  const isWebhook = step.id === "webhook";
  const values = [
    { label: "Callback URL", value: setup.values.callback_url },
    { label: "Verify token", value: setup.values.verify_token },
    { label: "Campo de webhook", value: setup.values.webhook_fields },
  ];

  return (
    <div className="page-form">
      <section className="form-section">
        <div className="section-copy">
          <Link className="button" href={`/clients/${clientId}`}>
            <ArrowLeft size={15} /> Volver al cliente
          </Link>
          <h1 style={{ marginTop: 12 }}>Configurar Meta</h1>
          <p>
            Sigue los pasos en orden. Los marcados <b>«Una vez por agencia»</b> se hacen solo la primera vez;
            los marcados <b>«Por cliente»</b> se repiten para cada cliente que conectes.
          </p>
        </div>
        <div className="form-fields">
          <div className="toolbar">
            <span className="pill ok">{setup.summary.green} listos</span>
            <span className="pill warn">{setup.summary.amber} por revisar</span>
            <span className="pill bad">{setup.summary.red} por corregir</span>
            <button type="button" className="button" onClick={load} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />} Comprobar de nuevo
            </button>
          </div>
        </div>
      </section>

      <div className="grid" style={{ gridTemplateColumns: "320px 1fr", gap: 18 }}>
        <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 4 }}>
          {setup.steps.map((item, index) => {
            const t = tone(item.status);
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => setSelected(index)}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    display: "flex",
                    gap: 10,
                    alignItems: "center",
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: "1px solid",
                    borderColor: index === selected ? "var(--brand, #075985)" : "#e4e8ee",
                    background: index === selected ? "#e6f0f6" : "#fff",
                    fontWeight: index === selected ? 700 : 500,
                  }}
                >
                  <span
                    aria-hidden
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: "50%",
                      display: "grid",
                      placeItems: "center",
                      fontSize: 11,
                      fontWeight: 700,
                      background: item.status === "done" ? "#15803d" : "#e2e8f0",
                      color: item.status === "done" ? "#fff" : "#475569",
                      flex: "none",
                    }}
                  >
                    {item.status === "done" ? <Check size={12} /> : index + 1}
                  </span>
                  <span style={{ flex: 1 }}>
                    {item.title}
                    <small className="field-help" style={{ display: "block", fontSize: 11 }}>
                      {item.scope === "agency" ? "una vez" : "por cliente"}
                    </small>
                  </span>
                  <span className={t.cls} title={t.label}>
                    {t.mark}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>

        <section className="form-section" style={{ margin: 0 }}>
          <div className="section-copy">
            <div className="row" style={{ gap: 8, marginBottom: 6 }}>
              <span className={step.scope === "agency" ? "pill info" : "pill mute"}>
                {step.scope === "agency" ? "Una vez por agencia" : "Por cliente"}
              </span>
            </div>
            <h2>{step.title}</h2>
            <p>{step.detail}</p>
          </div>
          <div className="form-fields">
            {step.link && (
              <a className="button" href={step.link} target="_blank" rel="noreferrer">
                Abrir en Meta →
              </a>
            )}

            {step.id === "credentials" && (
              <div style={{ background: "#f8fafc", border: "1px solid #e4e8ee", borderRadius: 10, padding: "14px" }}>
                <strong style={{ fontSize: 13 }}>Credenciales de la agencia</strong>
                <p className="field-help" style={{ margin: "4px 0 10px" }}>
                  Se guardan una vez y sirven para todos los clientes. {hasSecret ? "Ya hay un secret guardado." : "Todavía no hay secret guardado."}
                </p>
                <label className="field">
                  App ID
                  <input value={appId} onChange={(e) => setAppId(e.target.value)} placeholder="1234567890" />
                </label>
                <label className="field" style={{ marginTop: 10 }}>
                  App Secret {hasSecret ? "(déjalo vacío para conservar el actual)" : ""}
                  <input type="password" value={appSecret} onChange={(e) => setAppSecret(e.target.value)} placeholder="••••••••" />
                </label>
                <button type="button" className="button primary" style={{ marginTop: 12 }} onClick={saveApp} disabled={savingApp || !appId}>
                  {savingApp ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Guardar en la agencia
                </button>
              </div>
            )}

            {step.where && (
              <div style={{ background: "#f8fafc", border: "1px solid #e4e8ee", borderRadius: 10, padding: "12px 14px" }}>
                <strong style={{ fontSize: 13 }}>Dónde</strong>
                <p className="field-help" style={{ margin: "4px 0 0" }}>{step.where}</p>
              </div>
            )}
            {step.how?.length ? (
              <div>
                <strong style={{ fontSize: 13 }}>Qué hacer</strong>
                <ol style={{ margin: "6px 0 0", paddingLeft: 20, fontSize: 13.5, lineHeight: 1.7 }}>
                  {step.how.map((line) => <li key={line}>{line}</li>)}
                </ol>
              </div>
            ) : null}

            {isWebhook && (
              <>
                <h3 style={{ margin: "8px 0 0" }}>Valores para pegar en Meta</h3>
                {values.map((item) => (
              <label key={item.label}>
                {item.label}
                <span style={{ display: "flex", gap: 8 }}>
                  <input readOnly value={item.value || "—"} />
                  <button type="button" className="button" onClick={() => copy(item.value)} disabled={!item.value}>
                    <Copy size={14} />
                  </button>
                </span>
              </label>
            ))}

                <p className="field-help">
                  Pega cada valor en la pantalla de Meta que abre el botón de arriba, guarda allí y vuelve aquí a
                  pulsar «Comprobar de nuevo».
                </p>
              </>
            )}
            <button type="button" className="button primary" onClick={load} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}{" "}
              {isWebhook ? "Ya lo pegué: comprobar" : "Comprobar de nuevo"}
            </button>
          </div>
        </section>
      </div>

      <section className="form-section">
        <div className="section-copy">
          <h2>¿Puedo cerrar?</h2>
          <p>
            {setup.can_close
              ? "Sí. Los puntos ámbar dependen de una revisión de Meta y se comprueban solos; no bloquean el uso del canal."
              : "Todavía no: hay puntos en rojo que sí puedes corregir tú. Ábrelos en la lista y sigue la instrucción."}
          </p>
        </div>
      </section>
    </div>
  );
}

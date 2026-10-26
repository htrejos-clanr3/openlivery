"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Check, ChevronDown, Copy, LoaderCircle, RefreshCw } from "lucide-react";
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
  channel: { phone_number_id: string; waba_id: string; has_token: boolean };
};

function tone(status: string) {
  if (status === "done") return { cls: "pill ok", mark: "✓" };
  if (status === "todo") return { cls: "pill bad", mark: "!" };
  if (status === "manual") return { cls: "pill mute", mark: "i" };
  return { cls: "pill warn", mark: "?" };
}

export default function MetaSetupPage() {
  const params = useParams<{ id: string }>();
  const clientId = params?.id ?? "";
  const toast = useToast();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [open, setOpen] = useState<number | null>(0);
  const [busy, setBusy] = useState(false);
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [hasSecret, setHasSecret] = useState(false);
  const [savingApp, setSavingApp] = useState(false);
  const setupRef = useRef<Setup | null>(null);
  const [phoneId, setPhoneId] = useState("");
  const [wabaId, setWabaId] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [savingChannel, setSavingChannel] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const next = await api<Setup>(`/clients/${clientId}/meta-setup`);
      const previous = setupRef.current;
      const changed = !previous
        || previous.summary.green !== next.summary.green
        || previous.summary.red !== next.summary.red;
      if (previous) {
        if (changed) toast.success(`Actualizado: ${next.summary.green} listos, ${next.summary.red} por corregir`);
        else toast.info("Comprobado: sin cambios. Revisa el paso que falta.");
      }
      setupRef.current = next;
      setSetup(next);
      setPhoneId(next.channel.phone_number_id);
      setWabaId(next.channel.waba_id);
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
      .then((value) => {
        setAppId(value.app_id);
        setHasSecret(value.has_secret);
      })
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

  async function saveChannel() {
    setSavingChannel(true);
    try {
      await api(`/clients/${clientId}/meta-setup/channel`, {
        method: "PUT",
        body: JSON.stringify({ phone_number_id: phoneId, waba_id: wabaId, access_token: tokenInput || null }),
      });
      setTokenInput("");
      toast.success("Guardado en el canal");
      void load();
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setSavingChannel(false);
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
            Abre un paso y haz lo que dice. Los marcados <b>«una vez»</b> se hacen solo la primera vez; los
            marcados <b>«por cliente»</b> se repiten para cada cliente que conectes.
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

      <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
        {setup.steps.map((step, index) => {
          const t = tone(step.status);
          const isOpen = open === index;
          const isWebhook = step.id === "webhook";
          return (
            <li key={step.id} style={{ background: "#fff", border: "1px solid #e4e8ee", borderRadius: 12 }}>
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : index)}
                style={{
                  width: "100%",
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  padding: "14px 16px",
                  background: isOpen ? "#eef6fb" : "transparent",
                  border: 0,
                  borderRadius: isOpen ? "12px 12px 0 0" : 12,
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <span
                  aria-hidden
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    display: "grid",
                    placeItems: "center",
                    fontSize: 11,
                    fontWeight: 700,
                    background: step.status === "done" ? "#15803d" : "#e2e8f0",
                    color: step.status === "done" ? "#fff" : "#475569",
                    flex: "none",
                  }}
                >
                  {step.status === "done" ? <Check size={13} /> : index + 1}
                </span>
                <span style={{ flex: 1 }}>
                  <strong style={{ display: "block" }}>{index + 1}. {step.title}</strong>
                  <small className="field-help" style={{ fontSize: 11.5 }}>
                    {step.scope === "agency" ? "una vez" : "por cliente"}
                  </small>
                </span>
                <span className={t.cls}>{t.mark}</span>
                <ChevronDown size={16} style={{ transform: isOpen ? "rotate(180deg)" : "none", opacity: 0.5 }} />
              </button>

              {isOpen && (
                <div style={{ padding: "4px 16px 18px 52px", display: "grid", gap: 14 }}>
                  <p className="field-help" style={{ margin: 0 }}>{step.detail}</p>

                  {step.id === "credentials" && (
                    <div style={{ background: "#f8fafc", border: "1px solid #e4e8ee", borderRadius: 10, padding: 14 }}>
                      <strong style={{ fontSize: 13 }}>Credenciales de la agencia</strong>
                      <p className="field-help" style={{ margin: "4px 0 10px" }}>
                        Se guardan una vez y sirven para todos los clientes.{" "}
                        {hasSecret ? "Ya hay un secret guardado." : "Todavía no hay secret guardado."}
                      </p>
                      <label className="field">
                        App ID
                        <input value={appId} onChange={(e) => setAppId(e.target.value)} placeholder="1234567890" />
                      </label>
                      <label className="field" style={{ marginTop: 10 }}>
                        App Secret {hasSecret ? "(vacío = conservar el actual)" : ""}
                        <input
                          type="password"
                          value={appSecret}
                          onChange={(e) => setAppSecret(e.target.value)}
                          placeholder="••••••••"
                        />
                      </label>
                      <button
                        type="button"
                        className="button primary"
                        style={{ marginTop: 12 }}
                        onClick={saveApp}
                        disabled={savingApp || !appId}
                      >
                        {savingApp ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Guardar en la
                        agencia
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
                        {step.how.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ol>
                    </div>
                  ) : null}

                  {isWebhook && (
                    <>
                      <strong style={{ fontSize: 13 }}>Valores para pegar en Meta</strong>
                      {values.map((item) => (
                        <label key={item.label}>
                          {item.label}
                          <span style={{ display: "flex", gap: 8 }}>
                            <input readOnly value={item.value || "—"} />
                            <button
                              type="button"
                              className="button"
                              onClick={() => copy(item.value)}
                              disabled={!item.value}
                            >
                              <Copy size={14} />
                            </button>
                          </span>
                        </label>
                      ))}
                    </>
                  )}

                  {step.id === "app" && (
                    <button type="button" className="button" onClick={() => setOpen(1)} style={{ justifySelf: "start" }}>
                      Ir al paso 2: registrar App ID →
                    </button>
                  )}

                  {step.id === "waba" && (
                    <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: "12px 14px" }}>
                      <strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>Pega aquí los dos identificadores</strong>
                      <label className="field" style={{ marginTop: 10 }}>
                        Phone number ID
                        <input value={phoneId} onChange={(e) => setPhoneId(e.target.value)} placeholder="1234567890" />
                      </label>
                      <label className="field" style={{ marginTop: 10 }}>
                        Messaging Account ID
                        <input value={wabaId} onChange={(e) => setWabaId(e.target.value)} placeholder="0987654321" />
                      </label>
                      <button
                        type="button"
                        className="button primary"
                        style={{ marginTop: 12 }}
                        onClick={saveChannel}
                        disabled={savingChannel}
                      >
                        {savingChannel ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Guardar en el canal
                      </button>
                    </div>
                  )}

                  {step.id === "token" && (
                    <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: "12px 14px" }}>
                      <strong style={{ fontSize: 13 }}>
                        Pega aquí el token permanente {setup.channel.has_token ? "(ya hay uno guardado)" : ""}
                      </strong>
                      <label className="field" style={{ marginTop: 10 }}>
                        Token de acceso
                        <input
                          type="password"
                          value={tokenInput}
                          onChange={(e) => setTokenInput(e.target.value)}
                          placeholder={setup.channel.has_token ? "•••• (vacío = conservar)" : "EAAG…"}
                        />
                      </label>
                      <button type="button" className="button primary" style={{ marginTop: 12 }} onClick={saveChannel} disabled={savingChannel}>
                        {savingChannel ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Guardar en el canal
                      </button>
                    </div>
                  )}

                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                    {step.link && (
                      <a className="button" href={step.link} target="_blank" rel="noreferrer">
                        Abrir en Meta →
                      </a>
                    )}
                    <button type="button" className="button primary" onClick={load} disabled={busy}>
                      {busy ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}{" "}
                      {isWebhook ? "Ya lo pegué: comprobar" : "Comprobar de nuevo"}
                    </button>
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ol>

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

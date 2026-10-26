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
            Sigue los pasos en orden. En cada uno verás el enlace, el valor que debes pegar en Meta y su
            estado. Nada se publica hasta que todo esté en verde.
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
                  <span style={{ flex: 1 }}>{item.title}</span>
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
            <h2>{step.title}</h2>
            <p>{step.detail}</p>
          </div>
          <div className="form-fields">
            {step.link && (
              <a className="button" href={step.link} target="_blank" rel="noreferrer">
                Abrir en Meta →
              </a>
            )}

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
            <button type="button" className="button primary" onClick={load} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />} Ya lo pegué: comprobar
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

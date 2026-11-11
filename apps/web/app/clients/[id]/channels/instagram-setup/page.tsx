"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Check, ChevronDown, Instagram, LoaderCircle, RefreshCw } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useToast } from "@/components/toast";

type Step = {
  id: string;
  title: string;
  status: string;
  detail: string;
  where: string;
  how: string[];
  scope: string;
};

type Setup = {
  steps: Step[];
  summary: { green: number; amber: number; red: number };
  can_close: boolean;
  channel: { username: string; page_id: string; status: string };
};

function tone(status: string) {
  if (status === "done") return { cls: "pill ok", mark: "✓" };
  if (status === "todo") return { cls: "pill bad", mark: "!" };
  return { cls: "pill warn", mark: "i" };
}

export default function InstagramSetupPage() {
  const params = useParams<{ id: string }>();
  const clientId = params?.id ?? "";
  const toast = useToast();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [open, setOpen] = useState<string | null>("app");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setSetup(await api<Setup>(`/clients/${clientId}/instagram-setup`));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }, [clientId, toast]);

  useEffect(() => {
    if (clientId) void load();
  }, [clientId, load]);

  if (!setup) {
    return (
      <div className="page-loading">
        <LoaderCircle className="spin" /> Cargando…
      </div>
    );
  }

  const agencySteps = setup.steps.filter((item) => item.scope === "agency");
  const clientSteps = setup.steps.filter((item) => item.scope !== "agency");
  const agencyPending = agencySteps.filter((item) => item.status !== "done");

  return (
    <div className="page-form">
      <section
        style={{
          display: "flex",
          gap: 20,
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          padding: "18px 20px",
          border: "1px solid #e4e8ee",
          borderRadius: 14,
          background: "#fff",
        }}
      >
        <div style={{ display: "flex", gap: 14, alignItems: "center", minWidth: 0 }}>
          <span
            aria-hidden
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              display: "grid",
              placeItems: "center",
              background: "linear-gradient(135deg,#f9ce34,#ee2a7b 55%,#6228d7)",
              color: "#fff",
              flex: "none",
            }}
          >
            <Instagram size={24} />
          </span>
          <div style={{ minWidth: 0 }}>
            <small className="field-help" style={{ textTransform: "uppercase", letterSpacing: ".05em", fontSize: 11 }}>
              Canal de Instagram
            </small>
            <h1 style={{ margin: "2px 0 0", fontSize: 22, whiteSpace: "nowrap" }}>Configurar Instagram</h1>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <span className="pill ok">{setup.summary.green} listos</span>
          <span className="pill warn">{setup.summary.amber} por revisar</span>
          <span className="pill bad">{setup.summary.red} por corregir</span>
          <button type="button" className="button" onClick={load} disabled={busy}>
            {busy ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />} Comprobar
          </button>
        </div>
      </section>

      <section className="form-section" style={{ padding: "0 4px" }}>
        <div className="section-copy">
          <p className="field-help" style={{ margin: 0 }}>
            {agencyPending.length === 0
              ? "La configuración de la agencia está lista. Aquí solo van los datos de este cliente."
              : "La agencia aún tiene pasos pendientes de su lado. Lo que veas aquí es solo de este cliente."}
          </p>
        </div>
        <div className="form-fields">
          <Link className="button" href={`/clients/${clientId}/channels/instagram`}>
            <ArrowLeft size={15} /> Volver al canal
          </Link>
        </div>
      </section>

      <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
        {clientSteps.map((step, index) => {
          const t = tone(step.status);
          const isOpen = open === step.id;
          return (
            <li key={step.id} style={{ background: "#fff", border: "1px solid #e4e8ee", borderRadius: 12 }}>
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : step.id)}
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
                  <strong style={{ display: "block" }}>{step.title}</strong>
                  <small className="field-help" style={{ fontSize: 11.5 }}>
                    {step.scope === "agency" ? "una vez" : "por cliente"}
                  </small>
                </span>
                <span className={t.cls}>{t.mark}</span>
                <ChevronDown size={16} style={{ transform: isOpen ? "rotate(180deg)" : "none", opacity: 0.5 }} />
              </button>

              {isOpen && (
                <div style={{ padding: "4px 16px 18px 52px", display: "grid", gap: 12 }}>
                  <p className="field-help" style={{ margin: 0 }}>{step.detail}</p>
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
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <Link className="button primary" href={`/clients/${clientId}/channels/instagram`}>
                      Ir al canal de Instagram →
                    </Link>
                    <button type="button" className="button" onClick={load} disabled={busy}>
                      {busy ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />} Comprobar
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
              ? "Sí. No queda ningún paso en rojo que dependa de ti."
              : "Todavía no: hay pasos en rojo. Ábrelos y sigue la instrucción."}
          </p>
        </div>
      </section>
    </div>
  );
}

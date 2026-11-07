"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, LoaderCircle, RefreshCw } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useToast } from "@/components/toast";

type Lead = {
  id: string;
  source: string;
  score: number | null;
  stage_name: string | null;
  notes: string;
  next_action: string;
  last_activity_at: string | null;
  contact: { name: string | null; phone: string | null; email?: string | null };
};

type Bucket = "all" | "hot" | "warm" | "cold" | "unscored";

function bucketOf(score: number | null): Exclude<Bucket, "all"> {
  if (score === null || score === undefined) return "unscored";
  if (score >= 75) return "hot";
  if (score >= 45) return "warm";
  return "cold";
}

function badge(bucket: Exclude<Bucket, "all">) {
  if (bucket === "hot") return { cls: "pill ok", label: "Caliente" };
  if (bucket === "warm") return { cls: "pill warn", label: "Tibio" };
  if (bucket === "cold") return { cls: "pill bad", label: "Frío" };
  return { cls: "pill", label: "Sin calificar" };
}

export default function ClientLeadsPage() {
  const params = useParams<{ id: string }>();
  const clientId = params?.id ?? "";
  const toast = useToast();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [bucket, setBucket] = useState<Bucket>("all");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setLeads(await api<Lead[]>(`/clients/${clientId}/leads`));
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }, [clientId, toast]);

  useEffect(() => {
    if (clientId) void load();
  }, [clientId, load]);

  const sorted = useMemo(
    () =>
      [...leads]
        .filter((lead) => bucket === "all" || bucketOf(lead.score) === bucket)
        .sort((a, b) => (b.score ?? -1) - (a.score ?? -1)),
    [leads, bucket],
  );

  const counts = useMemo(() => {
    const base = { hot: 0, warm: 0, cold: 0, unscored: 0 } as Record<string, number>;
    for (const lead of leads) base[bucketOf(lead.score)] += 1;
    return base;
  }, [leads]);

  return (
    <div className="page-form">
      <section className="form-section">
        <div className="section-copy">
          <Link className="button" href={`/clients/${clientId}`}>
            <ArrowLeft size={15} /> Volver al cliente
          </Link>
          <h1 style={{ marginTop: 12 }}>Leads y evaluación</h1>
          <p>Ordenados por calificación. El puntaje sale del perfil de cliente ideal.</p>
        </div>
        <div className="form-fields">
          <div className="toolbar" style={{ flexWrap: "wrap", gap: 8 }}>
            <button type="button" className={bucket === "all" ? "button primary" : "button"} onClick={() => setBucket("all")}>
              Todos ({leads.length})
            </button>
            <button type="button" className={bucket === "hot" ? "button primary" : "button"} onClick={() => setBucket("hot")}>
              Calientes ({counts.hot})
            </button>
            <button type="button" className={bucket === "warm" ? "button primary" : "button"} onClick={() => setBucket("warm")}>
              Tibios ({counts.warm})
            </button>
            <button type="button" className={bucket === "cold" ? "button primary" : "button"} onClick={() => setBucket("cold")}>
              Fríos ({counts.cold})
            </button>
            <button type="button" className={bucket === "unscored" ? "button primary" : "button"} onClick={() => setBucket("unscored")}>
              Sin calificar ({counts.unscored})
            </button>
            <button type="button" className="button" onClick={load} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />} Actualizar
            </button>
          </div>
        </div>
      </section>

      <section className="form-section">
        <div className="form-fields" style={{ gridColumn: "1 / -1" }}>
          {sorted.length === 0 ? (
            <p className="field-help">
              {leads.length === 0
                ? "Este cliente aún no tiene leads. Se crean solos cuando entra una conversación."
                : "No hay leads en este filtro."}
            </p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5 }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid #e4e8ee" }}>
                  <th style={{ padding: "8px 6px" }}>Lead</th>
                  <th style={{ padding: "8px 6px" }}>Origen</th>
                  <th style={{ padding: "8px 6px" }}>Etapa</th>
                  <th style={{ padding: "8px 6px" }}>Puntaje</th>
                  <th style={{ padding: "8px 6px" }}>Evaluación</th>
                  <th style={{ padding: "8px 6px" }}>Última actividad</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((lead) => {
                  const b = badge(bucketOf(lead.score));
                  return (
                    <tr key={lead.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "10px 6px" }}>
                        <strong>{lead.contact?.name || "Sin nombre"}</strong>
                        <div className="field-help">{lead.contact?.phone || lead.contact?.email || "—"}</div>
                      </td>
                      <td style={{ padding: "10px 6px" }}>{lead.source || "—"}</td>
                      <td style={{ padding: "10px 6px" }}>{lead.stage_name || "—"}</td>
                      <td style={{ padding: "10px 6px" }}>{lead.score ?? "—"}</td>
                      <td style={{ padding: "10px 6px" }}>
                        <span className={b.cls}>{b.label}</span>
                      </td>
                      <td style={{ padding: "10px 6px" }}>
                        {lead.last_activity_at ? new Date(lead.last_activity_at).toLocaleString() : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

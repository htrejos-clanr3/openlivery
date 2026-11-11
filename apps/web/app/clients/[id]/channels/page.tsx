"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, LoaderCircle } from "lucide-react";
import { api } from "@/lib/api";

type ChannelCard = {
  id: string;
  name: string;
  status: string;
  detail: string;
  href: string;
  wizard: string;
};

export default function ClientChannelsPage() {
  const params = useParams<{ id: string }>();
  const clientId = params?.id ?? "";
  const [cards, setCards] = useState<ChannelCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!clientId) return;
    let alive = true;
    async function load() {
      const base = [
        { id: "whatsapp", name: "WhatsApp Cloud", href: `/clients/${clientId}/channels/whatsapp-cloud`, wizard: `/clients/${clientId}/channels/meta-setup` },
        { id: "instagram", name: "Instagram", href: `/clients/${clientId}/channels/instagram`, wizard: `/clients/${clientId}/channels/instagram-setup` },
      ];
      const results: ChannelCard[] = [];
      for (const item of base) {
        let status = "sin configurar";
        let detail = "Sin datos";
        try {
          if (item.id === "whatsapp") {
            const channel = await api<{ phone_number?: string; phone_number_id?: string; status?: string }>(
              `/whatsapp-cloud/channels/${clientId}`,
            );
            status = channel?.status || "sin configurar";
            detail = channel?.phone_number || channel?.phone_number_id || "Sin número";
          } else {
            const channel = await api<{ username?: string; status?: string }>(`/instagram/channels/${clientId}`);
            status = channel?.status || "sin configurar";
            detail = channel?.username ? `@${channel.username}` : "Sin cuenta";
          }
        } catch {
          status = "sin configurar";
        }
        results.push({ ...item, status, detail });
      }
      if (alive) {
        setCards(results);
        setLoading(false);
      }
    }
    void load();
    return () => {
      alive = false;
    };
  }, [clientId]);

  return (
    <div className="page-form">
      <section className="form-section">
        <div className="section-copy">
          <Link className="button" href={`/clients/${clientId}`}>
            <ArrowLeft size={15} /> Volver al cliente
          </Link>
          <h1 style={{ marginTop: 12 }}>Canales</h1>
          <p>Cada canal tiene su pantalla de conexión y su paso a paso guiado.</p>
        </div>
      </section>

      <section className="form-section">
        <div className="form-fields" style={{ gridColumn: "1 / -1", display: "grid", gap: 10 }}>
          {loading ? (
            <span className="field-help"><LoaderCircle className="spin" size={15} /> Cargando…</span>
          ) : (
            cards.map((card) => (
              <div key={card.id} style={{ border: "1px solid #e4e8ee", borderRadius: 12, padding: "14px 16px", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 220 }}>
                  <strong>{card.name}</strong>
                  <div className="field-help">{card.detail}</div>
                </div>
                <span className={card.status === "connected" ? "pill ok" : "pill bad"}>
                  {card.status === "connected" ? "Conectado" : "Desconectado"}
                </span>
                <Link className="button" href={card.href}>Abrir canal</Link>
                <Link className="button primary" href={card.wizard}>Paso a paso →</Link>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

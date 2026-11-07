"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LoaderCircle } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useToast } from "@/components/toast";

type Client = { id: string; name: string };

export default function LeadsIndexPage() {
  const toast = useToast();
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<Client[]>("/clients")
      .then(setClients)
      .catch((err) => toast.error(messageFrom(err)))
      .finally(() => setLoading(false));
  }, [toast]);

  return (
    <div className="page-form">
      <section className="form-section">
        <div className="section-copy">
          <h1>Leads</h1>
          <p>Elige un cliente para ver y evaluar sus leads.</p>
        </div>
        <div className="form-fields">
          {loading ? (
            <span className="field-help">
              <LoaderCircle className="spin" size={15} /> Cargando…
            </span>
          ) : clients.length === 0 ? (
            <p className="field-help">Todavía no hay clientes.</p>
          ) : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
              {clients.map((client) => (
                <li key={client.id} style={{ border: "1px solid #e4e8ee", borderRadius: 10, padding: "12px 14px" }}>
                  <Link href={`/clients/${client.id}/leads`} style={{ fontWeight: 600 }}>
                    {client.name}
                  </Link>
                  <div className="field-help">Ver leads y su evaluación →</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}

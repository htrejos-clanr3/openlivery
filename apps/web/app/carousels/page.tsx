"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Images, LoaderCircle, Plus } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Alert, EmptyState, PageHead } from "@/components/ui";
import type { Carousel, Client } from "@/types";

export default function CarouselsPage() {
  const t = useT();
  const [items, setItems] = useState<Carousel[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  async function load() {
    const [carousels, clientRows] = await Promise.all([
      api<Carousel[]>("/carousels"),
      api<Client[]>("/clients"),
    ]);
    setItems(carousels);
    setClients(clientRows);
  }

  useEffect(() => {
    load().catch((err) => setError(messageFrom(err)));
  }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const created = await api<Carousel>("/carousels", {
        method: "POST",
        body: JSON.stringify({
          client_id: data.get("client_id"),
          title: data.get("title"),
          brief: data.get("brief"),
          language: data.get("language") || "es",
          slide_count: Number(data.get("slide_count") || 8),
          with_images: data.get("with_images") === "on",
          generate: true,
        }),
      });
      setShowForm(false);
      window.location.href = `/carousels/${created.id}`;
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  function statusLabel(status: string) {
    const key = `carousels.status.${status}` as const;
    try {
      return t(key as "carousels.status.draft");
    } catch {
      return status;
    }
  }

  return (
    <div className="page">
      <PageHead
        eyebrow={t("carousels.page.eyebrow")}
        title={t("carousels.page.title")}
        description={t("carousels.page.description")}
        action={
          <button className="button primary" type="button" onClick={() => setShowForm((v) => !v)}>
            <Plus size={16} /> {t("carousels.list.new")}
          </button>
        }
      />
      {error && <Alert>{error}</Alert>}
      {showForm && (
        <form className="access-form section-block" onSubmit={create}>
          <label>
            {t("carousels.form.client")}
            <select name="client_id" required>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>{client.name}</option>
              ))}
            </select>
          </label>
          <label>
            {t("carousels.form.title")}
            <input name="title" required minLength={2} />
          </label>
          <label>
            {t("carousels.form.brief")}
            <textarea name="brief" rows={4} />
          </label>
          <label>
            {t("carousels.form.language")}
            <select name="language" defaultValue="es">
              <option value="es">ES</option>
              <option value="en">EN</option>
            </select>
          </label>
          <label>
            {t("carousels.form.slides")}
            <input name="slide_count" type="number" min={3} max={12} defaultValue={8} />
          </label>
          <label className="checkbox-row">
            <input name="with_images" type="checkbox" defaultChecked />
            {t("carousels.form.withImages")}
          </label>
          <button className="button primary" disabled={busy}>
            {busy && <LoaderCircle className="spin" size={16} />}
            {t("carousels.form.create")}
          </button>
        </form>
      )}
      {!items.length ? (
        <EmptyState icon={<Images />} title={t("carousels.list.empty")} description={t("carousels.list.emptyHint")} />
      ) : (
        <div className="card-list">
          {items.map((item) => (
            <Link key={item.id} href={`/carousels/${item.id}`} className="list-card">
              <strong>{item.title}</strong>
              <small>{statusLabel(item.status)} · {item.slide_count} slides</small>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

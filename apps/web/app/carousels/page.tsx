"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRight, Images, LoaderCircle, Plus, Search } from "lucide-react";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { CarouselImageCostAlert } from "@/components/carousel-image-cost-alert";
import { FormatPlaybookFields, type FormatPlaybookValue } from "@/components/format-playbook-fields";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Alert, EmptyState, PageHead } from "@/components/ui";
import type { Carousel, Client } from "@/types";

function formatUpdated(iso: string) {
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function CarouselStatusPill({
  status,
  generating,
  label,
  generatingLabel,
}: {
  status: string;
  generating?: boolean;
  label: string;
  generatingLabel: string;
}) {
  if (generating) {
    return <span className="pill carousel-pill generating">{generatingLabel}</span>;
  }
  return <span className={`pill carousel-pill status-${status}`}>{label}</span>;
}

export default function CarouselsPage() {
  const t = useT();
  const [items, setItems] = useState<Carousel[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [withImages, setWithImages] = useState(true);
  const [slideCount, setSlideCount] = useState(7);
  const [playbook, setPlaybook] = useState<FormatPlaybookValue>({
    contentGoal: "loyalty",
    ctaInstruction: "",
    hookStructure: true,
  });

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

  const clientById = useMemo(
    () => Object.fromEntries(clients.map((client) => [client.id, client.name])),
    [clients],
  );

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => {
      const clientName = clientById[item.client_id] || "";
      return `${item.title} ${item.brief} ${clientName} ${item.status}`.toLowerCase().includes(q);
    });
  }, [items, search, clientById]);

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
          slide_count: Number(data.get("slide_count") || 7),
          with_images: withImages,
          interpret_prompt: data.get("interpret_prompt") === "on",
          content_goal: playbook.contentGoal,
          cta_instruction: playbook.ctaInstruction.trim(),
          hook_structure: playbook.hookStructure,
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
    return t(`carousels.status.${status}` as "carousels.status.draft");
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
            <input
              name="slide_count"
              type="number"
              min={3}
              max={12}
              value={slideCount}
              onChange={(event) => setSlideCount(Number(event.target.value) || 7)}
            />
          </label>
          <FormatPlaybookFields value={playbook} onChange={setPlaybook} showSlidesHint />
          <label className="switch-row">
            <span>
              <strong>{t("carousels.form.interpretPrompt")}</strong>
              <small>{t("carousels.form.interpretPromptHint")}</small>
            </span>
            <input name="interpret_prompt" type="checkbox" defaultChecked />
          </label>
          <label className="switch-row">
            <span>
              <strong>{t("carousels.form.withImages")}</strong>
              <small>{t("carousels.form.withImagesHint")}</small>
            </span>
            <input
              name="with_images"
              type="checkbox"
              checked={withImages}
              onChange={(event) => setWithImages(event.target.checked)}
            />
          </label>
          <CarouselImageCostAlert imageCount={withImages ? slideCount : 1} />
          {!withImages && <small>{t("carousels.cost.minImage")}</small>}
          <button className="button primary" disabled={busy}>
            {busy && <LoaderCircle className="spin" size={16} />}
            {t("carousels.form.create")}
          </button>
        </form>
      )}

      <div className="toolbar">
        <label className="search-box">
          <Search size={18} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("carousels.list.searchPlaceholder")}
          />
        </label>
        <span className="result-count">{t("carousels.list.resultCount", { count: visible.length })}</span>
      </div>

      {visible.length ? (
        <div className="table-shell">
          <table className="data-table carousel-table">
            <thead>
              <tr>
                <th>{t("carousels.list.colCarousel")}</th>
                <th>{t("carousels.list.colClient")}</th>
                <th>{t("carousels.list.colSlides")}</th>
                <th>{t("carousels.list.colStatus")}</th>
                <th>{t("carousels.list.colUpdated")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => {
                const thumb = item.slides.find((slide) => slide.image_url)?.image_url ?? item.slides[0]?.image_url;
                const imageCount = item.slides.filter((slide) => slide.image_url).length;
                return (
                  <tr key={item.id}>
                    <td>
                      <Link href={`/carousels/${item.id}`} className="entity-cell carousel-entity-cell">
                        <span className="carousel-table-thumb" aria-hidden>
                          {thumb ? (
                            <AuthenticatedImage src={thumb} alt="" />
                          ) : (
                            <span className="carousel-table-thumb-fallback">
                              <Images size={18} />
                            </span>
                          )}
                        </span>
                        <span>
                          <strong>{item.title}</strong>
                          <small>{item.brief?.trim() || t("carousels.list.noBrief")}</small>
                        </span>
                      </Link>
                    </td>
                    <td>{clientById[item.client_id] || t("carousels.list.unknownClient")}</td>
                    <td>
                      <span className="carousel-slides-meta">
                        {t("carousels.list.slidesCount", { count: item.slide_count })}
                        {imageCount > 0 && <small>{imageCount} img</small>}
                      </span>
                    </td>
                    <td>
                      <CarouselStatusPill
                        status={item.status}
                        generating={item.is_generating}
                        label={statusLabel(item.status)}
                        generatingLabel={t("carousels.list.generating")}
                      />
                    </td>
                    <td><time dateTime={item.updated_at}>{formatUpdated(item.updated_at)}</time></td>
                    <td>
                      <Link href={`/carousels/${item.id}`} className="row-arrow" aria-label={t("carousels.list.openAria", { title: item.title })}>
                        <ArrowRight size={17} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          icon={<Images />}
          title={search ? t("carousels.list.empty") : t("carousels.list.empty")}
          description={search ? t("carousels.list.emptyHint") : t("carousels.list.emptyHint")}
          action={!search && (
            <button className="button primary" type="button" onClick={() => setShowForm(true)}>
              <Plus size={16} /> {t("carousels.list.new")}
            </button>
          )}
        />
      )}
    </div>
  );
}

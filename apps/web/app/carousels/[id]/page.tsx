"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Alert, PageHead } from "@/components/ui";
import type { Carousel, CarouselSlide } from "@/types";

export default function CarouselDetailPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const [carousel, setCarousel] = useState<Carousel | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);

  async function load() {
    setCarousel(await api<Carousel>(`/carousels/${params.id}`));
  }

  useEffect(() => {
    load().catch((err) => setError(messageFrom(err)));
  }, [params.id]);

  async function run(path: string, body?: unknown) {
    setBusy(true);
    setError("");
    try {
      const updated = await api<Carousel | CarouselSlide>(path, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      if ("slides" in (updated as Carousel)) setCarousel(updated as Carousel);
      else await load();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveSlide(event: FormEvent<HTMLFormElement>, slide: CarouselSlide) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await api(`/carousels/${params.id}/slides/${slide.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          headline: data.get("headline"),
          body: data.get("body"),
          cta: data.get("cta"),
        }),
      });
      setEditing(null);
      await load();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function schedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const when = new Date(String(data.get("scheduled_at")));
    await run(`/carousels/${params.id}/schedule`, { scheduled_at: when.toISOString() });
  }

  if (!carousel) return <div className="page"><p>{t("common.loading")}</p></div>;

  return (
    <div className="page">
      <PageHead
        eyebrow={t("carousels.page.eyebrow")}
        title={carousel.title}
        description={carousel.brief || t("carousels.page.description")}
        action={
          <div className="header-actions">
            <button className="button secondary" disabled={busy} onClick={() => run(`/carousels/${params.id}/generate`)}>
              {busy && <LoaderCircle className="spin" size={16} />}
              {t("carousels.detail.regenerate")}
            </button>
            {carousel.status === "draft" && (
              <button className="button primary" disabled={busy} onClick={() => run(`/carousels/${params.id}/submit-review`)}>
                {t("carousels.detail.submitReview")}
              </button>
            )}
          </div>
        }
      />
      {error && <Alert>{error}</Alert>}
      <p><strong>{t("carousels.list.status")}:</strong> {t(`carousels.status.${carousel.status}` as "carousels.status.draft")}</p>
      <p><strong>{t("carousels.detail.caption")}:</strong> {carousel.caption || "—"}</p>
      {carousel.publish_error && <Alert type="info">{carousel.publish_error}</Alert>}

      <div className="card-list">
        {carousel.slides.map((slide) => (
          <article key={slide.id} className="list-card">
            <small>#{slide.position} · {t(`carousels.slideStatus.${slide.agency_status}` as "carousels.slideStatus.pending")}</small>
            {editing === slide.id ? (
              <form className="access-form" onSubmit={(e) => saveSlide(e, slide)}>
                <label>{t("carousels.form.title")}<input name="headline" defaultValue={slide.headline} /></label>
                <label>{t("carousels.form.brief")}<textarea name="body" rows={3} defaultValue={slide.body} /></label>
                <label>CTA<input name="cta" defaultValue={slide.cta} /></label>
                <button className="button primary" disabled={busy}>{t("carousels.detail.saveSlide")}</button>
              </form>
            ) : (
              <>
                <strong>{slide.headline}</strong>
                <p>{slide.body}</p>
                {slide.cta && <em>{slide.cta}</em>}
                {slide.image_url && <img src={slide.image_url} alt="" style={{ maxWidth: "100%", borderRadius: 12, marginTop: 12 }} />}
              </>
            )}
            {carousel.status === "draft" && (
              <div className="header-actions" style={{ marginTop: 12 }}>
                <button className="button ghost" type="button" onClick={() => setEditing(slide.id)}>{t("carousels.detail.edit")}</button>
                <button className="button secondary" type="button" disabled={busy} onClick={() => run(`/carousels/${params.id}/slides/${slide.id}/agency-approve`)}>
                  {t("carousels.detail.agencyApprove")}
                </button>
                <button className="button danger" type="button" disabled={busy} onClick={() => run(`/carousels/${params.id}/slides/${slide.id}/agency-reject`)}>
                  {t("carousels.detail.agencyReject")}
                </button>
              </div>
            )}
          </article>
        ))}
      </div>

      {carousel.status === "approved" && (
        <form className="access-form section-block" onSubmit={schedule}>
          <p>{t("carousels.detail.scheduleHint")}</p>
          <label>
            {t("carousels.detail.schedule")}
            <input name="scheduled_at" type="datetime-local" required />
          </label>
          <button className="button primary" disabled={busy}>{t("carousels.detail.schedule")}</button>
        </form>
      )}
    </div>
  );
}

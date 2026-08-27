"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Alert } from "@/components/ui";
import { CarouselSlidePreview } from "@/components/carousel-slide-preview";
import type { Carousel } from "@/types";

export default function PortalCarouselsPage() {
  const t = useT();
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [items, setItems] = useState<Carousel[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setItems(await api<Carousel[]>(`/portal/${slug}/carousels`));
  }

  useEffect(() => {
    load().catch((err) => setError(messageFrom(err)));
  }, [slug]);

  async function act(path: string) {
    setBusy(true);
    setError("");
    try {
      await api(path, { method: "POST" });
      await load();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page" style={{ maxWidth: 960, margin: "0 auto", padding: 24 }}>
      <h1>{t("carousels.portal.title")}</h1>
      {error && <Alert>{error}</Alert>}
      {!items.length && <p>{t("carousels.portal.empty")}</p>}
      {items.map((carousel) => (
        <section key={carousel.id} className="section-block" style={{ marginTop: 24 }}>
          <h2>{carousel.title}</h2>
          <p>{t(`carousels.status.${carousel.status}` as "carousels.status.in_review")}</p>
          {carousel.brief && <p className="carousel-brief-banner">{carousel.brief}</p>}
          <div className="card-list">
            {carousel.slides.map((slide) => (
              <article key={slide.id} className="list-card" style={{ marginTop: 12 }}>
                <small>#{slide.position} · {t(`carousels.slideStatus.${slide.client_status}` as "carousels.slideStatus.pending")}</small>
                <div className="carousel-slide-layout">
                  <CarouselSlidePreview
                    position={slide.position}
                    total={carousel.slides.length}
                    headline={slide.headline}
                    body={slide.body}
                    cta={slide.cta}
                    imageUrl={slide.image_url}
                    layout={slide.layout_json}
                    emptyLabel={t("carousels.portal.previewEmpty")}
                  />
                  <div>
                    <strong>{slide.headline}</strong>
                    <p>{slide.body}</p>
                    {slide.cta && <em>{slide.cta}</em>}
                    {carousel.status === "in_review" && (
                      <div className="header-actions" style={{ marginTop: 12 }}>
                        <button className="button secondary" disabled={busy} type="button" onClick={() => act(`/portal/${slug}/carousels/${carousel.id}/slides/${slide.id}/approve`)}>
                          {t("carousels.portal.approveSlide")}
                        </button>
                        <button className="button danger" disabled={busy} type="button" onClick={() => act(`/portal/${slug}/carousels/${carousel.id}/slides/${slide.id}/reject`)}>
                          {t("carousels.portal.rejectSlide")}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
          {carousel.status === "in_review" && (
            <div className="header-actions" style={{ marginTop: 16 }}>
              <button className="button primary" disabled={busy} type="button" onClick={() => act(`/portal/${slug}/carousels/${carousel.id}/approve-set`)}>
                {t("carousels.portal.approveSet")}
              </button>
              <button className="button danger" disabled={busy} type="button" onClick={() => act(`/portal/${slug}/carousels/${carousel.id}/reject-set`)}>
                {t("carousels.portal.rejectSet")}
              </button>
            </div>
          )}
        </section>
      ))}
    </main>
  );
}

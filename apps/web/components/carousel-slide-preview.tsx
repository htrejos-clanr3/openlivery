"use client";

import { ReactNode, useEffect, useState } from "react";
import { AuthenticatedImage } from "@/components/authenticated-image";

type CarouselSlidePreviewProps = {
  position: number;
  total: number;
  headline: string;
  body: string;
  cta?: string;
  caption?: string;
  imageUrl?: string | null;
  layout?: Record<string, unknown> | null;
  username?: string;
  emptyLabel?: string;
  compact?: boolean;
  actions?: ReactNode;
};

function colorOf(layout: Record<string, unknown> | null | undefined, key: string, fallback: string) {
  const value = layout?.[key];
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function CarouselSlidePreview({
  position,
  total,
  headline,
  body,
  cta,
  caption,
  imageUrl,
  layout,
  username = "brand",
  emptyLabel = "No image yet — preview uses brand colors",
  compact = false,
  actions,
}: CarouselSlidePreviewProps) {
  const primary = colorOf(layout, "primary", "#075985");
  const secondary = colorOf(layout, "secondary", "#0f172a");
  const font = typeof layout?.font === "string" && layout.font ? layout.font : "inherit";
  const [imageFailed, setImageFailed] = useState(false);
  const handle = username.replace(/^@/, "") || "brand";

  useEffect(() => {
    setImageFailed(false);
  }, [imageUrl]);

  const showImage = Boolean(imageUrl) && !imageFailed;
  const hasCopy = Boolean(headline || body || cta);

  return (
    <div className={`carousel-preview ${compact ? "compact" : ""}`}>
      <div className="carousel-preview-phone">
        <div className="carousel-preview-head">
          <span className="ig-avatar" aria-hidden />
          <strong>@{handle}</strong>
          <span className="carousel-preview-dots" aria-hidden>···</span>
        </div>
        <div
          className="carousel-preview-frame"
          style={{
            background: showImage
              ? "#0f172a"
              : `linear-gradient(160deg, ${primary} 0%, ${secondary} 100%)`,
            fontFamily: font,
          }}
        >
          {imageUrl ? (
            <AuthenticatedImage
              src={imageUrl}
              alt=""
              className="carousel-preview-bg"
              onError={() => setImageFailed(true)}
            />
          ) : null}
          {!showImage ? (
            <div className="carousel-preview-overlay">
              {hasCopy ? (
                compact ? (
                  headline ? <h3>{headline}</h3> : null
                ) : (
                  <>
                    {headline ? <h3>{headline}</h3> : null}
                    {body ? <p>{body}</p> : null}
                    {cta ? <span className="carousel-preview-cta-chip">{cta}</span> : null}
                  </>
                )
              ) : (
                <p className="carousel-preview-empty">{emptyLabel}</p>
              )}
            </div>
          ) : null}
          <span className="carousel-preview-count">
            {position}/{total}
          </span>
        </div>
        <div className="carousel-preview-meta">
          <div className="carousel-preview-pips" aria-hidden>
            {Array.from({ length: Math.min(total, 10) }, (_, i) => (
              <i key={i} className={i + 1 === position ? "active" : ""} />
            ))}
          </div>
          {hasCopy && (showImage || compact) ? (
            <div className="carousel-preview-copy">
              {headline ? <strong>{headline}</strong> : null}
              {body ? <p>{body}</p> : null}
              {cta ? <span className="carousel-preview-cta-line">{cta}</span> : null}
            </div>
          ) : null}
          {caption && !compact ? (
            <p className="carousel-preview-caption-line">
              <strong>@{handle}</strong> {caption}
            </p>
          ) : null}
        </div>
        {actions ? <div className="carousel-preview-under-image">{actions}</div> : null}
      </div>
    </div>
  );
}

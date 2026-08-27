"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Alert } from "@/components/ui";
import type { ImageCostQuote } from "@/types";

function money(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return `$${n.toFixed(n >= 1 ? 2 : 2)}`;
}

export function CarouselImageCostAlert({
  imageCount,
}: {
  imageCount: number;
}) {
  const t = useT();
  const count = Math.max(1, Math.min(imageCount || 1, 12));
  const [quote, setQuote] = useState<ImageCostQuote | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    setQuote(null);
    api<ImageCostQuote>(`/carousels/image-quote?count=${count}`)
      .then((data) => {
        if (!cancelled) setQuote(data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [count]);

  if (failed) {
    return (
      <Alert type="info">
        <span>
          <strong>{t("carousels.cost.title")}</strong> {t("carousels.cost.unknown")}
        </span>
      </Alert>
    );
  }

  if (!quote) {
    return (
      <Alert type="info">
        <span>
          <strong>{t("carousels.cost.title")}</strong> {t("carousels.cost.loading")}
        </span>
      </Alert>
    );
  }

  if (!quote.billable) {
    return (
      <Alert type="info">
        <span>
          <strong>{t("carousels.cost.title")}</strong>{" "}
          {t("carousels.cost.local", {
            provider: quote.provider,
            model: quote.model,
            count: String(quote.image_count),
          })}
        </span>
      </Alert>
    );
  }

  if (quote.usd_per_image == null || quote.usd_typical == null) {
    return (
      <Alert type="info">
        <span>
          <strong>{t("carousels.cost.title")}</strong> {t("carousels.cost.unknown")} {quote.note}
        </span>
      </Alert>
    );
  }

  return (
    <Alert type="warning">
      <span>
        <strong>{t("carousels.cost.title")}</strong>{" "}
        {t("carousels.cost.openai", {
          model: quote.model,
          size: quote.size,
          perImage: money(quote.usd_per_image),
          count: String(quote.image_count),
          typical: money(quote.usd_typical),
        })}{" "}
        {quote.fallback_model && quote.usd_per_image_fallback != null
          ? t("carousels.cost.openaiFallback", {
              fallback: quote.fallback_model,
              fallbackEach: money(quote.usd_per_image_fallback),
              worst: money(quote.usd_if_fallback),
            })
          : null}{" "}
        {t("carousels.cost.disclaimer")}
        {!quote.available ? ` ${t("carousels.cost.notReady")}` : null}
      </span>
    </Alert>
  );
}

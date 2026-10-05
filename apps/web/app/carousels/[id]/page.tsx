"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Check, LoaderCircle, X } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useCarouselGeneration } from "@/lib/carousel-generation-context";
import { useT } from "@/lib/i18n";
import { Alert, Modal, PageHead } from "@/components/ui";
import { CarouselSlidePreview } from "@/components/carousel-slide-preview";
import { CarouselImageCostAlert } from "@/components/carousel-image-cost-alert";
import { FileDropzone } from "@/components/file-dropzone";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { FormatPlaybookFields, type FormatPlaybookValue } from "@/components/format-playbook-fields";
import type { Carousel, CarouselSlide } from "@/types";

export default function CarouselDetailPage() {
  const t = useT();
  const { register, unregister } = useCarouselGeneration();
  const abortRef = useRef<AbortController | null>(null);
  const params = useParams<{ id: string }>();
  const [carousel, setCarousel] = useState<Carousel | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ headline: "", body: "", cta: "", imagePrompt: "" });
  const [interpretPrompt, setInterpretPrompt] = useState(true);
  const [playbook, setPlaybook] = useState<FormatPlaybookValue>({
    contentGoal: "loyalty",
    ctaInstruction: "",
    hookStructure: true,
  });
  const [withImages, setWithImages] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatingSeconds, setGeneratingSeconds] = useState(0);
  const [regenAsk, setRegenAsk] = useState(false);

  async function load() {
    const data = await api<Carousel>(`/carousels/${params.id}`);
    setCarousel(data);
    setInterpretPrompt(data.interpret_prompt !== false);
    setPlaybook({
      contentGoal: data.content_goal === "reach" || data.content_goal === "convert" ? data.content_goal : "loyalty",
      ctaInstruction: data.cta_instruction || "",
      hookStructure: data.hook_structure !== false,
    });
    setSelectedId((current) => {
      if (current && data.slides.some((s) => s.id === current)) return current;
      return data.slides[0]?.id ?? null;
    });
  }

  useEffect(() => {
    load().catch((err) => setError(messageFrom(err)));
  }, [params.id]);

  const selected = useMemo(
    () => carousel?.slides.find((s) => s.id === selectedId) ?? carousel?.slides[0] ?? null,
    [carousel, selectedId],
  );

  useEffect(() => {
    if (!selected) return;
    setDraft({
      headline: selected.headline || "",
      body: selected.body || "",
      cta: selected.cta || "",
      imagePrompt: selected.image_prompt || "",
    });
    setEditing(false);
  }, [selected?.id, selected?.headline, selected?.body, selected?.cta, selected?.image_url, selected?.image_prompt]);

  useEffect(() => {
    if (!generating) {
      setGeneratingSeconds(0);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      setGeneratingSeconds(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [generating]);

  async function run(path: string, body?: unknown) {
    const isGenerate = path.includes("/generate");
    const isSlideGenerate = isGenerate && path.includes("/slides/");
    setBusy(true);
    setGenerating(isGenerate);
    setError("");
    setInfo("");
    const controller = isGenerate ? new AbortController() : null;
    if (controller) abortRef.current = controller;
    if (isGenerate && carousel) {
      register({
        carouselId: params.id,
        clientId: carousel.client_id,
        title: isSlideGenerate
          ? `${carousel.title} · #${selected?.position ?? "?"}`
          : carousel.title,
        startedAt: Date.now(),
        abort: () => controller?.abort(),
      });
    }
    try {
      if (isGenerate) {
        setInfo(
          isSlideGenerate
            ? t("carousels.detail.generatingSlideHint")
            : t("carousels.detail.generatingHint"),
        );
      }
      const updated = await api<Carousel | CarouselSlide>(path, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
        timeoutMs: isGenerate ? (isSlideGenerate ? 180_000 : 600_000) : undefined,
        signal: controller?.signal,
      });
      if ("slides" in (updated as Carousel)) {
        const next = updated as Carousel;
        setCarousel(next);
        setInterpretPrompt(next.interpret_prompt !== false);
        if (next.generation_notes?.length) {
          setInfo(next.generation_notes.join(" "));
        } else {
          setInfo("");
        }
      } else await load();
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      const msg = messageFrom(err);
      setError(
        aborted
          ? t("carousels.generation.cancelled")
          : err instanceof DOMException && err.name === "TimeoutError"
            ? `${msg} — ${t("carousels.detail.generatingHint")}`
            : msg,
      );
      setInfo("");
    } finally {
      if (isGenerate) unregister(params.id);
      abortRef.current = null;
      setBusy(false);
      setGenerating(false);
    }
  }

  async function saveSlide(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !carousel) return;
    setBusy(true);
    setError("");
    try {
      await api(`/carousels/${params.id}/slides/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          headline: draft.headline,
          body: draft.body,
          cta: draft.cta,
          image_prompt: draft.imagePrompt,
        }),
      });
      setEditing(false);
      await load();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveImagePromptOnly() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await api(`/carousels/${params.id}/slides/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({ image_prompt: draft.imagePrompt }),
      });
      await load();
      setInfo(t("carousels.detail.saveImagePrompt"));
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function uploadProduct(file: File) {
    if (!selected) return;
    setBusy(true);
    setError("");
    const data = new FormData();
    data.append("file", file);
    try {
      await api(`/carousels/${params.id}/slides/${selected.id}/product-image`, {
        method: "POST",
        body: data,
      });
      await load();
      setInfo(t("carousels.detail.productPhotoReady"));
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function removeProduct() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await api(`/carousels/${params.id}/slides/${selected.id}/product-image`, { method: "DELETE" });
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

  function generateBody(includeApproved: boolean) {
    return {
      with_images: withImages,
      interpret_prompt: interpretPrompt,
      ensure_min_image: true,
      include_approved: includeApproved,
      content_goal: playbook.contentGoal,
      cta_instruction: playbook.ctaInstruction.trim(),
      hook_structure: playbook.hookStructure,
    };
  }

  if (!carousel) return <div className="page"><p>{t("common.loading")}</p></div>;

  const previewHeadline = editing ? draft.headline : selected?.headline || "";
  const previewBody = editing ? draft.body : selected?.body || "";
  const previewCta = editing ? draft.cta : selected?.cta || "";
  const total = carousel.slides.length || carousel.slide_count || 1;
  const approvedCount = carousel.slides.filter((slide) => slide.agency_status === "agency_ok").length;
  const allApproved = total > 0 && approvedCount === carousel.slides.length;
  const isDraft = carousel.status === "draft";

  return (
    <div className="page">
      <PageHead
        eyebrow={t("carousels.page.eyebrow")}
        title={carousel.title}
        description={carousel.brief || t("carousels.page.description")}
        action={
          <div className="header-actions">
            <Link className="button secondary" href={`/clients/${carousel.client_id}/channels/instagram`}>
              {t("carousels.detail.openInstagram")}
            </Link>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => {
                if (approvedCount > 0) {
                  setRegenAsk(true);
                  return;
                }
                run(`/carousels/${params.id}/generate`, generateBody(false));
              }}
            >
              {busy && <LoaderCircle className="spin" size={16} />}
              {t("carousels.detail.regenerate")}
            </button>
            {isDraft && carousel.slides.length > 0 ? (
              <>
                <button
                  className="button secondary"
                  type="button"
                  disabled={busy || allApproved}
                  onClick={() => run(`/carousels/${params.id}/agency-approve-set`)}
                >
                  {t("carousels.detail.agencyApproveAll")}
                </button>
                <button
                  className="button primary"
                  type="button"
                  disabled={busy || !allApproved}
                  onClick={() => run(`/carousels/${params.id}/submit-review`)}
                >
                  {t("carousels.detail.submitReview")}
                </button>
              </>
            ) : null}
          </div>
        }
      />
      {error && <Alert>{error}</Alert>}
      {info && (
        <Alert type="info">
          {info}
          {generating && generatingSeconds > 0 && (
            <> {t("carousels.detail.generatingElapsed", { seconds: generatingSeconds })}</>
          )}
        </Alert>
      )}
      <p><strong>{t("carousels.list.status")}:</strong> {t(`carousels.status.${carousel.status}` as "carousels.status.draft")}</p>
      <p><strong>{t("carousels.detail.caption")}:</strong> {carousel.caption || "—"}</p>
      {carousel.brief && (
        <div className="carousel-brief-banner">
          <strong>{t("carousels.detail.ideaBrief")}</strong>
          {carousel.brief}
        </div>
      )}
      <div className="carousel-options">
        <strong className="carousel-options-title">{t("carousels.detail.interpretMode")}</strong>
        <label className="switch-row">
          <span>
            <strong>{interpretPrompt ? t("carousels.detail.interpretOn") : t("carousels.detail.interpretOff")}</strong>
            <small>{t("carousels.form.interpretPromptHint")}</small>
          </span>
          <input
            type="checkbox"
            checked={interpretPrompt}
            onChange={(e) => setInterpretPrompt(e.target.checked)}
          />
        </label>
        <label className="switch-row">
          <span>
            <strong>{t("carousels.form.withImages")}</strong>
            <small>{t("carousels.form.withImagesHint")}</small>
          </span>
          <input type="checkbox" checked={withImages} onChange={(e) => setWithImages(e.target.checked)} />
        </label>
        <CarouselImageCostAlert imageCount={withImages ? total : 1} />
        {!withImages && <small>{t("carousels.cost.minImage")}</small>}
        <strong className="carousel-options-title">{t("carousels.detail.formatPlaybook")}</strong>
        <FormatPlaybookFields value={playbook} onChange={setPlaybook} showSlidesHint />
      </div>
      {carousel.ig_media_id && (
        <p><strong>{t("carousels.detail.igMediaId")}:</strong> {carousel.ig_media_id}</p>
      )}
      {carousel.publish_error && <Alert type="info">{carousel.publish_error}</Alert>}

      {carousel.generation_usage?.items?.length ? (
        <section className="carousel-usage" aria-label={t("carousels.detail.usageTitle")}>
          <div className="carousel-usage-head">
            <strong>{t("carousels.detail.usageTitle")}</strong>
            <small>{t("carousels.detail.usageHint")}</small>
          </div>
          <table className="carousel-usage-table">
            <tbody>
              {carousel.generation_usage.items.map((row, index) => (
                <tr key={`${row.kind}-${row.label || row.model}-${index}`}>
                  <th>
                    {row.kind === "copy" ? t("carousels.detail.usageCopy") : t("carousels.detail.usageImage")}
                    {row.label && row.label !== "copy" ? ` · ${row.label}` : null}
                    <span>
                      {row.provider} / {row.model}
                    </span>
                  </th>
                  <td>
                    {t("carousels.detail.usageTokens", {
                      input: row.input_tokens.toLocaleString(),
                      output: row.output_tokens.toLocaleString(),
                    })}
                  </td>
                  <td>${row.estimated_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th>{t("carousels.detail.usageTotal")}</th>
                <td>
                  {t("carousels.detail.usageTokens", {
                    input: carousel.generation_usage.input_tokens.toLocaleString(),
                    output: carousel.generation_usage.output_tokens.toLocaleString(),
                  })}
                </td>
                <td>${carousel.generation_usage.estimated_usd.toFixed(4)}</td>
              </tr>
            </tfoot>
          </table>
        </section>
      ) : null}

      {carousel.slides.length > 0 && (
        <div className="carousel-strip" role="list">
          {carousel.slides.map((slide) => {
            const ok = slide.agency_status === "agency_ok";
            const rejected = slide.agency_status === "rejected";
            return (
              <article
                key={slide.id}
                className={`carousel-strip-item ${slide.id === selected?.id ? "active" : ""} ${ok ? "is-ok" : ""} ${rejected ? "is-rejected" : ""}`}
                role="listitem"
                onClick={() => setSelectedId(slide.id)}
              >
                <small>
                  #{slide.position} · {t(`carousels.slideStatus.${slide.agency_status}` as "carousels.slideStatus.pending")}
                </small>
                <CarouselSlidePreview
                  compact
                  position={slide.position}
                  total={total}
                  headline={slide.headline}
                  body={slide.body}
                  cta={slide.cta}
                  imageUrl={slide.image_url}
                  layout={slide.layout_json}
                  emptyLabel={t("carousels.detail.previewEmpty")}
                  actions={
                    isDraft ? (
                      <div className="carousel-strip-actions">
                        <button
                          className="button secondary small"
                          type="button"
                          disabled={busy || ok}
                          onClick={(event) => {
                            event.stopPropagation();
                            run(`/carousels/${params.id}/slides/${slide.id}/agency-approve`);
                          }}
                        >
                          <Check size={14} /> {t("carousels.detail.agencyApprove")}
                        </button>
                        <button
                          className="button danger small"
                          type="button"
                          disabled={busy}
                          onClick={(event) => {
                            event.stopPropagation();
                            run(`/carousels/${params.id}/slides/${slide.id}/agency-reject`);
                          }}
                        >
                          <X size={14} /> {t("carousels.detail.agencyReject")}
                        </button>
                      </div>
                    ) : null
                  }
                />
              </article>
            );
          })}
        </div>
      )}

      {selected && (
        <article className="list-card">
          <small>
            #{selected.position} · {t(`carousels.slideStatus.${selected.agency_status}` as "carousels.slideStatus.pending")}
            {selected.image_url ? "" : ` · ${t("carousels.detail.noImageHint")}`}
          </small>
          <div className="carousel-slide-layout">
            <div className="carousel-slide-preview-col">
              <CarouselSlidePreview
                position={selected.position}
                total={total}
                headline={previewHeadline}
                body={previewBody}
                cta={previewCta}
                caption={carousel.caption}
                imageUrl={selected.image_url}
                layout={selected.layout_json}
                emptyLabel={t("carousels.detail.previewEmpty")}
                actions={
                  isDraft ? (
                    <div className="carousel-preview-actions">
                      <button
                        className="button secondary"
                        type="button"
                        disabled={busy || selected.agency_status === "agency_ok"}
                        onClick={() => run(`/carousels/${params.id}/slides/${selected.id}/agency-approve`)}
                      >
                        <Check size={15} /> {t("carousels.detail.agencyApprove")}
                      </button>
                      <button
                        className="button danger"
                        type="button"
                        disabled={busy}
                        onClick={() => run(`/carousels/${params.id}/slides/${selected.id}/agency-reject`)}
                      >
                        <X size={15} /> {t("carousels.detail.agencyReject")}
                      </button>
                    </div>
                  ) : null
                }
              />
            </div>
            <div className="carousel-slide-editor">
              <p className="field-help">{t("carousels.detail.previewHint")}</p>
              <p className={`carousel-image-status ${selected.image_url ? "ok" : "missing"}`}>
                {selected.image_url ? t("carousels.detail.hasImage") : t("carousels.detail.noImageYet")}
              </p>
              {selected.image_error ? (
                <Alert type="info">{t("carousels.detail.imageError")}: {selected.image_error}</Alert>
              ) : null}
              {editing || carousel.status === "draft" ? (
                <form className="access-form" onSubmit={saveSlide}>
                  <label>
                    {t("carousels.form.headline")}
                    <input
                      name="headline"
                      value={draft.headline}
                      onChange={(e) => {
                        setEditing(true);
                        setDraft((d) => ({ ...d, headline: e.target.value }));
                      }}
                    />
                  </label>
                  <label>
                    {t("carousels.form.body")}
                    <textarea
                      name="body"
                      rows={4}
                      value={draft.body}
                      onChange={(e) => {
                        setEditing(true);
                        setDraft((d) => ({ ...d, body: e.target.value }));
                      }}
                    />
                  </label>
                  <label>
                    CTA
                    <input
                      name="cta"
                      value={draft.cta}
                      onChange={(e) => {
                        setEditing(true);
                        setDraft((d) => ({ ...d, cta: e.target.value }));
                      }}
                    />
                  </label>
                  <div className="carousel-admin-prompt">
                    <strong>{t("carousels.detail.productPhoto")}</strong>
                    <small className="field-help">{t("carousels.detail.productPhotoHint")}</small>
                    {selected.product_image_url ? (
                      <div className="carousel-product-row">
                        <span className="carousel-product-thumb">
                          <AuthenticatedImage src={selected.product_image_url} alt="" />
                        </span>
                        <button className="button danger" type="button" disabled={busy} onClick={() => removeProduct()}>
                          {t("carousels.detail.productPhotoRemove")}
                        </button>
                      </div>
                    ) : (
                      <FileDropzone accept="image/png,image/jpeg,image/webp" disabled={busy} onFile={uploadProduct}>
                        <span>{t("carousels.detail.productPhotoUpload")}</span>
                      </FileDropzone>
                    )}
                    <label>
                      {t("carousels.detail.imagePromptAdmin")}
                      <textarea
                        name="image_prompt"
                        rows={6}
                        value={draft.imagePrompt}
                        placeholder={t("carousels.detail.imagePromptHint")}
                        onChange={(e) => {
                          setEditing(true);
                          setDraft((d) => ({ ...d, imagePrompt: e.target.value }));
                        }}
                      />
                    </label>
                    <small className="field-help">{t("carousels.detail.imagePromptHint")}</small>
                    <div className="header-actions" style={{ marginTop: 8 }}>
                      <button
                        className="button secondary"
                        type="button"
                        disabled={busy}
                        onClick={() => saveImagePromptOnly()}
                      >
                        {t("carousels.detail.saveImagePrompt")}
                      </button>
                      <button
                        className="button secondary"
                        type="button"
                        disabled={busy}
                        onClick={async () => {
                          setDraft((d) => ({ ...d, imagePrompt: "" }));
                          setBusy(true);
                          setError("");
                          try {
                            await api(`/carousels/${params.id}/slides/${selected.id}`, {
                              method: "PATCH",
                              body: JSON.stringify({ image_prompt: "" }),
                            });
                            await load();
                          } catch (err) {
                            setError(messageFrom(err));
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        {t("carousels.detail.resetImagePrompt")}
                      </button>
                    </div>
                  </div>
                  {carousel.status === "draft" && (
                    <button className="button primary" disabled={busy}>
                      {busy && !generating && <LoaderCircle className="spin" size={16} />}
                      {t("carousels.detail.saveSlide")}
                    </button>
                  )}
                </form>
              ) : (
                <>
                  <strong>{selected.headline}</strong>
                  <p>{selected.body}</p>
                  {selected.cta && <em>{selected.cta}</em>}
                  {selected.image_prompt ? (
                    <div className="carousel-admin-prompt readonly">
                      <strong>{t("carousels.detail.imagePromptAdmin")}</strong>
                      <pre>{selected.image_prompt}</pre>
                    </div>
                  ) : null}
                </>
              )}
              {carousel.status === "draft" && (
                <div className="header-actions" style={{ marginTop: 4 }}>
                  <button
                    className="button secondary"
                    type="button"
                    disabled={busy}
                    title={t("carousels.detail.regenerateSlideHint")}
                    onClick={() =>
                      run(`/carousels/${params.id}/slides/${selected.id}/generate`, {
                        with_images: withImages,
                        image_prompt: draft.imagePrompt || null,
                        regenerate_copy: true,
                      })
                    }
                  >
                    {busy && generating && <LoaderCircle className="spin" size={16} />}
                    {t("carousels.detail.regenerateSlide")}
                  </button>
                  <button
                    className="button secondary"
                    type="button"
                    disabled={busy}
                    title={t("carousels.detail.regenerateSlideHint")}
                    onClick={() =>
                      run(`/carousels/${params.id}/slides/${selected.id}/generate`, {
                        with_images: true,
                        image_prompt: draft.imagePrompt || null,
                        regenerate_copy: false,
                      })
                    }
                  >
                    {t("carousels.detail.regenerateImageOnly")}
                  </button>
                </div>
              )}
            </div>
          </div>
        </article>
      )}

      {(carousel.status === "approved" || carousel.status === "failed") && (
        <div className="access-form section-block">
          <p>{t("carousels.detail.scheduleHint")}</p>
          <div className="header-actions" style={{ marginBottom: 16 }}>
            <button
              className="button primary"
              type="button"
              disabled={busy}
              onClick={() => run(`/carousels/${params.id}/publish`)}
            >
              {busy && <LoaderCircle className="spin" size={16} />}
              {t("carousels.detail.publishNow")}
            </button>
          </div>
          <form onSubmit={schedule}>
            <label>
              {t("carousels.detail.schedule")}
              <input name="scheduled_at" type="datetime-local" required />
            </label>
            <button className="button secondary" disabled={busy}>{t("carousels.detail.schedule")}</button>
          </form>
        </div>
      )}
      <Modal
        open={regenAsk}
        title={t("carousels.detail.regenerateApprovedTitle")}
        description={t("carousels.detail.regenerateApprovedCopy", { count: approvedCount })}
        onClose={() => setRegenAsk(false)}
      >
        <div className="modal-actions">
          <button className="button ghost" type="button" onClick={() => setRegenAsk(false)}>
            {t("carousels.detail.regenerateApprovedCancel")}
          </button>
          <button
            className="button secondary"
            type="button"
            onClick={() => {
              setRegenAsk(false);
              run(`/carousels/${params.id}/generate`, generateBody(false));
            }}
          >
            {t("carousels.detail.regenerateApprovedKeep")}
          </button>
          <button
            className="button primary"
            type="button"
            onClick={() => {
              setRegenAsk(false);
              run(`/carousels/${params.id}/generate`, generateBody(true));
            }}
          >
            {t("carousels.detail.regenerateApprovedAll")}
          </button>
        </div>
      </Modal>
    </div>
  );
}

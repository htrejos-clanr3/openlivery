"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import {
  ArrowDown, ArrowLeft, ArrowUp, CheckCircle2, LoaderCircle, Sparkles, Trash2, Upload,
} from "lucide-react";
import { FileDropzone } from "@/components/file-dropzone";
import { FormatPlaybookFields, type FormatPlaybookValue } from "@/components/format-playbook-fields";
import { Alert } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { TIMEZONES } from "@/lib/timezones";
import type {
  Client,
  InstagramChannel,
  InstagramContentItem,
  InstagramGenerateResult,
  InstagramMediaAsset,
  InstagramPublication,
} from "@/types";

type ContentType = "IMAGE" | "CAROUSEL" | "REEL";
type MediaSlot = { id: string; file_name: string; mime_type: string; preview_url: string | null };
type AiSlide = { headline?: string; body?: string; cta?: string };

function ComposePageInner() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const contentIdParam = search.get("content");

  const [client, setClient] = useState<Client | null>(null);
  const [channel, setChannel] = useState<InstagramChannel | null>(null);
  const [contentId, setContentId] = useState<string | null>(contentIdParam);
  const [contentType, setContentType] = useState<ContentType>("IMAGE");
  const [title, setTitle] = useState("");
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [cta, setCta] = useState("");
  const [timezone, setTimezone] = useState("America/Bogota");
  const [scheduleAt, setScheduleAt] = useState("");
  const [media, setMedia] = useState<MediaSlot[]>([]);
  const [aiSlides, setAiSlides] = useState<AiSlide[]>([]);
  const [aiObjective, setAiObjective] = useState("");
  const [aiAudience, setAiAudience] = useState("");
  const [aiInstruction, setAiInstruction] = useState("");
  const [slideCount, setSlideCount] = useState(7);
  const [playbook, setPlaybook] = useState<FormatPlaybookValue>({
    contentGoal: "loyalty",
    ctaInstruction: "",
    hookStructure: true,
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [published, setPublished] = useState<InstagramPublication | null>(null);
  const [reviewedExact, setReviewedExact] = useState(false);
  const [publishAuthorized, setPublishAuthorized] = useState(false);

  function publishApprovalBody() {
    return { human_approved: publishAuthorized, reviewed_exact_content: reviewedExact };
  }

  function ensurePublishApproval() {
    if (!reviewedExact || !publishAuthorized) {
      setError(t("legal.publishBlocked"));
      return false;
    }
    return true;
  }

  useEffect(() => {
    (async () => {
      try {
        const [c, ch] = await Promise.all([
          api<Client>(`/clients/${id}`),
          api<InstagramChannel>(`/instagram/channels/${id}`),
        ]);
        setClient(c);
        setChannel(ch);
        if (contentIdParam) {
          const item = await api<InstagramContentItem>(`/instagram/channels/${id}/content/${contentIdParam}`);
          setContentId(item.id);
          setContentType((item.content_type as ContentType) || "IMAGE");
          setTitle(item.title || "");
          setCaption(item.caption || "");
          setHashtags(item.hashtags || "");
          setCta(item.cta || "");
          setTimezone(item.timezone || "America/Bogota");
          setMedia(
            item.media.map((m) => ({
              id: m.media_id,
              file_name: m.file_name || m.media_id,
              mime_type: m.mime_type || "",
              preview_url: m.preview_url,
            })),
          );
          const slides = (item.ai_meta?.slides as AiSlide[] | undefined) || [];
          setAiSlides(slides);
          const metaGoal = item.ai_meta?.content_goal;
          setPlaybook({
            contentGoal: metaGoal === "reach" || metaGoal === "convert" ? metaGoal : "loyalty",
            ctaInstruction: typeof item.ai_meta?.cta_instruction === "string" ? item.ai_meta.cta_instruction : "",
            hookStructure: item.ai_meta?.hook_structure !== false,
          });
          if (typeof item.ai_meta?.slide_count === "number") {
            setSlideCount(item.ai_meta.slide_count);
          }
        }
      } catch (err) {
        setError(messageFrom(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [id, contentIdParam]);

  async function uploadFile(file: File) {
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("file", file);
      const asset = await api<InstagramMediaAsset>(`/instagram/channels/${id}/media`, {
        method: "POST",
        body,
      });
      const slot: MediaSlot = {
        id: asset.id,
        file_name: asset.file_name,
        mime_type: asset.mime_type,
        preview_url: asset.preview_url,
      };
      setMedia((prev) => {
        if (contentType === "IMAGE" || contentType === "REEL") return [slot];
        return [...prev, slot].slice(0, 10);
      });
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  function moveMedia(index: number, dir: -1 | 1) {
    setMedia((prev) => {
      const next = [...prev];
      const target = index + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function removeMedia(index: number) {
    setMedia((prev) => prev.filter((_, i) => i !== index));
  }

  function validateMedia(): string | null {
    if (contentType === "CAROUSEL" && (media.length < 2 || media.length > 10)) {
      return t("instagram.compose.needCarousel");
    }
    if (contentType === "IMAGE" && media.length < 1) return t("instagram.compose.needMedia");
    if (contentType === "REEL") {
      if (media.length < 1) return t("instagram.compose.needVideo");
      if (!media[0].mime_type.startsWith("video/")) return t("instagram.compose.needVideo");
    }
    return null;
  }

  async function saveDraft(): Promise<InstagramContentItem | null> {
    if (contentId) {
      return api<InstagramContentItem>(`/instagram/channels/${id}/content/${contentId}`, {
        method: "PUT",
        body: JSON.stringify({
          title,
          caption,
          hashtags,
          cta,
          timezone,
          media_ids: media.map((m) => m.id),
          ai_meta: {
            slides: aiSlides,
            content_goal: playbook.contentGoal,
            cta_instruction: playbook.ctaInstruction.trim(),
            hook_structure: playbook.hookStructure,
            slide_count: slideCount,
          },
        }),
      });
    }
    const created = await api<InstagramContentItem>(`/instagram/channels/${id}/content`, {
      method: "POST",
      body: JSON.stringify({
        content_type: contentType,
        title,
        caption,
        hashtags,
        cta,
        timezone,
        media_ids: media.map((m) => m.id),
      }),
    });
    if (aiSlides.length) {
      return api<InstagramContentItem>(`/instagram/channels/${id}/content/${created.id}`, {
        method: "PUT",
        body: JSON.stringify({
          ai_meta: {
            slides: aiSlides,
            content_goal: playbook.contentGoal,
            cta_instruction: playbook.ctaInstruction.trim(),
            hook_structure: playbook.hookStructure,
            slide_count: slideCount,
          },
        }),
      });
    }
    return created;
  }

  async function onSaveDraft(event?: FormEvent) {
    event?.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const saved = await saveDraft();
      if (saved) {
        setContentId(saved.id);
        setInfo(t("instagram.compose.draftSaved"));
      }
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSchedule() {
    const mediaError = validateMedia();
    if (mediaError) {
      setError(mediaError);
      return;
    }
    if (!ensurePublishApproval()) return;
    if (!scheduleAt) {
      setError(t("instagram.compose.scheduleAt"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      const saved = await saveDraft();
      if (!saved) return;
      setContentId(saved.id);
      const pub = await api<InstagramPublication>(
        `/instagram/channels/${id}/content/${saved.id}/schedule`,
        {
          method: "POST",
          body: JSON.stringify({
            scheduled_at: new Date(scheduleAt).toISOString(),
            timezone,
            ...publishApprovalBody(),
          }),
        },
      );
      setPublished(pub);
      setInfo(t("instagram.compose.scheduledCopy"));
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function onPublish() {
    const mediaError = validateMedia();
    if (mediaError) {
      setError(mediaError);
      return;
    }
    if (!ensurePublishApproval()) return;
    setBusy(true);
    setError("");
    try {
      const saved = await saveDraft();
      if (!saved) return;
      setContentId(saved.id);
      const pub = await api<InstagramPublication>(
        `/instagram/channels/${id}/content/${saved.id}/publish`,
        { method: "POST", body: JSON.stringify(publishApprovalBody()) },
      );
      setPublished(pub);
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function onGenerate() {
    if (!aiObjective.trim()) {
      setError(t("instagram.compose.needObjective"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api<InstagramGenerateResult>(`/instagram/channels/${id}/generate`, {
        method: "POST",
        body: JSON.stringify({
          content_type: contentType,
          objective: aiObjective.trim(),
          audience: aiAudience.trim(),
          user_instruction: aiInstruction.trim(),
          slide_count: slideCount,
          language: "es",
          content_goal: playbook.contentGoal,
          cta_instruction: playbook.ctaInstruction.trim(),
          hook_structure: playbook.hookStructure,
        }),
      });
      if (result.title) setTitle(result.title);
      if (result.caption) setCaption(result.caption);
      if (result.cta) setCta(result.cta);
      if (result.hashtags?.length) setHashtags(result.hashtags.join(" "));
      if (result.slides?.length) setAiSlides(result.slides);
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading || !client) {
    return (
      <div className="page-loading">
        <LoaderCircle className="spin" /> {t("instagram.compose.loadingContent")}
      </div>
    );
  }

  if (published?.status === "PUBLISHED") {
    return (
      <div className="page wa-page ig-page">
        <Link href={`/clients/${id}/channels/instagram`} className="back-link">
          <ArrowLeft size={17} /> {t("instagram.compose.back")}
        </Link>
        <section className="wa-panel" style={{ marginTop: 24 }}>
          <div className="wa-panel-head">
            <span><CheckCircle2 size={19} /></span>
            <div>
              <h2>{t("instagram.compose.successTitle")}</h2>
              <p>{t("instagram.compose.successCopy")}</p>
            </div>
          </div>
          <div className="wa-actions">
            {published.provider_permalink && (
              <a className="button primary" href={published.provider_permalink} target="_blank" rel="noreferrer">
                {t("instagram.compose.successPermalink")}
              </a>
            )}
            <Link className="button secondary" href={`/clients/${id}/channels/instagram`}>
              {t("instagram.compose.successBack")}
            </Link>
          </div>
        </section>
      </div>
    );
  }

  if (published?.status === "QUEUED") {
    return (
      <div className="page wa-page ig-page">
        <Link href={`/clients/${id}/channels/instagram`} className="back-link">
          <ArrowLeft size={17} /> {t("instagram.compose.back")}
        </Link>
        <section className="wa-panel" style={{ marginTop: 24 }}>
          <div className="wa-panel-head">
            <span><CheckCircle2 size={19} /></span>
            <div>
              <h2>{t("instagram.compose.scheduledTitle")}</h2>
              <p>{t("instagram.compose.scheduledCopy")}</p>
            </div>
          </div>
          <div className="wa-actions">
            <Link className="button primary" href={`/clients/${id}/channels/instagram`}>
              {t("instagram.compose.successBack")}
            </Link>
          </div>
        </section>
      </div>
    );
  }

  const accept = contentType === "REEL" ? "video/*" : "image/*,video/*";
  const username = channel?.username || "username";

  return (
    <div className="page wa-page ig-page">
      <Link href={`/clients/${id}/channels/instagram`} className="back-link">
        <ArrowLeft size={17} /> {t("instagram.compose.back")}
      </Link>
      <header className="wa-header">
        <div className="wa-mark ig-mark"><Upload size={26} /></div>
        <div>
          <span>@{username}</span>
          <h1>{contentId ? t("instagram.compose.editTitle") : t("instagram.compose.title")}</h1>
          <p>{client.name}</p>
        </div>
      </header>
      {error && <Alert>{error}</Alert>}
      {info && <Alert type="success">{info}</Alert>}

      <div className="wa-layout">
        <main>
          <section className="wa-panel">
            <div className="wa-panel-head">
              <span><Upload size={19} /></span>
              <div>
                <h2>{t("instagram.compose.typeLabel")}</h2>
              </div>
            </div>
            <div className="ig-type-row">
              {([
                ["IMAGE", "instagram.compose.typeImage"],
                ["CAROUSEL", "instagram.compose.typeCarousel"],
                ["REEL", "instagram.compose.typeReel"],
              ] as const).map(([value, key]) => (
                <button
                  key={value}
                  type="button"
                  className={`button ${contentType === value ? "primary" : "secondary"}`}
                  onClick={() => {
                    setContentType(value);
                    if (value !== "CAROUSEL" && media.length > 1) setMedia((m) => m.slice(0, 1));
                  }}
                  disabled={busy || Boolean(contentId)}
                >
                  {t(key)}
                </button>
              ))}
            </div>
          </section>

          <section className="wa-panel">
            <div className="wa-panel-head">
              <span><Upload size={19} /></span>
              <div>
                <h2>{t("instagram.compose.uploadTitle")}</h2>
                <p>
                  {contentType === "REEL"
                    ? t("instagram.compose.uploadReelHint")
                    : t("instagram.compose.uploadHint")}
                </p>
              </div>
            </div>
            <FileDropzone onFile={uploadFile} accept={accept} disabled={busy} className="ig-dropzone">
              <Upload size={22} />
              <span>
                {contentType === "REEL"
                  ? t("instagram.compose.uploadReelHint")
                  : t("instagram.compose.uploadHint")}
              </span>
            </FileDropzone>
            {media.length > 0 && (
              <ul className="ig-media-list">
                {media.map((item, index) => (
                  <li key={item.id}>
                    {item.preview_url && item.mime_type.startsWith("image/") ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={item.preview_url} alt={item.file_name} />
                    ) : (
                      <div className="ig-media-fallback">{item.file_name}</div>
                    )}
                    <div className="ig-media-meta">
                      <strong>{item.file_name}</strong>
                      <small>{item.mime_type}</small>
                    </div>
                    {contentType === "CAROUSEL" && (
                      <div className="ig-media-actions">
                        <button type="button" className="icon-button" onClick={() => moveMedia(index, -1)} disabled={index === 0} aria-label={t("instagram.compose.moveUp")}>
                          <ArrowUp size={15} />
                        </button>
                        <button type="button" className="icon-button" onClick={() => moveMedia(index, 1)} disabled={index === media.length - 1} aria-label={t("instagram.compose.moveDown")}>
                          <ArrowDown size={15} />
                        </button>
                      </div>
                    )}
                    <button type="button" className="icon-button" onClick={() => removeMedia(index)} aria-label={t("instagram.compose.remove")}>
                      <Trash2 size={15} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="wa-panel">
            <form className="wa-cloud-form" onSubmit={onSaveDraft}>
              <label style={{ gridColumn: "1 / -1" }}>
                {t("instagram.compose.titleField")}
                <input value={title} onChange={(e) => setTitle(e.target.value)} />
              </label>
              <label style={{ gridColumn: "1 / -1" }}>
                {t("instagram.compose.caption")}
                <textarea rows={5} value={caption} onChange={(e) => setCaption(e.target.value)} />
              </label>
              <label>
                {t("instagram.compose.hashtags")}
                <input value={hashtags} onChange={(e) => setHashtags(e.target.value)} placeholder="#brand #launch" />
              </label>
              <label>
                {t("instagram.compose.cta")}
                <input value={cta} onChange={(e) => setCta(e.target.value)} />
              </label>
              <label>
                {t("instagram.compose.timezone")}
                <select value={timezone} onChange={(e) => setTimezone(e.target.value)}>
                  {TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </label>
              <label>
                {t("instagram.compose.scheduleAt")}
                <input type="datetime-local" value={scheduleAt} onChange={(e) => setScheduleAt(e.target.value)} />
              </label>
              <fieldset style={{ gridColumn: "1 / -1", border: "1px solid #eceef3", borderRadius: 12, padding: "12px 14px" }}>
                <legend>{t("legal.publishTitle")}</legend>
                <label>
                  <input type="checkbox" checked={reviewedExact} onChange={(e) => setReviewedExact(e.target.checked)} />
                  {" "}{t("legal.publishReview")}
                </label>
                <label>
                  <input type="checkbox" checked={publishAuthorized} onChange={(e) => setPublishAuthorized(e.target.checked)} />
                  {" "}{t("legal.publishAuthorize")}
                </label>
              </fieldset>
              <div className="wa-actions" style={{ gridColumn: "1 / -1" }}>
                <button className="button secondary" type="submit" disabled={busy}>
                  {busy ? <LoaderCircle className="spin" size={17} /> : null} {t("instagram.compose.saveDraft")}
                </button>
                <button className="button secondary" type="button" onClick={onSchedule} disabled={busy}>
                  {t("instagram.compose.schedule")}
                </button>
                <button className="button primary" type="button" onClick={onPublish} disabled={busy}>
                  {busy ? <LoaderCircle className="spin" size={17} /> : null} {t("instagram.compose.publishNow")}
                </button>
              </div>
            </form>
          </section>

          <section className="wa-panel">
            <div className="wa-panel-head">
              <span><Sparkles size={19} /></span>
              <div>
                <h2>{t("instagram.compose.aiTitle")}</h2>
              </div>
            </div>
            <div className="wa-cloud-form">
              <label style={{ gridColumn: "1 / -1" }}>
                {t("instagram.compose.aiObjective")}
                <input value={aiObjective} onChange={(e) => setAiObjective(e.target.value)} />
              </label>
              <label>
                {t("instagram.compose.aiAudience")}
                <input value={aiAudience} onChange={(e) => setAiAudience(e.target.value)} />
              </label>
              <label>
                {t("instagram.compose.aiSlides")}
                <input
                  type="number"
                  min={3}
                  max={10}
                  value={slideCount}
                  onChange={(e) => setSlideCount(Number(e.target.value) || 7)}
                  disabled={contentType !== "CAROUSEL"}
                />
              </label>
              <div style={{ gridColumn: "1 / -1" }}>
                <FormatPlaybookFields
                  variant="campaign"
                  value={playbook}
                  onChange={setPlaybook}
                  showSlidesHint={contentType === "CAROUSEL"}
                />
              </div>
              <label style={{ gridColumn: "1 / -1" }}>
                {t("instagram.compose.aiInstruction")}
                <textarea rows={3} value={aiInstruction} onChange={(e) => setAiInstruction(e.target.value)} />
              </label>
              <div className="wa-actions" style={{ gridColumn: "1 / -1" }}>
                <button className="button secondary" type="button" onClick={onGenerate} disabled={busy}>
                  {busy ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />} {t("instagram.compose.aiGenerate")}
                </button>
              </div>
            </div>
            {aiSlides.length > 0 && (
              <div className="ig-ai-slides">
                <p className="ig-muted">{t("instagram.compose.aiSlidesHint")}</p>
                {aiSlides.map((slide, index) => (
                  <div key={index} className="ig-ai-slide">
                    <strong>{t("instagram.compose.aiSlideHeadline")}:</strong> {slide.headline || "—"}
                    <br />
                    <strong>{t("instagram.compose.aiSlideBody")}:</strong> {slide.body || "—"}
                    {slide.cta ? (
                      <>
                        <br />
                        <strong>{t("instagram.compose.cta")}:</strong> {slide.cta}
                      </>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>

        <aside className="wa-side ig-preview">
          <h3>{t("instagram.compose.preview")}</h3>
          <div className="ig-preview-card">
            <div className="ig-preview-head">
              <span className="ig-avatar" />
              <strong>@{username}</strong>
            </div>
            <div className="ig-preview-media">
              {media[0]?.preview_url && media[0].mime_type.startsWith("image/") ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={media[0].preview_url} alt="" />
              ) : (
                <div className="ig-preview-empty">
                  {t("instagram.compose.previewMedia", { count: String(media.length) })}
                </div>
              )}
              {media.length > 1 && <span className="ig-preview-count">{media.length}</span>}
            </div>
            <p className="ig-preview-caption">
              <strong>@{username}</strong> {caption || "…"}
            </p>
            {hashtags && <p className="ig-preview-tags">{hashtags}</p>}
            {cta && <p className="ig-preview-cta">{cta}</p>}
          </div>
        </aside>
      </div>
    </div>
  );
}

export default function InstagramComposePage() {
  return (
    <Suspense fallback={<div className="page-loading"><LoaderCircle className="spin" /></div>}>
      <ComposePageInner />
    </Suspense>
  );
}

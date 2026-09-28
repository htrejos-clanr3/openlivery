"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { BookOpen, Check, ChevronLeft, ChevronRight, CircleHelp, Lightbulb, RotateCcw, TriangleAlert } from "lucide-react";
import { ChatPlayground } from "@/components/chat-playground";
import { ManualCaptureScene } from "@/components/manual-captures";
import { useT, type I18nKey } from "@/lib/i18n";
import {
  MANUAL_LESSONS,
  MANUAL_LESSON_IDS,
  type ManualLessonId,
  type ManualLessonMeta,
} from "@/lib/playground-manual-lessons";

const STORAGE_KEY = "openlivery.manual.v1";

const PRACTICE_KEYS: Record<ManualLessonMeta["hrefLabelKey"], I18nKey> = {
  openHome: "manual.openHome",
  openClients: "manual.openClients",
  openAgents: "manual.openAgents",
  openSettings: "manual.openSettings",
  openInbox: "manual.openInbox",
  openCarousels: "manual.openCarousels",
  openInstagram: "manual.openInstagram",
  openLinkedIn: "manual.openLinkedIn",
  openChannels: "manual.openChannels",
  practiceHere: "manual.practiceHere",
};

const PIN_KEYS = {
  a: "pinA",
  b: "pinB",
  c: "pinC",
} as const;

function isLessonId(value: string): value is ManualLessonId {
  return (MANUAL_LESSON_IDS as readonly string[]).includes(value);
}

function readDone(): ManualLessonId[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter(isLessonId) : [];
  } catch {
    return [];
  }
}

export function PlaygroundManual({
  lessonId,
  onLessonChange,
}: {
  lessonId: ManualLessonId;
  onLessonChange: (id: ManualLessonId) => void;
}) {
  const t = useT();
  const [done, setDone] = useState<ManualLessonId[]>([]);
  const [pin, setPin] = useState<string | null>(null);
  const [check, setCheck] = useState<"idle" | "ok" | "no">("idle");

  useEffect(() => {
    setDone(readDone());
  }, []);

  useEffect(() => {
    setPin(null);
    setCheck("idle");
  }, [lessonId]);

  const lesson = useMemo(
    () => MANUAL_LESSONS.find((item) => item.id === lessonId) ?? MANUAL_LESSONS[0],
    [lessonId],
  );
  const index = MANUAL_LESSONS.findIndex((item) => item.id === lesson.id);
  const prev = index > 0 ? MANUAL_LESSONS[index - 1] : null;
  const next = index < MANUAL_LESSONS.length - 1 ? MANUAL_LESSONS[index + 1] : null;
  const field = (name: string) => t(`manual.lessons.${lesson.id}.${name}` as I18nKey);

  const persist = useCallback((ids: ManualLessonId[]) => {
    setDone(ids);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  }, []);

  function markDone() {
    if (done.includes(lesson.id)) return;
    persist([...done, lesson.id]);
  }

  function onPin(id: string) {
    setPin(id);
    if (!lesson.correctPin) {
      setCheck("idle");
      return;
    }
    setCheck(id === lesson.correctPin ? "ok" : "no");
    if (id === lesson.correctPin) markDone();
  }

  return (
    <div className="manual-layout">
      <aside className="manual-toc" aria-label={t("manual.title")}>
        <div className="manual-toc-head">
          <BookOpen size={18} />
          <div>
            <strong>{t("manual.title")}</strong>
            <small>{t("manual.progress", { done: done.length, total: MANUAL_LESSONS.length })}</small>
          </div>
        </div>
        <div className="manual-progress" aria-hidden>
          <i style={{ width: `${Math.round((done.length / MANUAL_LESSONS.length) * 100)}%` }} />
        </div>
        <p className="manual-howto-label">{t("manual.howTo")}</p>
        <ol className="manual-howto">
          <li>{t("manual.how1")}</li>
          <li>{t("manual.how2")}</li>
          <li>{t("manual.how3")}</li>
        </ol>
        <ol className="manual-lessons">
          {MANUAL_LESSONS.map((item, i) => {
            const complete = done.includes(item.id);
            return (
              <li key={item.id}>
                <button
                  type="button"
                  className={item.id === lesson.id ? "active" : complete ? "done" : ""}
                  onClick={() => onLessonChange(item.id)}
                >
                  <span>{complete ? <Check size={13} /> : i + 1}</span>
                  <strong>{t(`manual.lessons.${item.id}.title` as I18nKey)}</strong>
                  <small>{t("manual.minutes", { count: item.minutes })}</small>
                </button>
              </li>
            );
          })}
        </ol>
        {done.length > 0 && (
          <button
            type="button"
            className="manual-reset"
            onClick={() => {
              persist([]);
              setCheck("idle");
            }}
          >
            <RotateCcw size={14} /> {t("manual.reset")}
          </button>
        )}
      </aside>

      <article className="manual-lesson">
        <header>
          <p className="manual-kicker">{t("manual.objective")}</p>
          <h2>{field("title")}</h2>
          <p className="manual-goal">{field("goal")}</p>
        </header>

        <section className="manual-why">
          <Lightbulb size={16} />
          <div>
            <strong>{t("manual.why")}</strong>
            <p>{field("why")}</p>
          </div>
        </section>

        <section className="manual-shot-wrap">
          <div className="manual-shot-label">{t("manual.shotCaption")}</div>
          <div className="manual-shot">
            <ManualCaptureScene kind={lesson.capture} />
            {lesson.pins.map((item, i) => (
              <button
                key={item.id}
                type="button"
                className={`manual-pin ${pin === item.id ? "on" : ""} ${check === "ok" && item.id === lesson.correctPin ? "ok" : ""}`}
                style={{ left: `${item.x}%`, top: `${item.y}%` }}
                onClick={() => onPin(item.id)}
                aria-label={`${i + 1}. ${field(PIN_KEYS[item.id as keyof typeof PIN_KEYS] || "pinA")}`}
              >
                {i + 1}
              </button>
            ))}
          </div>
          <p className="manual-look-hint">
            <CircleHelp size={14} /> {t("manual.lookHint")}
          </p>
          {pin && (
            <div className={`manual-pin-card ${check}`}>
              <strong>{t("manual.look")}</strong>
              <p>{field(PIN_KEYS[pin as keyof typeof PIN_KEYS] || "pinA")}</p>
            </div>
          )}
        </section>

        <section>
          <h3>{t("manual.do")}</h3>
          <ol className="manual-steps">
            <li>{field("step1")}</li>
            <li>{field("step2")}</li>
            <li>{field("step3")}</li>
          </ol>
        </section>

        <section className="manual-trap">
          <TriangleAlert size={16} />
          <div>
            <strong>{t("manual.trap")}</strong>
            <p>{field("trap")}</p>
          </div>
        </section>

        <section className="manual-check">
          <h3>{t("manual.check")}</h3>
          <p>{field("check")}</p>
          <small>{t("manual.checkHint")}</small>
          {check === "ok" && <p className="ok">{t("manual.checkOk")}</p>}
          {check === "no" && <p className="no">{t("manual.checkNo")}</p>}
        </section>

        {lesson.showLiveChat ? (
          <section className="manual-live">
            <h3>{t("manual.practiceHere")}</h3>
            <ChatPlayground />
          </section>
        ) : (
          <Link className={`button primary ${check === "ok" ? "ready" : ""}`} href={lesson.href}>
            {t(PRACTICE_KEYS[lesson.hrefLabelKey])}
          </Link>
        )}

        <footer className="manual-nav">
          <button type="button" className="button ghost" disabled={!prev} onClick={() => prev && onLessonChange(prev.id)}>
            <ChevronLeft size={16} /> {t("manual.prev")}
          </button>
          <button
            type="button"
            className="button secondary"
            onClick={markDone}
            disabled={done.includes(lesson.id)}
          >
            {done.includes(lesson.id) ? t("manual.marked") : t("manual.markDone")}
          </button>
          <button type="button" className={`button primary ${check === "ok" ? "ready" : ""}`} disabled={!next} onClick={() => next && onLessonChange(next.id)}>
            {check === "ok" && next ? t("manual.nextReady") : t("manual.next")} <ChevronRight size={16} />
          </button>
        </footer>
      </article>
    </div>
  );
}

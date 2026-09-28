"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, MessageSquareText } from "lucide-react";
import { PageHead } from "@/components/ui";
import { ChatPlayground } from "@/components/chat-playground";
import { PlaygroundManual } from "@/components/playground-manual";
import { useT } from "@/lib/i18n";
import { MANUAL_LESSON_IDS, type ManualLessonId } from "@/lib/playground-manual-lessons";

function isLessonId(value: string | null): value is ManualLessonId {
  return Boolean(value && (MANUAL_LESSON_IDS as readonly string[]).includes(value));
}

function PlaygroundInner() {
  const t = useT();
  const router = useRouter();
  const search = useSearchParams();
  const view = search.get("view") === "manual" ? "manual" : "chat";
  const lessonParam = search.get("lesson");
  const lessonId: ManualLessonId = isLessonId(lessonParam) ? lessonParam : "map";

  function go(nextView: "chat" | "manual", lesson?: ManualLessonId) {
    const params = new URLSearchParams();
    if (nextView === "manual") {
      params.set("view", "manual");
      params.set("lesson", lesson || lessonId);
    }
    const query = params.toString();
    router.replace(query ? `/playground?${query}` : "/playground", { scroll: false });
  }

  return (
    <div className={`page playground-page ${view === "manual" ? "manual-mode" : ""}`}>
      <PageHead
        eyebrow={view === "manual" ? t("manual.eyebrow") : t("playground.page.eyebrow")}
        title={view === "manual" ? t("manual.title") : t("playground.page.title")}
        description={view === "manual" ? t("manual.description") : t("playground.page.description")}
        action={
          <div className="playground-tabs" role="tablist" aria-label={t("playground.page.title")}>
            <button
              type="button"
              role="tab"
              aria-selected={view === "chat"}
              className={view === "chat" ? "on" : ""}
              onClick={() => go("chat")}
            >
              <MessageSquareText size={16} /> {t("manual.tabChat")}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={view === "manual"}
              className={view === "manual" ? "on" : ""}
              onClick={() => go("manual")}
            >
              <BookOpen size={16} /> {t("manual.tabManual")}
            </button>
          </div>
        }
      />
      {view === "manual" ? (
        <PlaygroundManual lessonId={lessonId} onLessonChange={(id) => go("manual", id)} />
      ) : (
        <ChatPlayground />
      )}
    </div>
  );
}

export default function PlaygroundPage() {
  return (
    <Suspense fallback={<div className="page playground-page" />}>
      <PlaygroundInner />
    </Suspense>
  );
}

"use client";

import { useT, type I18nKey } from "@/lib/i18n";

export type ContentGoal = "loyalty" | "reach" | "convert";

export type FormatPlaybookValue = {
  contentGoal: ContentGoal;
  ctaInstruction: string;
  hookStructure: boolean;
};

type Variant = "carousel" | "campaign";

const KEYS: Record<Variant, {
  title: I18nKey;
  hint: I18nKey;
  goal: I18nKey;
  loyalty: I18nKey;
  reach: I18nKey;
  convert: I18nKey;
  cta: I18nKey;
  ctaHint: I18nKey;
  ctaPlaceholder: I18nKey;
  hook: I18nKey;
  hookHint: I18nKey;
  slidesHint: I18nKey;
}> = {
  carousel: {
    title: "carousels.form.playbookTitle",
    hint: "carousels.form.playbookHint",
    goal: "carousels.form.contentGoal",
    loyalty: "carousels.form.goalLoyalty",
    reach: "carousels.form.goalReach",
    convert: "carousels.form.goalConvert",
    cta: "carousels.form.ctaInstruction",
    ctaHint: "carousels.form.ctaInstructionHint",
    ctaPlaceholder: "carousels.form.ctaInstructionPlaceholder",
    hook: "carousels.form.hookStructure",
    hookHint: "carousels.form.hookStructureHint",
    slidesHint: "carousels.form.slidesHint",
  },
  campaign: {
    title: "instagram.compose.playbookTitle",
    hint: "instagram.compose.playbookHint",
    goal: "instagram.compose.contentGoal",
    loyalty: "instagram.compose.goalLoyalty",
    reach: "instagram.compose.goalReach",
    convert: "instagram.compose.goalConvert",
    cta: "instagram.compose.ctaInstruction",
    ctaHint: "instagram.compose.ctaInstructionHint",
    ctaPlaceholder: "instagram.compose.ctaInstructionPlaceholder",
    hook: "instagram.compose.hookStructure",
    hookHint: "instagram.compose.hookStructureHint",
    slidesHint: "instagram.compose.slidesHint",
  },
};

export function FormatPlaybookFields({
  value,
  onChange,
  variant = "carousel",
  showSlidesHint = false,
}: {
  value: FormatPlaybookValue;
  onChange: (next: FormatPlaybookValue) => void;
  variant?: Variant;
  showSlidesHint?: boolean;
}) {
  const t = useT();
  const keys = KEYS[variant];
  return (
    <fieldset className="playbook-fields">
      <legend>
        <strong>{t(keys.title)}</strong>
        <small>{t(keys.hint)}</small>
      </legend>
      <label>
        {t(keys.goal)}
        <select
          value={value.contentGoal}
          onChange={(event) => onChange({ ...value, contentGoal: event.target.value as ContentGoal })}
        >
          <option value="loyalty">{t(keys.loyalty)}</option>
          <option value="reach">{t(keys.reach)}</option>
          <option value="convert">{t(keys.convert)}</option>
        </select>
      </label>
      <label>
        {t(keys.cta)}
        <input
          value={value.ctaInstruction}
          maxLength={180}
          placeholder={t(keys.ctaPlaceholder)}
          onChange={(event) => onChange({ ...value, ctaInstruction: event.target.value })}
        />
        <span className="field-help">{t(keys.ctaHint)}</span>
      </label>
      <label className="switch-row">
        <span>
          <strong>{t(keys.hook)}</strong>
          <small>{t(keys.hookHint)}</small>
        </span>
        <input
          type="checkbox"
          checked={value.hookStructure}
          onChange={(event) => onChange({ ...value, hookStructure: event.target.checked })}
        />
      </label>
      {showSlidesHint ? <small className="playbook-slides-hint">{t(keys.slidesHint)}</small> : null}
    </fieldset>
  );
}

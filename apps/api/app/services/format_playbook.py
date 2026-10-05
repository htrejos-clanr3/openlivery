"""Instagram format playbook: hook, second-slide enganche, one CTA."""

from __future__ import annotations

from typing import Any

CONTENT_GOALS = ("loyalty", "reach", "convert")
GOAL_COPY = {
    "loyalty": "Existing followers: depth, cases, saveable value. Not cold ads.",
    "reach": "New people: more general, shareable, discovery. Still one CTA.",
    "convert": "One action: book, buy, DM, comment a word. No stacked asks.",
}


def normalize_content_goal(value: str | None) -> str:
    raw = (value or "loyalty").strip().lower()
    return raw if raw in CONTENT_GOALS else "loyalty"


def apply_playbook_to_carousel(
    carousel: Any,
    *,
    content_goal: str | None = None,
    cta_instruction: str | None = None,
    hook_structure: bool | None = None,
) -> None:
    if content_goal is not None:
        carousel.content_goal = normalize_content_goal(content_goal)
    if cta_instruction is not None:
        carousel.cta_instruction = (cta_instruction or "").strip()[:180]
    if hook_structure is not None:
        carousel.hook_structure = bool(hook_structure)


def slide_role(position: int, total: int, *, hook_structure: bool) -> str:
    if position <= 1:
        return "hook"
    if hook_structure and position == 2 and total >= 3:
        return "enganche"
    if position >= total:
        return "cta"
    return "point"


def assign_slide_cta(
    item: dict[str, str],
    *,
    position: int,
    total: int,
    cta_instruction: str = "",
) -> dict[str, str]:
    """Only the last slide keeps a CTA. Optional instruction overrides the text."""
    forced = (cta_instruction or "").strip()[:180]
    if position >= total:
        item["cta"] = (forced or str(item.get("cta") or "").strip())[:180]
    else:
        item["cta"] = ""
    return item


def slide_role_hint(
    position: int,
    total: int,
    *,
    hook_structure: bool,
    cta_instruction: str = "",
) -> str:
    role = slide_role(position, total, hook_structure=hook_structure)
    if role == "hook":
        return "This is slide 1 (cover HOOK). Punchy, ≤8 words. Empty cta."
    if role == "enganche":
        return (
            "This is slide 2 (ENGANCHE). Equally punchy as the cover, adds context "
            "so someone who missed slide 1 still stays. Empty cta."
        )
    if role == "cta":
        hint = f"This is the LAST slide ({position}/{total}). The only CTA of the carousel."
        if cta_instruction.strip():
            hint += f' Use exactly: "{cta_instruction.strip()[:180]}"'
        return hint
    return f"Middle slide {position}/{total} — one scannable idea, empty cta."


def playbook_prompt(
    *,
    content_type: str = "CAROUSEL",
    content_goal: str = "loyalty",
    cta_instruction: str = "",
    hook_structure: bool = True,
    slide_count: int = 7,
) -> str:
    goal = normalize_content_goal(content_goal)
    kind = (content_type or "CAROUSEL").upper()
    cta = (cta_instruction or "").strip()[:180]
    lines = [
        "Instagram format playbook (must follow):",
        f"- Goal: {goal}. {GOAL_COPY[goal]}",
        "- Exactly ONE call to action for the whole piece. Never ask for likes. "
        "Prefer comment / save / DM / visit profile. Action doable in ~5 seconds. "
        "Never stack CTAs (no 'comment, save and follow').",
        "- Copy lives in headline/body/cta fields. Do not paint headlines, slogans, or CTAs in image_scene.",
    ]
    if cta:
        lines.append(f'- The only CTA text is exactly: "{cta}"')
    if kind == "CAROUSEL":
        lines.append(f"- Use {slide_count} slides. 5–7 is ideal; people drop off after slide 7–8.")
        if hook_structure:
            lines.append(
                "- Slide 1 = cover HOOK (punchy, ≤8 words). "
                "Slide 2 = ENGANCHE: equally punchy, more context. "
                "Middle slides = one scannable idea each, empty cta. "
                "Last slide = the only CTA."
            )
        else:
            lines.append("- Slide 1 hook; last slide CTA; middle slides one idea each; empty cta except last.")
    elif kind == "REEL":
        lines.append(
            "- Start in the first 0.5s (no pause). Script about 30 seconds max. "
            "Hook, one useful point, one CTA. Cover title sits in the center of the thumbnail."
        )
    elif kind == "IMAGE":
        lines.append("- One saveable or shareable idea. One CTA.")
    else:
        lines.append("- One CTA. Keep it scannable.")
    return "\n".join(lines)

"use client";

import { FormEvent, KeyboardEvent, UIEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BadgeCheck, FlaskConical, Globe, Inbox as InboxIcon, LoaderCircle, MessageCircle, Search, UserRound, Zap } from "lucide-react";
import { PageHead } from "@/components/ui";
import { useToast } from "@/components/toast";
import { api, messageFrom } from "@/lib/api";
import { formatWhen, isNearBottom, isSameOpenThread } from "@/lib/datetime";
import { useLanguage, useT } from "@/lib/i18n";
import type { AgencyMember, Agent, CannedReply, Conversation, ConversationInbox, User } from "@/types";

const LIMIT = 30;
const POLL_MS = 8000;
const LABELS = ["urgent", "waiting", "follow_up"] as const;
type LabelKey = (typeof LABELS)[number];
type Tab = "all" | "mine" | "unread" | "human" | "ai";

function initials(name: string) {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("") || "?";
}

export default function InboxPage() {
  const t = useT();
  const { lang } = useLanguage();
  const toast = useToast();
  const [me, setMe] = useState<User | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [members, setMembers] = useState<AgencyMember[]>([]);
  const [canned, setCanned] = useState<CannedReply[]>([]);
  const [items, setItems] = useState<ConversationInbox[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [agentId, setAgentId] = useState("");
  const [channel, setChannel] = useState("");
  const [tab, setTab] = useState<Tab>("all");
  const [labelFilter, setLabelFilter] = useState<LabelKey | "">("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [cannedOpen, setCannedOpen] = useState(false);
  const [cannedIndex, setCannedIndex] = useState(0);

  useEffect(() => {
    api<User>("/auth/me").then(setMe).catch(() => {});
    api<Agent[]>("/agents").then(setAgents).catch(() => {});
    api<AgencyMember[]>("/agency/members").then(setMembers).catch(() => {});
    api<CannedReply[]>("/conversations/canned").then(setCanned).catch(() => {});
  }, []);
  useEffect(() => { const id = setTimeout(() => setSearch(searchInput), 300); return () => clearTimeout(id); }, [searchInput]);

  const channelLabel = (value: string) => {
    if (value === "playground") return t("inbox.channelPlayground");
    if (value === "whatsapp") return t("inbox.channelWhatsapp");
    if (value === "whatsapp_cloud") return t("inbox.channelWhatsappCloud");
    if (value === "widget") return t("inbox.channelWidget");
    return value;
  };

  const channelIcon = (value: string) => {
    if (value === "whatsapp") return <MessageCircle size={10} />;
    if (value === "whatsapp_cloud") return <BadgeCheck size={10} />;
    if (value === "widget") return <Globe size={10} />;
    if (value === "playground") return <FlaskConical size={10} />;
    return <MessageCircle size={10} />;
  };

  const labelName = (key: LabelKey) => {
    if (key === "urgent") return t("inbox.labelUrgent");
    if (key === "waiting") return t("inbox.labelWaiting");
    return t("inbox.labelFollowUp");
  };

  const emptyCopy = () => {
    if (tab === "mine") return t("inbox.emptyMine");
    if (tab === "unread") return t("inbox.emptyUnread");
    if (labelFilter) return t("inbox.emptyLabel");
    return t("inbox.empty");
  };

  const buildParams = useCallback((offsetValue: number) => {
    const params = new URLSearchParams();
    if (agentId) params.set("agent_id", agentId);
    if (channel) params.set("channel", channel);
    if (tab === "human" || tab === "ai") params.set("mode", tab);
    if (tab === "unread") params.set("unread", "1");
    if (tab === "mine") params.set("assigned", "me");
    if (labelFilter) params.set("label", labelFilter);
    if (search) params.set("search", search);
    params.set("limit", String(LIMIT));
    params.set("offset", String(offsetValue));
    return params.toString();
  }, [agentId, channel, tab, labelFilter, search]);

  const selectedIdRef = useRef<string | null>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLInputElement>(null);
  const cannedRef = useRef<HTMLFormElement>(null);
  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);
  const wasNearBottomRef = useRef(true);
  useEffect(() => {
    const el = messagesRef.current;
    if (el) { const handler = () => { wasNearBottomRef.current = isNearBottom(el); }; el.addEventListener("scroll", handler, { passive: true }); return () => el.removeEventListener("scroll", handler); }
  }, [selected?.id]);
  useEffect(() => {
    const el = messagesRef.current;
    if (!el) return;
    if (wasNearBottomRef.current) {
      const frame = requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
      return () => cancelAnimationFrame(frame);
    }
  }, [selected?.id, selected?.messages?.at(-1)?.id]);

  const loadFirst = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) setLoading(true);
    try {
      const rows = await api<ConversationInbox[]>(`/conversations/inbox?${buildParams(0)}`);
      setItems(rows); setOffset(rows.length); setHasMore(rows.length === LIMIT);
    } catch (err) {
      if (!opts?.silent) toast.error(messageFrom(err));
    } finally {
      if (!opts?.silent) setLoading(false);
    }
  }, [buildParams, toast]);

  const refreshSelected = useCallback(async () => {
    const id = selectedIdRef.current;
    if (!id) return;
    try {
      const conv = await api<Conversation>(`/conversations/${id}`);
      if (selectedIdRef.current !== id) return;
      setSelected((prev) => {
        if (isSameOpenThread(prev, conv)) return prev;
        setItems((rows) => rows.map((row) => (row.id === id ? { ...row, unread: false, unread_count: 0 } : row)));
        api(`/conversations/${id}/read`, { method: "POST" }).catch(() => {});
        return conv;
      });
    } catch {
      // Poll failures should not interrupt the open thread.
    }
  }, []);

  useEffect(() => { loadFirst(); }, [loadFirst]);

  useEffect(() => {
    const id = setInterval(() => {
      if (offset <= LIMIT) {
        loadFirst({ silent: true });
        refreshSelected();
      }
    }, POLL_MS);
    return () => clearInterval(id);
  }, [loadFirst, refreshSelected, offset]);

  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const rows = await api<ConversationInbox[]>(`/conversations/inbox?${buildParams(offset)}`);
      setItems((prev) => [...prev, ...rows]); setOffset((o) => o + rows.length); setHasMore(rows.length === LIMIT);
    } catch (err) { toast.error(messageFrom(err)); } finally { setLoadingMore(false); }
  }

  function onScroll(event: UIEvent<HTMLElement>) {
    const el = event.currentTarget;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 80) loadMore();
  }

  async function choose(id: string) {
    selectedIdRef.current = id;
    setCannedOpen(false);
    setSelected(await api<Conversation>(`/conversations/${id}`));
    setItems((rows) => rows.map((row) => (row.id === id ? { ...row, unread: false, unread_count: 0 } : row)));
    api(`/conversations/${id}/read`, { method: "POST" }).catch(() => {});
  }

  async function toggleMode(next: "ai" | "human") {
    if (!selected) return;
    const conv = await api<Conversation>(`/conversations/${selected.id}/mode`, { method: "PATCH", body: JSON.stringify({ mode: next }) });
    setSelected(conv);
    loadFirst({ silent: true });
    if (next === "human") requestAnimationFrame(() => composerRef.current?.focus());
  }

  async function assignTo(userId: string) {
    if (!selected) return;
    const conv = await api<Conversation>(`/conversations/${selected.id}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ assigned_user_id: userId || null }),
    });
    setSelected(conv);
    loadFirst({ silent: true });
  }

  async function toggleLabel(key: LabelKey) {
    if (!selected) return;
    const current = selected.labels || [];
    const next = current.includes(key) ? current.filter((item) => item !== key) : [...current, key];
    const conv = await api<Conversation>(`/conversations/${selected.id}/labels`, {
      method: "PATCH",
      body: JSON.stringify({ labels: next }),
    });
    setSelected(conv);
    loadFirst({ silent: true });
  }

  const draft = selected ? (drafts[selected.id] ?? "") : "";
  const slashMatch = draft.match(/(?:^|\s)\/([^\s]*)$/);
  const cannedQuery = (slashMatch?.[1] ?? "").toLowerCase();
  const cannedMatches = useMemo(() => {
    const q = cannedQuery;
    if (!q) return canned;
    return canned.filter((item) => item.shortcode.includes(q) || item.title.toLowerCase().includes(q) || item.body.toLowerCase().includes(q));
  }, [canned, cannedQuery]);

  useEffect(() => { setCannedIndex(0); }, [cannedQuery, cannedOpen]);
  useEffect(() => {
    if (!cannedOpen) return;
    const close = (event: MouseEvent) => {
      if (cannedRef.current && !cannedRef.current.contains(event.target as Node)) setCannedOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [cannedOpen]);

  function setDraft(value: string) {
    if (!selected) return;
    setDrafts((prev) => ({ ...prev, [selected.id]: value }));
    if (/(?:^|\s)\/[^\s]*$/.test(value)) setCannedOpen(true);
  }

  function insertCanned(item: CannedReply) {
    if (!selected) return;
    const next = draft.replace(/(?:^|\s)\/[^\s]*$/, "").replace(/\s+$/, "");
    setDrafts((prev) => ({ ...prev, [selected.id]: next ? `${next} ${item.body}` : item.body }));
    setCannedOpen(false);
    requestAnimationFrame(() => composerRef.current?.focus());
  }

  function onComposerKey(event: KeyboardEvent<HTMLInputElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (selected?.mode === "human") setCannedOpen((open) => !open);
      return;
    }
    if (!cannedOpen) return;
    if (event.key === "Escape") { event.preventDefault(); setCannedOpen(false); return; }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setCannedIndex((i) => Math.min(i + 1, Math.max(cannedMatches.length - 1, 0)));
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setCannedIndex((i) => Math.max(i - 1, 0));
      return;
    }
    if (event.key === "Enter" && cannedMatches[cannedIndex]) {
      event.preventDefault();
      insertCanned(cannedMatches[cannedIndex]);
    }
  }

  async function reply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !draft.trim()) return;
    setBusy(true);
    try {
      setSelected(await api<Conversation>(`/conversations/${selected.id}/reply`, { method: "POST", body: JSON.stringify({ content: draft.trim() }) }));
      setDrafts((prev) => ({ ...prev, [selected.id]: "" }));
      setCannedOpen(false);
      loadFirst({ silent: true });
    } catch (err) { toast.error(messageFrom(err)); } finally { setBusy(false); composerRef.current?.focus(); }
  }

  return <div className="page">
    <PageHead eyebrow={t("inbox.eyebrow")} title={t("inbox.title")} description={t("inbox.description")} />

    <div className="toolbar filters">
      <div className="filter-select"><span>{t("inbox.filterAgent")}</span><select value={agentId} onChange={(e) => setAgentId(e.target.value)}><option value="">{t("inbox.allAgents")}</option>{agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></div>
      <div className="filter-select"><span>{t("inbox.filterChannel")}</span><select value={channel} onChange={(e) => setChannel(e.target.value)}><option value="">{t("inbox.allChannels")}</option><option value="playground">{t("inbox.channelPlayground")}</option><option value="whatsapp">{t("inbox.channelWhatsapp")}</option><option value="whatsapp_cloud">{t("inbox.channelWhatsappCloud")}</option><option value="widget">{t("inbox.channelWidget")}</option></select></div>
    </div>

    <div className="inbox-layout">
      <aside className="inbox-list" onScroll={onScroll}>
        <div className="inbox-search"><Search size={16} /><input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder={t("inbox.searchPlaceholder")} /></div>
        <div className="inbox-tabs" role="tablist">
          <button type="button" role="tab" aria-selected={tab === "all"} className={tab === "all" ? "active" : ""} onClick={() => setTab("all")}>{t("inbox.tabAll")}</button>
          <button type="button" role="tab" aria-selected={tab === "mine"} className={tab === "mine" ? "active" : ""} onClick={() => setTab("mine")}>{t("inbox.tabMine")}</button>
          <button type="button" role="tab" aria-selected={tab === "unread"} className={tab === "unread" ? "active" : ""} onClick={() => setTab("unread")}>{t("inbox.tabUnread")}</button>
          <button type="button" role="tab" aria-selected={tab === "human"} className={tab === "human" ? "active" : ""} onClick={() => setTab("human")}>{t("inbox.statusHuman")}</button>
          <button type="button" role="tab" aria-selected={tab === "ai"} className={tab === "ai" ? "active" : ""} onClick={() => setTab("ai")}>{t("inbox.statusAi")}</button>
        </div>
        <div className="inbox-label-filters" role="group" aria-label={t("inbox.filterStatus")}>
          {LABELS.map((key) => (
            <button key={key} type="button" className={`inbox-chip ${key} ${labelFilter === key ? "on" : ""}`} aria-pressed={labelFilter === key} onClick={() => setLabelFilter((prev) => prev === key ? "" : key)}>{labelName(key)}</button>
          ))}
        </div>
        {loading ? <div className="no-conversations"><LoaderCircle className="spin" size={16} /> {t("inbox.loading")}</div>
          : items.length ? <>
            {items.map((item) => (
              <button key={item.id} className={`inbox-row ${selected?.id === item.id ? "active" : ""} ${item.unread ? "unread" : ""}`} onClick={() => choose(item.id)}>
                <span className="inbox-avatar">
                  <span className="entity-avatar tiny"><UserRound size={15} /></span>
                  <span className={`channel-badge ${item.channel}`} title={channelLabel(item.channel)}>{channelIcon(item.channel)}</span>
                </span>
                <span className="inbox-row-body">
                  <span className="inbox-row-top"><strong>{item.contact_name || item.title}</strong><time>{formatWhen(item.updated_at, lang)}</time></span>
                  <small className="inbox-row-preview">{item.preview || t("inbox.noMessages")}</small>
                  <small className="inbox-row-meta">
                    {item.agent_name} · {channelLabel(item.channel)}
                    <span className={`mini-badge ${item.mode}`}>{item.mode === "human" ? t("inbox.modeHuman") : t("inbox.modeAi")}</span>
                    {(item.labels || []).map((key) => LABELS.includes(key as LabelKey) ? <span key={key} className={`inbox-dot ${key}`} title={labelName(key as LabelKey)} /> : null)}
                    {item.assigned_user_name && <span className="inbox-assignee" title={item.assigned_user_name}>{initials(item.assigned_user_name)}</span>}
                  </small>
                </span>
                {item.unread_count > 0 && selected?.id !== item.id && <span className="inbox-unread-count" aria-label={t("inbox.unreadCount", { count: item.unread_count })}>{item.unread_count > 99 ? "99+" : item.unread_count}</span>}
              </button>
            ))}
            {loadingMore && <div className="no-conversations"><LoaderCircle className="spin" size={15} /></div>}
          </> : <div className="no-conversations">{emptyCopy()}</div>}
      </aside>

      <section className="inbox-thread">
        {!selected ? <div className="empty-state"><div className="empty-icon"><InboxIcon /></div><h3>{t("inbox.empty")}</h3><p>{t("inbox.selectPrompt")}</p></div>
          : <>
            <header>
              <div>
                <strong>{selected.contact_name || selected.title}</strong>
                <small>{channelLabel(selected.channel)}{selected.assigned_user_name ? ` · ${selected.assigned_user_id === me?.id ? t("inbox.you") : selected.assigned_user_name}` : ""}</small>
              </div>
              <button className={`mode-toggle ${selected.mode}`} onClick={() => toggleMode(selected.mode === "ai" ? "human" : "ai")}>{selected.mode === "ai" ? t("inbox.takeControl") : t("inbox.returnToAi")}</button>
            </header>
            <div className="inbox-desk">
              <label className="inbox-assign">
                <span>{t("inbox.assign")}</span>
                <select value={selected.assigned_user_id || ""} onChange={(e) => assignTo(e.target.value)} aria-label={t("inbox.assign")}>
                  <option value="">{t("inbox.unassigned")}</option>
                  {members.map((member) => (
                    <option key={member.id} value={member.id}>{member.id === me?.id ? t("inbox.you") : member.name}</option>
                  ))}
                </select>
              </label>
              <div className="inbox-thread-labels">
                {LABELS.map((key) => (
                  <button key={key} type="button" className={`inbox-chip ${key} ${(selected.labels || []).includes(key) ? "on" : ""}`} aria-pressed={(selected.labels || []).includes(key)} onClick={() => toggleLabel(key)}>{labelName(key)}</button>
                ))}
              </div>
            </div>
            <div className="inbox-messages" ref={messagesRef}>
              {selected.messages?.map((message) => (
                <div key={message.id} className={`inbox-message ${message.role}`}>
                  <small>{message.sender_name || (message.role === "assistant" ? t("inbox.senderAgent") : t("inbox.senderVisitor"))} · {formatWhen(message.created_at, lang)}</small>
                  <p>{message.content}</p>
                </div>
              ))}
            </div>
            <form className="inbox-composer" onSubmit={reply} ref={cannedRef}>
              {cannedOpen && selected.mode === "human" && (
                <div className="inbox-canned" role="listbox" aria-label={t("inbox.cannedTitle")}>
                  <strong>{t("inbox.cannedTitle")}</strong>
                  <p>{t("inbox.cannedHint")}</p>
                  {cannedMatches.length ? cannedMatches.map((item, index) => (
                    <button key={item.id} type="button" role="option" aria-selected={index === cannedIndex} className={index === cannedIndex ? "active" : ""} onClick={() => insertCanned(item)}>
                      <span><b>/{item.shortcode}</b> {item.title}</span>
                      <small>{item.body}</small>
                    </button>
                  )) : <em>{t("inbox.cannedEmpty")}</em>}
                </div>
              )}
              <input
                ref={composerRef}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={onComposerKey}
                placeholder={selected.mode === "human" ? t("inbox.composerHuman") : t("inbox.composerLocked")}
                disabled={selected.mode !== "human"}
                aria-autocomplete="list"
              />
              <button type="button" className="inbox-canned-toggle" disabled={selected.mode !== "human"} aria-label={t("inbox.cannedTitle")} aria-expanded={cannedOpen} aria-haspopup="listbox" onClick={() => setCannedOpen((open) => !open)}><Zap size={16} /></button>
              <button type="submit" disabled={selected.mode !== "human" || busy || !draft.trim()}>{t("inbox.send")}</button>
            </form>
          </>}
      </section>
    </div>
  </div>;
}

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { Bell, BookOpen, Bot, Building2, CreditCard, Inbox, Images, LayoutDashboard, LogOut, Menu, MessageSquareText, Radio, Settings, Sparkles, Wallet, Workflow, X } from "lucide-react";
import { api } from "@/lib/api";
import { useCarouselGeneration } from "@/lib/carousel-generation-context";
import { useT, type I18nKey } from "@/lib/i18n";
import { LanguageSwitcher } from "@/components/language-switcher";
import type { Carousel, LeadNotification, User } from "@/types";

const navigation: { href: string; labelKey: I18nKey; icon: typeof LayoutDashboard }[] = [
  { href: "/", labelKey: "nav.home", icon: LayoutDashboard },
  { href: "/clients", labelKey: "nav.clients", icon: Building2 },
  { href: "/agents", labelKey: "nav.agents", icon: Bot },
  { href: "/carousels", labelKey: "nav.carousels", icon: Images },
  { href: "/automations", labelKey: "nav.automations", icon: Workflow },
  { href: "/inbox", labelKey: "nav.inbox", icon: Inbox },
  { href: "/playground", labelKey: "nav.playground", icon: MessageSquareText },
  { href: "/channels", labelKey: "nav.channels", icon: Radio },
  { href: "/settings", labelKey: "nav.settings", icon: Settings },
  { href: "/manual", labelKey: "nav.manual", icon: BookOpen },
];

// Extra path prefixes served without a session (comma-separated, baked at
// build). Lets a deployment add public pages without patching the shell.
const EXTRA_PUBLIC_PATHS = (process.env.NEXT_PUBLIC_PUBLIC_PATHS || "")
  .split(",")
  .map((path) => path.trim())
  .filter(Boolean);

const EXTRA_NAV_ICONS: Record<string, typeof LayoutDashboard> = {
  wallet: Wallet,
  "credit-card": CreditCard,
  billing: Wallet,
  sparkles: Sparkles,
};

// Extra sidebar links (comma-separated `label|href|icon`, baked at build). Lets a
// deployment add nav entries without patching the shell; icon falls back to Wallet.
const EXTRA_NAV = (process.env.NEXT_PUBLIC_EXTRA_NAV || "")
  .split(",")
  .map((entry) => entry.trim())
  .filter(Boolean)
  .map((entry) => {
    const [label, href, icon] = entry.split("|").map((part) => (part || "").trim());
    return { label, href, icon: EXTRA_NAV_ICONS[icon] || Wallet };
  })
  .filter((item) => item.label && item.href);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const t = useT();
  const { activeCount: clientGeneratingCount } = useCarouselGeneration();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(pathname !== "/login");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [serverGeneratingCount, setServerGeneratingCount] = useState(0);
  const [notes, setNotes] = useState<LeadNotification[]>([]);
  const [notesOpen, setNotesOpen] = useState(false);
  const isLogin = pathname === "/login";
  const isPortal = pathname.startsWith("/portal/");
  const isWidget = pathname.startsWith("/widget/");
  const isExtraPublic = EXTRA_PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
  const isBare = isLogin || isPortal || isWidget || isExtraPublic;

  useEffect(() => {
    if (isBare) { setLoading(false); return; }
    setLoading(true);
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [isBare, pathname, router]);

  useEffect(() => {
    if (isBare || !user) return;
    const poll = () => {
      api<Carousel[]>("/carousels")
        .then((rows) => setServerGeneratingCount(rows.filter((row) => row.is_generating).length))
        .catch(() => {});
    };
    poll();
    const timer = window.setInterval(poll, 5000);
    return () => window.clearInterval(timer);
  }, [isBare, user]);

  useEffect(() => {
    if (isBare || !user) return;
    const poll = () => {
      api<LeadNotification[]>("/leads/notifications")
        .then(setNotes)
        .catch(() => {});
    };
    poll();
    const timer = window.setInterval(poll, 15000);
    return () => window.clearInterval(timer);
  }, [isBare, user]);

  const generatingBadgeCount = Math.max(clientGeneratingCount, serverGeneratingCount);

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  if (isBare) return <>{children}</>;
  if (loading || !user) return <div className="app-loader"><span className="openlivery-icon"><img src="/brand/app-logo-icon.png" alt="" /></span><span>{t("shell.loading")}</span></div>;

  return (
    <div className="app-layout">
      <button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label={t("shell.openMenu")}><Menu /></button>
      {mobileOpen && <div className="sidebar-overlay" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand-row">
          <Link href="/" className="brand"><span className="openlivery-icon"><img src="/brand/app-logo-icon.png" alt="" /></span><span>Fast Livery</span></Link>
          <button className="sidebar-close" onClick={() => setMobileOpen(false)} aria-label={t("shell.closeMenu")}><X /></button>
        </div>
        <div className="sidebar-workspace"><Building2 size={14} /><span>{user.agency.name}</span></div>
        <nav>
          <span className="nav-label">{t("nav.section")}</span>
          {navigation.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const showGeneratingBadge = item.href === "/carousels" && generatingBadgeCount > 0;
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : ""} onClick={() => setMobileOpen(false)}>
                <item.icon size={18} />
                <span>{t(item.labelKey)}</span>
                {showGeneratingBadge && (
                  <span className="nav-badge" title={t("carousels.generation.badgeTitle")}>
                    {generatingBadgeCount}
                  </span>
                )}
              </Link>
            );
          })}
          {EXTRA_NAV.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return <Link key={item.href} href={item.href} className={active ? "active" : ""} onClick={() => setMobileOpen(false)}><Icon size={18} /><span>{item.label}</span></Link>;
          })}
        </nav>
        <div className="sidebar-foot">
          <div className="notice-wrap">
            <button type="button" className="icon-button inverse" onClick={() => setNotesOpen((open) => !open)} title={t("shell.notifications")}>
              <Bell size={17} />
              {notes.filter((item) => !item.read_at).length > 0 && (
                <span className="notice-badge">{notes.filter((item) => !item.read_at).length}</span>
              )}
            </button>
            {notesOpen && (
              <div className="notice-dropdown">
                <strong>{t("shell.notifications")}</strong>
                {notes.length === 0 && <p>{t("shell.noNotifications")}</p>}
                {notes.slice(0, 12).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={item.read_at ? "" : "unread"}
                    onClick={async () => {
                      if (!item.read_at) {
                        await api(`/leads/notifications/${item.id}/read`, { method: "POST" }).catch(() => {});
                        setNotes((current) => current.map((row) => (row.id === item.id ? { ...row, read_at: new Date().toISOString() } : row)));
                      }
                      setNotesOpen(false);
                      setMobileOpen(false);
                      router.push(`/clients/${item.client_id}?tab=leads`);
                    }}
                  >
                    <span>{item.contact_name || t("shell.newLead")}</span>
                    <small>{item.source}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="user-avatar">{user.name.slice(0, 1).toUpperCase()}</div>
          <div className="user-meta"><strong>{user.name}</strong><span>{user.email}</span></div>
          <button className="icon-button inverse" onClick={logout} title={t("shell.logout")}><LogOut size={17} /></button>
        </div>
        <LanguageSwitcher />
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}

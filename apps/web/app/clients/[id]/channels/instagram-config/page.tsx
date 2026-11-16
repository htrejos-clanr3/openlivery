"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Check, ExternalLink, Instagram, LoaderCircle, X } from "lucide-react";
import { api } from "@/lib/api";

type Channel = { status: string; username: string | null; page_id: string | null };
type Options = { oauth_available: boolean; mock_mode: boolean };
type AgencyApp = { app_id: string; has_secret: boolean };

function Row({ title, state, detail, children }: { title: string; state: "ok" | "todo" | "wait"; detail: string; children?: React.ReactNode }) {
  const color = state === "ok" ? "#16a34a" : state === "todo" ? "#dc2626" : "#a16207";
  return (
    <div style={{ display: "flex", gap: 14, padding: "14px 16px", border: "1px solid #e4e8ee", borderRadius: 12, background: "#fff", alignItems: "flex-start", flexWrap: "wrap" }}>
      <span style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", background: color, color: "#fff", flex: "none", marginTop: 2 }}>
        {state === "ok" ? <Check size={14} /> : state === "todo" ? <X size={14} /> : "·"}
      </span>
      <div style={{ flex: 1, minWidth: 220 }}>
        <strong style={{ display: "block" }}>{title}</strong>
        <span className="field-help">{detail}</span>
      </div>
      <div style={{ display: "flex", gap: 8 }}>{children}</div>
    </div>
  );
}

export default function InstagramConfigPage() {
  const params = useParams<{ id: string }>();
  const clientId = params?.id ?? "";
  const [channel, setChannel] = useState<Channel | null>(null);
  const [options, setOptions] = useState<Options | null>(null);
  const [app, setApp] = useState<AgencyApp | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!clientId) return;
    Promise.allSettled([
      api<Channel>(`/instagram/channels/${clientId}`),
      api<Options>("/instagram/oauth/options"),
      api<AgencyApp>("/agency/meta-app"),
    ]).then((results) => {
      if (results[0].status === "fulfilled") setChannel(results[0].value);
      if (results[1].status === "fulfilled") setOptions(results[1].value);
      if (results[2].status === "fulfilled") setApp(results[2].value);
      setLoading(false);
    });
  }, [clientId]);

  const connected = channel?.status === "connected";
  const appReady = Boolean(app?.app_id && app.has_secret);
  const appsUrl = app?.app_id ? `https://developers.facebook.com/apps/${app.app_id}/use_cases` : "https://developers.facebook.com/apps";
  const basicUrl = app?.app_id ? `https://developers.facebook.com/apps/${app.app_id}/settings/basic/` : "https://developers.facebook.com/apps";

  if (loading) {
    return <div className="page-loading"><LoaderCircle className="spin" /> Cargando…</div>;
  }

  return (
    <div className="page-form" style={{ display: "grid", gap: 12 }}>
      <section style={{ display: "flex", gap: 14, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", padding: "18px 20px", border: "1px solid #e4e8ee", borderRadius: 14, background: "#fff" }}>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <span aria-hidden style={{ width: 44, height: 44, borderRadius: 12, display: "grid", placeItems: "center", background: "linear-gradient(135deg,#f9ce34,#ee2a7b 55%,#6228d7)", color: "#fff", flex: "none" }}>
            <Instagram size={24} />
          </span>
          <div>
            <small className="field-help" style={{ textTransform: "uppercase", letterSpacing: ".05em", fontSize: 11 }}>Canal de Instagram</small>
            <h1 style={{ margin: "2px 0 0", fontSize: 22 }}>Configuración de Instagram</h1>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className={connected ? "pill ok" : "pill bad"}>{connected ? "Conectado" : "Desconectado"}</span>
          <Link className="button" href={`/clients/${clientId}/channels`}><ArrowLeft size={15} /> Canales</Link>
        </div>
      </section>

      <Row
        title="1 · App de Meta de la agencia"
        state={appReady ? "ok" : "todo"}
        detail={
          appReady
            ? `App ID ${app?.app_id} guardado. Es la misma para todos los clientes.`
            : "Falta el App ID o el App Secret. Se copian de la pantalla de Meta de abajo y se pegan en Configuración → Meta."
        }
      >
        <a className="button" href={basicUrl} target="_blank" rel="noreferrer">
          <ExternalLink size={15} /> Abrir la app en Meta
        </a>
        <Link className="button ghost" href="/settings/meta">Pegar en Configuración → Meta</Link>
      </Row>

      <section style={{ border: "1px solid #e4e8ee", borderRadius: 12, background: "#f8fafc", padding: "14px 16px" }}>
        <strong style={{ display: "block", fontSize: 13.5 }}>Instrucciones de esa pantalla de Meta</strong>
        <ol style={{ margin: "8px 0 0", paddingLeft: 20, fontSize: 13.5, lineHeight: 1.7 }}>
          <li>En Meta abre <b>Configuración de la app → Básica</b>.</li>
          <li><b>Identificador de la app</b>: ese número es el App ID. Cópialo.</li>
          <li><b>Clave secreta de la app</b>: pulsa <b>Mostrar</b> y cópiala. Meta solo la enseña ahí.</li>
          <li>Pégalos en <b>Configuración → Meta</b> y pulsa Guardar. Se validan contra Meta al guardar.</li>
        </ol>
      </section>

      <Row
        title="2 · Permisos de Instagram en la app"
        state="wait"
        detail="Meta no permite comprobarlos desde aquí. Deben estar concedidos: instagram_basic, instagram_content_publish, instagram_manage_messages, instagram_manage_comments, pages_show_list, pages_manage_posts."
      >
        <a className="button" href={appsUrl} target="_blank" rel="noreferrer">
          <ExternalLink size={15} /> Abrir permisos en Meta
        </a>
      </Row>

      <Row
        title="3 · Conectar la cuenta del cliente"
        state={connected ? "ok" : "todo"}
        detail={
          connected
            ? `Cuenta conectada${channel?.username ? `: @${channel.username}` : ""}.`
            : options?.oauth_available
              ? "El cliente autoriza con su cuenta Business. Sin cuenta Business no se puede publicar."
              : "El login de Meta no está disponible: revisa el App ID y el secret del paso 1."
        }
      >
        <Link className="button primary" href={`/clients/${clientId}/channels/instagram?connect=1`}>
          {connected ? "Reconectar" : "Conectar con Instagram"}
        </Link>
      </Row>

      <Row
        title="4 · Página de Facebook vinculada"
        state={channel?.page_id ? "ok" : "todo"}
        detail={channel?.page_id ? `Página ${channel.page_id}.` : "Instagram exige una Página vinculada. Sin ella la publicación falla."}
      >
        <a className="button" href="https://business.facebook.com/settings/pages" target="_blank" rel="noreferrer">
          <ExternalLink size={15} /> Abrir Páginas en Meta
        </a>
      </Row>

      <Row
        title="5 · Publicación de prueba"
        state="todo"
        detail="Todavía no existe el publicador: esta función está pendiente de construir. Cuando exista, aquí saldrá el botón para publicar una imagen."
      />

      <section style={{ display: "flex", gap: 12, padding: "14px 16px", border: "1px solid #fde68a", borderRadius: 12, background: "#fffbeb" }}>
        <div>
          <strong style={{ display: "block", fontSize: 14 }}>Qué falta exactamente ahora</strong>
          <span className="field-help" style={{ display: "block", marginTop: 2 }}>
            {!appReady
              ? "Guardar el App ID y el secret de la agencia."
              : !connected
                ? "Conectar la cuenta y asegurarte de que los permisos del paso 2 estén concedidos en Meta."
                : "El publicador: es el único bloque que no existe todavía."}
          </span>
        </div>
      </section>
    </div>
  );
}

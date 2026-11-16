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
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [hasSecret, setHasSecret] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (!clientId) return;
    Promise.allSettled([
      api<Channel>(`/instagram/channels/${clientId}`),
      api<Options>("/instagram/oauth/options"),
      api<AgencyApp>("/agency/meta-app"),
    ]).then((results) => {
      if (results[0].status === "fulfilled") setChannel(results[0].value);
      if (results[1].status === "fulfilled") setOptions(results[1].value);
      if (results[2].status === "fulfilled") {
        setApp(results[2].value);
        setAppId(results[2].value.app_id || "");
        setHasSecret(Boolean(results[2].value.has_secret));
      }
      setLoading(false);
    });
  }, [clientId]);

  async function saveApp() {
    setSaving(true);
    setFeedback("");
    try {
      const result = await api<{ verified: boolean | null; has_secret: boolean }>("/agency/meta-app", {
        method: "PUT",
        body: JSON.stringify({ app_id: appId, app_secret: appSecret || null }),
      });
      setHasSecret(Boolean(result.has_secret));
      setAppSecret("");
      setApp({ app_id: appId, has_secret: Boolean(result.has_secret) });
      setFeedback(result.verified === false ? "Meta no reconoce ese App ID con ese secret." : "Guardado y verificado.");
    } catch {
      setFeedback("No se pudo guardar. Revisa los datos.");
    } finally {
      setSaving(false);
    }
  }

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
          <button type="button" className="button" onClick={() => window.location.reload()}>
            Comprobar
          </button>
          <Link className="button" href={`/clients/${clientId}/channels`}><ArrowLeft size={15} /> Canales</Link>
        </div>
      </section>

      <section style={{ border: "1px solid #e4e8ee", borderRadius: 12, background: "#fff", padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", background: appReady ? "#16a34a" : "#dc2626", color: "#fff", flex: "none" }}>
              {appReady ? <Check size={14} /> : <X size={14} />}
            </span>
            <div>
              <strong style={{ display: "block" }}>1 · App de Meta de la agencia</strong>
              <span className="field-help">
                {appReady ? "Guardada y compartida por todos los clientes." : "Faltan el App ID o el secret."}
              </span>
            </div>
          </div>
          <a className="button" href={basicUrl} target="_blank" rel="noreferrer">
            <ExternalLink size={15} /> Abrir la app en Meta
          </a>
        </div>

        <div style={{ display: "grid", gap: 10, marginTop: 14, maxWidth: 620 }}>
          <label className="field">
            App ID
            <input value={appId} onChange={(event) => setAppId(event.target.value)} placeholder="1074725462274330" />
          </label>
          <label className="field">
            App Secret {hasSecret ? "(vacío = conservar el actual)" : ""}
            <input
              type="password"
              value={appSecret}
              onChange={(event) => setAppSecret(event.target.value)}
              placeholder={hasSecret ? "clave guardada" : "Pega la clave secreta"}
            />
          </label>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" className="button primary" onClick={saveApp} disabled={saving || !appId}>
              {saving ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Guardar app de la agencia
            </button>
            {feedback ? <span className="field-help">{feedback}</span> : null}
          </div>
        </div>

        <ol style={{ margin: "14px 0 0", paddingLeft: 20, fontSize: 13, lineHeight: 1.7, color: "#475569" }}>
          <li>En Meta abre <b>Configuración de la app → Básica</b>.</li>
          <li><b>Identificador de la app</b>: ese número es el App ID.</li>
          <li><b>Clave secreta de la app</b>: pulsa <b>Mostrar</b> y cópiala.</li>
          <li>Pégalos arriba y pulsa Guardar. Se validan contra Meta.</li>
        </ol>
      </section>
      <section style={{ border: "1px solid #e4e8ee", borderRadius: 12, background: "#fff", padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", background: "#a16207", color: "#fff", flex: "none" }}>·</span>
            <div>
              <strong style={{ display: "block" }}>2 · Permisos de Instagram en la app</strong>
              <span className="field-help">Meta los revisa y no se pueden comprobar desde aquí.</span>
            </div>
          </div>
          <a className="button" href={appsUrl} target="_blank" rel="noreferrer">
            <ExternalLink size={15} /> Abrir permisos en Meta
          </a>
          <button type="button" className="button" onClick={() => window.location.reload()}>
            Comprobar
          </button>
        </div>

        <ol style={{ margin: "14px 0 0", paddingLeft: 20, fontSize: 13, lineHeight: 1.75, color: "#475569" }}>
          <li><b>No hay botón Guardar en esa pantalla.</b> Meta aplica cada cambio al marcarlo; la confirmación es la columna <b>Estado</b> diciendo «Listo para la prueba».</li>
          <li>En el desplegable de arriba, el caso de uso correcto es <b>«API de Instagram»</b>.</li>
          <li>Si falta alguna función, pulsa <b>«Agregar más a este caso de uso»</b> y agrega: <code style={{ fontSize: 12 }}>instagram_basic · instagram_content_publish · instagram_manage_messages · instagram_manage_comments</code></li>
          <li>Para publicar también en la <b>Página de Facebook</b>, agrega el caso de uso «Administrar todos los aspectos de tu página» con <code style={{ fontSize: 12 }}>pages_show_list · pages_manage_posts · business_management</code></li>
          <li><b>«Listo para la prueba» no es aprobado:</b> solo funciona con usuarios con rol en la app. Para clientes reales necesitas verificación de negocio, acceso avanzado de cada permiso y la app publicada.</li>
          <li>Cuando termines, pulsa el botón <b>Comprobar</b> de este bloque (o el de arriba a la derecha): si sigue en ámbar, Meta no está devolviendo los permisos.</li>
        </ol>
      </section>

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

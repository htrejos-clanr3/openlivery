"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, ArrowLeft, Check, ExternalLink, Instagram, LoaderCircle, RefreshCw, X } from "lucide-react";
import { buildChannelConsent } from "@/components/channel-connect-consent-modal";
import { api } from "@/lib/api";

type Channel = { status: string; username: string | null; page_id: string | null };
type Options = { oauth_available: boolean; mock_mode: boolean };
type AgencyApp = { app_id: string; has_secret: boolean };
type CheckOutcome = {
  level: "ok" | "todo" | "wait";
  title: string;
  detail: string;
  next: string;
};

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
  const [checking, setChecking] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [outcome, setOutcome] = useState<CheckOutcome | null>(null);

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

  async function connect() {
    setConnecting(true);
    setOutcome(null);
    try {
      const session = await api<{ state: string; dialog_url: string | null; mock_mode: boolean }>(
        `/instagram/channels/${clientId}/oauth/session`,
        { method: "POST", body: JSON.stringify(buildChannelConsent("instagram", clientId)) },
      );
      if (session.dialog_url) {
        // Meta must open in its own window so this screen stays available to
        // receive the result and re-check the channel state.
        const popup = window.open(session.dialog_url, "_blank");
        if (!popup) window.location.href = session.dialog_url;
        setConnecting(false);
        return;
      }
      setOutcome({
        level: "todo",
        title: "Meta no devolvió una URL de autorización",
        detail: "El servidor no pudo construir el diálogo de Meta: falta el App ID o el secret, o el servidor tiene el login guiado deshabilitado.",
        next: "Revisa el bloque 1, guarda los datos y vuelve a intentar.",
      });
    } catch {
      setOutcome({
        level: "todo",
        title: "La conexión no se pudo iniciar",
        detail: "La petición de sesión OAuth falló antes de salir hacia Meta.",
        next: "Pulsa Comprobar estado para ver qué falta y revisa el bloque 1.",
      });
    } finally {
      setConnecting(false);
    }
  }

  async function runCheck() {
    setChecking(true);
    setOutcome(null);
    try {
      const [channelResult, optionsResult, appResult] = await Promise.allSettled([
        api<Channel>(`/instagram/channels/${clientId}`),
        api<Options>("/instagram/oauth/options"),
        api<AgencyApp>("/agency/meta-app"),
      ]);
      const currentChannel = channelResult.status === "fulfilled" ? channelResult.value : channel;
      const currentOptions = optionsResult.status === "fulfilled" ? optionsResult.value : options;
      const currentApp = appResult.status === "fulfilled" ? appResult.value : app;

      if (!currentApp?.app_id || !currentApp.has_secret) {
        setOutcome({
          level: "todo",
          title: "No hay nada que comprobar todavía",
          detail: "La app de Meta de la agencia no está configurada, así que esta consulta no se envía a Meta.",
          next: "Guarda el App ID y el App Secret en el bloque 1 y vuelve a pulsar Comprobar estado.",
        });
        return;
      }
      if (!currentOptions?.oauth_available) {
        setOutcome({
          level: "todo",
          title: "Consulta enviada a Meta sin resultado",
          detail: "Meta no acepta el App ID con ese secret, o el login guiado está deshabilitado en el servidor.",
          next: "Revisa el App ID y el secret en el bloque 1, guarda y vuelve a comprobar.",
        });
        return;
      }
      if (currentChannel?.status !== "connected") {
        setOutcome({
          level: "todo",
          title: "Consulta enviada a Meta sin resultado",
          detail: "La app está bien configurada, pero no hay una cuenta conectada: sin token no se pueden leer los permisos.",
          next: "Pulsa «Conectar con Instagram» en el bloque 3. Meta pedirá autorización; al volver, pulsa Comprobar estado otra vez.",
        });
        return;
      }
      setOutcome({
        level: "ok",
        title: "Resultado exitoso",
        detail: "La cuenta está conectada y la app responde. Meta no expone aquí si los permisos son de prueba o aprobados.",
        next: "Paso 5: publicar una imagen de prueba. Ese publicador todavía no existe, así que es lo único que queda pendiente.",
      });
    } finally {
      setChecking(false);
    }
  }

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
          <button
            type="button"
            className="button ghost"
            title="Consulta el estado y explica el siguiente paso"
            onClick={runCheck}
            disabled={checking}
          >
            {checking ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}
            {checking ? "Comprobando…" : "Comprobar estado"}
          </button>
          <Link className="button" href={`/clients/${clientId}/channels`}><ArrowLeft size={15} /> Canales</Link>
        </div>
      </section>

      {outcome ? (
        <section
          role="status"
          aria-live="polite"
          style={{
            display: "flex",
            gap: 12,
            padding: "14px 16px",
            borderRadius: 12,
            border: `1px solid ${outcome.level === "ok" ? "#bbf7d0" : "#fde68a"}`,
            background: outcome.level === "ok" ? "#f0fdf4" : "#fffbeb",
          }}
        >
          <span style={{ flex: "none", marginTop: 2 }}>
            {outcome.level === "ok" ? <Check size={18} color="#16a34a" /> : <AlertTriangle size={18} color="#a16207" />}
          </span>
          <div>
            <strong style={{ display: "block", fontSize: 14 }}>{outcome.title}</strong>
            <span style={{ display: "block", fontSize: 13, color: "#475569", marginTop: 2 }}>{outcome.detail}</span>
            <span style={{ display: "block", fontSize: 13, marginTop: 6 }}>
              <b>Siguiente paso:</b> {outcome.next}
            </span>
          </div>
        </section>
      ) : null}

      <p className="field-help" style={{ margin: 0, padding: "0 4px" }}>
        <b>✓ Listo</b> · <b>✗ Falta</b> · <b>⚠ Pendiente de Meta</b> (no se puede verificar desde aquí) · Cada bloque indica si es <b>Obligatorio</b>, <b>Condicional</b> u <b>Opcional</b>.
      </p>

      <section style={{ border: "1px solid #e4e8ee", borderRadius: 12, background: "#fff", padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", background: appReady ? "#16a34a" : "#dc2626", color: "#fff", flex: "none" }}>
              {appReady ? <Check size={14} /> : <X size={14} />}
            </span>
            <div>
              <strong style={{ display: "block" }}>1 · App de Meta de la agencia<span style={{ marginLeft: 8, fontSize: 10.5, fontWeight: 600, letterSpacing: ".04em", textTransform: "uppercase", padding: "2px 6px", borderRadius: 6, background: "#fef3c7", color: "#92400e", verticalAlign: "middle" }}>Obligatorio</span></strong>
              <span className="field-help">
                {appReady ? "Guardada y compartida por todos los clientes." : "Faltan el App ID o el secret."}
              </span>
            </div>
          </div>

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
          <li>En Meta abre <a href={basicUrl} target="_blank" rel="noreferrer">Configuración de la app → Básica</a>.</li>
          <li><b>Identificador de la app</b>: ese número es el App ID.</li>
          <li><b>Clave secreta de la app</b>: pulsa <b>Mostrar</b> y cópiala.</li>
          <li>Pégalos arriba y pulsa Guardar. Se validan contra Meta.</li>
          <li><b>En esa misma app</b> → Configuración → Básica → <b>Dominios de la app</b>: agrega <code style={{ fontSize: 12 }}>fast-livery.r3soluciones.com</code> y guarda.</li>
          <li>En <b>Iniciar sesión con Facebook → Configuración</b> → <b>URI de redirección de OAuth válidos</b>: agrega <code style={{ fontSize: 12 }}>https://fast-livery.r3soluciones.com/api/instagram/oauth/callback</code> y guarda.</li>
          <li>En <b>Roles de la app → Probar</b> añádete como tester mientras la app no esté publicada.</li>
        </ol>
      </section>
      <section style={{ border: "1px solid #e4e8ee", borderRadius: 12, background: "#fff", padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span title="Pendiente de revisión en Meta" style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", background: "#fef3c7", color: "#a16207", flex: "none" }}>
              <AlertTriangle size={14} />
            </span>
            <div>
              <strong style={{ display: "block" }}>2 · Permisos de Instagram en la app<span style={{ marginLeft: 8, fontSize: 10.5, fontWeight: 600, letterSpacing: ".04em", textTransform: "uppercase", padding: "2px 6px", borderRadius: 6, background: "#fef3c7", color: "#92400e", verticalAlign: "middle" }}>Obligatorio</span></strong>
              <span className="field-help">Meta los revisa y no se pueden comprobar desde aquí. <b>Pendiente de Meta</b>.</span>
            </div>
          </div>
          <a className="button" href={appsUrl} target="_blank" rel="noreferrer">
            <ExternalLink size={15} /> Abrir permisos en Meta
          </a>
        </div>

        <ol style={{ margin: "14px 0 0", paddingLeft: 20, fontSize: 13, lineHeight: 1.75, color: "#475569" }}>
          <li><b>No hay botón Guardar en esa pantalla.</b> Meta aplica cada cambio al marcarlo; la confirmación es la columna <b>Estado</b> diciendo «Listo para la prueba».</li>
          <li>En el desplegable de arriba, el caso de uso correcto es <b>«API de Instagram»</b>.</li>
          <li>Si falta alguna función, pulsa <b>«Agregar más a este caso de uso»</b> y agrega: <code style={{ fontSize: 12 }}>instagram_basic · instagram_content_publish · instagram_manage_messages · instagram_manage_comments</code></li>
          <li>Para publicar también en la <b>Página de Facebook</b> (condicional: solo si vas a publicar ahí), agrega el caso de uso «Administrar todos los aspectos de tu página» con <code style={{ fontSize: 12 }}>pages_show_list · pages_manage_posts · business_management</code></li>
          <li><b>«Listo para la prueba» no es aprobado:</b> solo funciona con usuarios con rol en la app. Para clientes reales necesitas verificación de negocio, acceso avanzado de cada permiso y la app publicada.</li>
          <li>Cuando termines, pulsa <b>Comprobar estado</b> (arriba a la derecha): si sigue en ámbar, Meta no está devolviendo los permisos.</li>
        </ol>
      </section>

      <section style={{ border: "1px solid #e4e8ee", borderRadius: 12, background: "#fff", padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", background: connected ? "#16a34a" : "#dc2626", color: "#fff", flex: "none" }}>
              {connected ? <Check size={14} /> : <X size={14} />}
            </span>
            <div>
              <strong style={{ display: "block" }}>3 · Conectar la cuenta del cliente<span style={{ marginLeft: 8, fontSize: 10.5, fontWeight: 600, letterSpacing: ".04em", textTransform: "uppercase", padding: "2px 6px", borderRadius: 6, background: "#fef3c7", color: "#92400e", verticalAlign: "middle" }}>Obligatorio</span></strong>
              <span className="field-help">
                {connected
                  ? `Cuenta conectada${channel?.username ? `: @${channel.username}` : ""}.`
                  : options?.oauth_available
                    ? "El cliente autoriza con su cuenta Business de Instagram."
                    : "Falta el App ID o el secret del bloque 1: sin eso el botón no puede salir a Meta."}
              </span>
            </div>
          </div>
          <button type="button" className="button primary" onClick={connect} disabled={connecting}>
            {connecting ? <LoaderCircle className="spin" size={15} /> : null}
            {connecting ? "Abriendo Meta…" : connected ? "Reconectar" : "Conectar con Instagram"}
          </button>
        </div>

        <ol style={{ margin: "14px 0 0", paddingLeft: 20, fontSize: 13, lineHeight: 1.75, color: "#475569" }}>
          <li><b>Requisito:</b> los datos del bloque 1 ya guardados (dominio, URI de redirección y tu usuario como tester).</li>
          <li>Pulsa <b>«Conectar con Instagram»</b>: se abre una <b>ventana nueva</b> con Meta; esta pantalla no se cierra.</li>
          <li>Inicia sesión con la cuenta que administra el Instagram del cliente. Debe ser <b>Business o Creator</b> vinculada a una Página.</li>
          <li>Acepta los permisos. La ventana vuelve sola a <code style={{ fontSize: 12 }}>/api/instagram/oauth/callback</code>.</li>
          <li>Vuelve a esta pestaña y pulsa <b>Comprobar estado</b>: el bloque queda en verde con el <b>@usuario</b>.</li>
        </ol>
      </section>

      <section style={{ border: "1px solid #e4e8ee", borderRadius: 12, background: "#fff", padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", background: channel?.page_id ? "#16a34a" : "#dc2626", color: "#fff", flex: "none" }}>
              {channel?.page_id ? <Check size={14} /> : <X size={14} />}
            </span>
            <div>
              <strong style={{ display: "block" }}>4 · Página de Facebook vinculada<span style={{ marginLeft: 8, fontSize: 10.5, fontWeight: 600, letterSpacing: ".04em", textTransform: "uppercase", padding: "2px 6px", borderRadius: 6, background: "#e2e8f0", color: "#334155", verticalAlign: "middle" }}>Condicional</span></strong>
              <span className="field-help">
                {channel?.page_id ? `Página ${channel.page_id} vinculada.` : "Instagram exige una Página vinculada. Sin ella la publicación falla."}
              </span>
            </div>
          </div>
          <a className="button" href="https://business.facebook.com/settings/pages" target="_blank" rel="noreferrer">
            <ExternalLink size={15} /> Abrir Páginas en Meta
          </a>
        </div>

        <ol style={{ margin: "14px 0 0", paddingLeft: 20, fontSize: 13, lineHeight: 1.75, color: "#475569" }}>
          <li>En Meta abre <b>Configuración del negocio → Cuentas → Páginas</b>.</li>
          <li>Comprueba que exista una <b>Página de Facebook</b> del cliente. Si no existe, créala ahí mismo.</li>
          <li>Entra en <b>Instagram → Cuentas de Instagram</b> y vincula la cuenta Business a esa Página.</li>
          <li>Vuelve aquí y pulsa <b>Comprobar estado</b>: el bloque solo se pone en verde cuando el canal devuelve el <b>page_id</b>.</li>
        </ol>
      </section>

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

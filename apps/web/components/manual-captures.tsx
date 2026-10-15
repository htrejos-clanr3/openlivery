"use client";

import type { ReactNode } from "react";
import type { ManualLessonId } from "@/lib/playground-manual-lessons";

function ShotFrame({ url, children }: { url: string; children: ReactNode }) {
  return (
    <div className="shot-frame">
      <div className="shot-chrome" aria-hidden>
        <b /><b /><b />
        <span>{url}</span>
      </div>
      {children}
    </div>
  );
}

export function ManualCaptureScene({ kind }: { kind: ManualLessonId }) {
  switch (kind) {
    case "map":
      return (
        <ShotFrame url="fast-livery.app — capas">
          <div className="shot-map">
            <article><small>1</small><strong>Cliente</strong><span>DNA, marca, portal</span></article>
            <span className="shot-arrow">→</span>
            <article><small>2</small><strong>Agente</strong><span>Brief, Q&A, modelo</span></article>
            <span className="shot-arrow">→</span>
            <article><small>3</small><strong>Canal</strong><span>Playground · WA · IG · LI</span></article>
          </div>
        </ShotFrame>
      );
    case "home":
      return (
        <ShotFrame url="fast-livery.app/inicio">
          <div className="shot-app">
            <aside>
              <b>Fast Livery</b>
              <i className="on">Inicio</i>
              <i>Clientes</i>
              <i>Agentes</i>
              <i>Carruseles</i>
              <i>Playground</i>
              <em>ES · tú</em>
            </aside>
            <main>
              <h4>Inicio</h4>
              <ol>
                <li className="on">Crear un cliente</li>
                <li>Crear un agente</li>
                <li>Guardar clave de IA</li>
              </ol>
              <div className="shot-cards"><span /><span /><span /><span /></div>
            </main>
          </div>
        </ShotFrame>
      );
    case "clients":
      return (
        <ShotFrame url="fast-livery.app/clientes/nuevo">
          <div className="shot-form">
            <header className="shot-form-head">
              <h4>Nuevo cliente</h4>
              <span className="shot-toggle">Activo</span>
            </header>
            <label>Nombre<input readOnly value="Restaurante La Casona" /></label>
            <label>Industria<input readOnly value="Restaurantes" /></label>
            <label>Contexto general<textarea readOnly value="Menú italiano, reservas, no prometas descuentos que no existen." /></label>
            <button type="button">Crear cliente</button>
          </div>
        </ShotFrame>
      );
    case "agents":
      return (
        <ShotFrame url="fast-livery.app/agentes">
          <div className="shot-app">
            <aside>
              <b>Mesero Virtual</b>
              <i>Detalles</i>
              <i className="on">Conocimiento</i>
              <i>Herramientas</i>
              <i>Playground</i>
            </aside>
            <main>
              <header className="shot-form-head">
                <nav><span>Detalles</span><span className="on">Conocimiento</span><span>Widget</span></nav>
                <span className="shot-publish">Publicar</span>
              </header>
              <p>Q&A · ¿Horario? Lun–Dom 12:00–22:00</p>
              <p>PDF · menu-casona.pdf</p>
            </main>
          </div>
        </ShotFrame>
      );
    case "keys":
      return (
        <ShotFrame url="fast-livery.app/configuracion">
          <div className="shot-form">
            <header className="shot-form-head">
              <h4>Configuración · Proveedores</h4>
              <span className="shot-help">Ayuda</span>
            </header>
            <label>Agencia / logo<input readOnly value="Fast Livery" /></label>
            <label>OpenAI<input readOnly value="sk-••••••••••••" /></label>
            <button type="button">Guardar clave</button>
          </div>
        </ShotFrame>
      );
    case "chat":
      return (
        <ShotFrame url="fast-livery.app/playground">
          <div className="shot-app">
            <aside>
              <label>Cliente<select disabled><option>La Casona</option></select></label>
              <label>Agente<select disabled><option>Mesero Virtual</option></select></label>
              <small>Conversaciones</small>
            </aside>
            <main className="shot-chat">
              <header className="shot-form-head">
                <span>Prueba · La Casona</span>
                <em>Humano</em>
              </header>
              <div className="you">¿Tienen lasagna hoy?</div>
              <div className="bot">Sí, lasagna de la casa. ¿Para cuántas personas?</div>
              <div className="shot-composer">Escribe un mensaje…</div>
            </main>
          </div>
        </ShotFrame>
      );
    case "inbox":
      return (
        <ShotFrame url="fast-livery.app/inbox">
          <div className="shot-app">
            <aside>
              <b>Inbox</b>
              <small className="shot-filter">Filtro · WhatsApp</small>
              <i className="on">WhatsApp · Ana</i>
              <i>Playground · prueba</i>
            </aside>
            <main>
              <header className="shot-form-head">
                <span>Ana · WhatsApp</span>
                <em>Humano</em>
              </header>
              <p>El agente no supo la reserva. Tú tomas el hilo.</p>
            </main>
          </div>
        </ShotFrame>
      );
    case "carousels":
      return (
        <ShotFrame url="fast-livery.app/carruseles/nuevo">
          <div className="shot-form shot-wide">
            <header className="shot-form-head">
              <h4>Nuevo carrusel</h4>
              <span className="shot-toggle">Imágenes</span>
            </header>
            <label>Idea<input readOnly value="Menú de la semana" /></label>
            <div className="shot-playbook">
              <strong>Formato Instagram</strong>
              <span>Fidelizar · Un CTA · Hook + enganche</span>
              <em>Comenta MENÚ</em>
            </div>
            <button type="button">Generar</button>
          </div>
        </ShotFrame>
      );
    case "campaign":
      return (
        <ShotFrame url="fast-livery.app/instagram/compose">
          <div className="shot-form">
            <h4>Nueva publicación</h4>
            <div className="shot-types"><i className="on">Carrusel</i><i>Imagen</i><i>Reel</i></div>
            <label>Caption<textarea readOnly value="Esta semana: lasagna de la casa." /></label>
            <label>CTA<input readOnly value="Comenta MENÚ" /></label>
            <button type="button">Generar con IA</button>
          </div>
        </ShotFrame>
      );
    case "linkedin":
      return (
        <ShotFrame url="fast-livery.app/canales/linkedin">
          <div className="shot-form shot-wide">
            <header className="shot-form-head">
              <h4>LinkedIn · perfil personal</h4>
              <span className="shot-toggle">API oficial</span>
            </header>
            <div className="shot-playbook">
              <strong>1 · Conectar con LinkedIn</strong>
              <span>OAuth · openid · profile · w_member_social</span>
            </div>
            <label>Texto final<textarea readOnly value="Un hecho real, revisado y listo para publicar." /></label>
            <label className="switch-row"><span><strong>Revisé este texto exacto</strong></span><input type="checkbox" role="switch" readOnly checked /></label>
            <button type="button">Publicar texto aprobado</button>
          </div>
        </ShotFrame>
      );
    case "live":
      return (
        <ShotFrame url="fast-livery.app/canales">
          <div className="shot-map shot-channels">
            <article><strong>WhatsApp</strong><span>Guía paso a paso</span></article>
            <article><strong>Instagram</strong><span>Login o avanzado</span></article>
            <article className="on"><strong>Portal</strong><span>El cliente aprueba</span></article>
          </div>
        </ShotFrame>
      );
    default:
      return null;
  }
}

export const metadata = {
  title: "Política de privacidad · Fast Livery",
  description: "Cómo Fast Livery trata los datos personales de agencias, clientes y personas que escriben por WhatsApp.",
};

export default function PrivacyPage() {
  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "48px 24px 80px", lineHeight: 1.7, color: "#0f172a" }}>
      <p style={{ color: "#64748b", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>
        Fast Livery
      </p>
      <h1 style={{ fontSize: 30, margin: "6px 0 4px" }}>Política de privacidad</h1>
      <p style={{ color: "#64748b", margin: "0 0 32px" }}>Última actualización: 9 de noviembre de 2026</p>

      <Section title="1. Quién es el responsable">
        <p>
          Fast Livery es una plataforma operada por R3 Soluciones Informáticas que permite a agencias de
          marketing y ventas gestionar la atención de sus clientes por WhatsApp, calificar contactos y agendar
          citas. El responsable del tratamiento de los datos de cada cliente final es la agencia o empresa que
          contrata el servicio; Fast Livery actúa como encargado del tratamiento por cuenta de esa agencia.
        </p>
        <p>
          Contacto para asuntos de privacidad: <a href="mailto:privacidad@r3soluciones.com">privacidad@r3soluciones.com</a>
        </p>
      </Section>

      <Section title="2. Qué datos tratamos">
        <ul>
          <li><b>Datos de cuenta:</b> nombre, correo electrónico, agencia y rol de las personas que usan el panel.</li>
          <li><b>Datos de contacto de clientes finales:</b> número de teléfono de WhatsApp, nombre de perfil, contenido de los mensajes y, cuando se agenda, la cita acordada.</li>
          <li><b>Datos de configuración de canales:</b> identificadores de cuenta de WhatsApp Business, de Página de Facebook y de Instagram, y tokens de acceso cifrados.</li>
          <li><b>Datos técnicos:</b> registros de acceso, dirección IP y eventos de uso necesarios para operar y asegurar el servicio.</li>
        </ul>
        <p>
          No recopilamos datos de categorías especiales ni datos de menores de edad. No pedimos contraseñas de
          redes sociales: el acceso a canales se realiza mediante autorización OAuth de la plataforma
          correspondiente.
        </p>
      </Section>

      <Section title="3. Para qué los usamos">
        <ul>
          <li>Prestar el servicio: recibir mensajes, responder con agentes de IA, calificar contactos y agendar citas.</li>
          <li>Permitir que una persona del equipo de la agencia continúe una conversación cuando el agente no puede resolverla.</li>
          <li>Enviar notificaciones operativas y recordatorios de citas solicitados por la agencia.</li>
          <li>Seguridad: detectar abuso, fraude y accesos no autorizados.</li>
          <li>Facturación y soporte del servicio contratado por la agencia.</li>
        </ul>
      </Section>

      <Section title="4. Con quién los compartimos">
        <p>
          Solo con proveedores necesarios para operar, cada uno con su propio contrato y medidas de seguridad:
        </p>
        <ul>
          <li><b>Meta Platforms</b> (WhatsApp Cloud API, Instagram y Facebook), para enviar y recibir mensajes y publicar contenido autorizado por el cliente.</li>
          <li><b>Proveedores de modelos de lenguaje</b> configurados por cada agencia, que procesan el texto de los mensajes para generar respuestas. La agencia elige el proveedor y puede cambiarlo.</li>
          <li><b>Proveedor de infraestructura</b> que aloja la base de datos y los servicios.</li>
          <li><b>Proveedor de correo</b> para el envío de notificaciones y recuperación de acceso.</li>
        </ul>
        <p>
          No vendemos datos personales, no los usamos para publicidad de terceros y no los cedemos fuera de las
          finalidades descritas.
        </p>
      </Section>

      <Section title="5. Cuánto tiempo los conservamos">
        <p>
          Los datos de cuenta se conservan mientras exista la relación contractual. Las conversaciones y citas se
          conservan mientras la agencia mantenga el servicio activo; la agencia puede solicitar su eliminación en
          cualquier momento. Los registros técnicos se conservan hasta 12 meses por razones de seguridad.
        </p>
      </Section>

      <Section title="6. Tus derechos">
        <p>
          Cualquier persona puede solicitar acceso, corrección, actualización o eliminación de sus datos, así como
          oponerse a su tratamiento. Las solicitudes se atienden escribiendo a{" "}
          <a href="mailto:privacidad@r3soluciones.com">privacidad@r3soluciones.com</a>, indicando el número de
          teléfono con el que se contactó al negocio. Respondemos en un plazo máximo de 15 días hábiles.
        </p>
      </Section>

      <Section title="7. Eliminación de datos">
        <p>
          Para eliminar los datos asociados a una conversación de WhatsApp, envía un mensaje con la palabra{" "}
          <b>ELIMINAR</b> al mismo número con el que escribiste, o solicítalo por correo. Eliminamos los registros
          de conversación, el contacto y su historial de citas en un plazo máximo de 30 días.
        </p>
        <p>
          Las agencias pueden eliminar un cliente completo, con sus conversaciones y contactos, desde el panel o
          escribiendo a la misma dirección.
        </p>
      </Section>

      <Section title="8. Seguridad">
        <p>
          Los tokens de acceso a canales se guardan cifrados con una clave que no se transmite al navegador. El
          acceso al panel requiere autenticación y cada consulta se limita a la agencia del usuario autenticado,
          de modo que una agencia no puede ver datos de otra.
        </p>
      </Section>

      <Section title="9. Cookies">
        <p>
          Usamos únicamente cookies necesarias para mantener la sesión iniciada. No utilizamos cookies de
          publicidad ni de seguimiento entre sitios.
        </p>
      </Section>

      <Section title="10. Cambios">
        <p>
          Si esta política cambia de forma sustancial, lo avisaremos a las agencias por correo antes de que el
          cambio entre en vigor. La fecha de la última actualización aparece al inicio de esta página.
        </p>
      </Section>

      <p style={{ marginTop: 40, fontSize: 13, color: "#64748b" }}>
        Fast Livery · <a href="/login">Iniciar sesión</a> · <a href="mailto:privacidad@r3soluciones.com">privacidad@r3soluciones.com</a>
      </p>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 18, margin: "0 0 8px" }}>{title}</h2>
      <div style={{ fontSize: 15, color: "#334155" }}>{children}</div>
    </section>
  );
}

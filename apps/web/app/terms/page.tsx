export const metadata = {
  title: "Términos del servicio · Fast Livery",
  description: "Condiciones de uso de la plataforma Fast Livery para agencias y sus clientes.",
};

export default function TermsPage() {
  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "48px 24px 80px", lineHeight: 1.7, color: "#0f172a" }}>
      <p style={{ color: "#64748b", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>Fast Livery</p>
      <h1 style={{ fontSize: 30, margin: "6px 0 4px" }}>Términos del servicio</h1>
      <p style={{ color: "#64748b", margin: "0 0 32px" }}>Última actualización: 9 de noviembre de 2026</p>

      <Section title="1. Qué es el servicio">
        <p>
          Fast Livery es una plataforma para agencias de marketing y ventas que permite atender conversaciones de
          WhatsApp con agentes de inteligencia artificial, calificar contactos, agendar citas y publicar contenido
          en los canales que el cliente autorice. El servicio se presta por suscripción y se accede por web.
        </p>
      </Section>

      <Section title="2. Cuentas y responsabilidad de la agencia">
        <p>
          La agencia que contrata el servicio es responsable de las cuentas de sus clientes, de la veracidad de los
          datos que carga y del uso que haga de las conversaciones. Debe contar con autorización de cada cliente
          para conectar sus canales de WhatsApp, Instagram o Facebook.
        </p>
        <p>
          Cada usuario accede con sus propias credenciales. Está prohibido compartir el acceso o usar el servicio
          para enviar mensajes no solicitados, contenido ilegal o suplantar identidades.
        </p>
      </Section>

      <Section title="3. Canales de terceros">
        <p>
          El envío de mensajes y la publicación dependen de las políticas y los límites de Meta Platforms. Si Meta
          suspende una cuenta, cambia sus requisitos o revoca permisos, el servicio correspondiente puede dejar de
          funcionar sin que eso constituya un incumplimiento de estos términos.
        </p>
      </Section>

      <Section title="4. Uso aceptable">
        <ul>
          <li>No enviar mensajes masivos sin consentimiento de los destinatarios.</li>
          <li>No usar el servicio para acosar, discriminar o difundir desinformación.</li>
          <li>No intentar acceder a datos de otra agencia ni eludir el aislamiento del sistema.</li>
          <li>Respetar los tiempos de respuesta y los horarios que el propio cliente configure.</li>
        </ul>
      </Section>

      <Section title="5. Inteligencia artificial">
        <p>
          Las respuestas pueden generarse con modelos de lenguaje de proveedores configurados por la agencia. La
          agencia es responsable del contenido que se publica y de revisar lo que el agente propone cuando el
          proceso lo permita.
        </p>
      </Section>

      <Section title="6. Disponibilidad y soporte">
        <p>
          Procuramos mantener el servicio disponible de forma continua, con ventanas de mantenimiento programadas
          cuando sean necesarias. No garantizamos disponibilidad ininterrumpida ni la conservación de datos más
          allá de los plazos indicados en la política de privacidad.
        </p>
      </Section>

      <Section title="7. Pagos y cancelación">
        <p>
          La suscripción se cobra por el período contratado. La agencia puede cancelar en cualquier momento; el
          servicio se mantiene hasta el final del período pagado y después se desactiva el acceso. Los datos se
          conservan el tiempo descrito en la política de privacidad y luego se eliminan.
        </p>
      </Section>

      <Section title="8. Limitación de responsabilidad">
        <p>
          En la medida permitida por la ley, no respondemos por lucro cesante, pérdida de oportunidades ni daños
          indirectos derivados del uso del servicio. La responsabilidad total se limita al importe pagado en los
          últimos doce meses.
        </p>
      </Section>

      <Section title="9. Cambios">
        <p>
          Podemos actualizar estos términos por cambios legales o del producto. Avisaremos a las agencias por correo
          antes de que entren en vigor. La fecha de la última actualización aparece al inicio de esta página.
        </p>
      </Section>

      <Section title="10. Contacto">
        <p>
          Para asuntos legales o comerciales: <a href="mailto:privacidad@r3soluciones.com">privacidad@r3soluciones.com</a>
        </p>
      </Section>

      <p style={{ marginTop: 40, fontSize: 13, color: "#64748b" }}>
        Fast Livery · <a href="/privacy">Política de privacidad</a> · <a href="/data-deletion">Eliminación de datos</a>
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

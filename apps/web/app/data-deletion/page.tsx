export const metadata = {
  title: "Eliminación de datos · Fast Livery",
  description: "Cómo solicitar la eliminación de los datos asociados a una conversación de WhatsApp, Instagram o Facebook.",
};

export default function DataDeletionPage() {
  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "48px 24px 80px", lineHeight: 1.7, color: "#0f172a" }}>
      <p style={{ color: "#64748b", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>Fast Livery</p>
      <h1 style={{ fontSize: 30, margin: "6px 0 4px" }}>Eliminación de datos</h1>
      <p style={{ color: "#64748b", margin: "0 0 32px" }}>Última actualización: 9 de noviembre de 2026</p>

      <Section title="Cómo pedir la eliminación">
        <p>Hay tres caminos, según quién seas:</p>
        <ol>
          <li>
            <b>Si escribiste por WhatsApp, Instagram o Facebook a un negocio</b> que usa Fast Livery: envía un
            mensaje con la palabra <b>ELIMINAR</b> al mismo número o cuenta con la que te contactaron.
          </li>
          <li>
            <b>Si eres cliente y quieres borrar todos tus datos</b>: escribe a{" "}
            <a href="mailto:privacidad@r3soluciones.com?subject=Eliminacion%20de%20datos">privacidad@r3soluciones.com</a>{" "}
            con el número de teléfono o usuario con el que te contactaron.
          </li>
          <li>
            <b>Si eres la agencia</b>: puedes eliminar un cliente completo, con sus conversaciones, contactos y
            citas, desde el panel o solicitándolo por correo.
          </li>
        </ol>
      </Section>

      <Section title="Qué se elimina">
        <ul>
          <li>El contenido de las conversaciones y los mensajes.</li>
          <li>El contacto: número, nombre de perfil y etiquetas.</li>
          <li>El historial de citas y de seguimientos asociados a ese contacto.</li>
          <li>Los datos de canal vinculados al contacto, cuando corresponda.</li>
        </ul>
        <p>
          No eliminamos los registros de facturación que la ley obliga a conservar, ni datos anónimos de uso que
          ya no permiten identificar a una persona.
        </p>
      </Section>

      <Section title="Plazo">
        <p>
          Confirmamos la solicitud en un máximo de <b>5 días hábiles</b> y completamos la eliminación en un máximo
          de <b>30 días</b>. Te avisamos por el mismo medio por el que hiciste la solicitud.
        </p>
      </Section>

      <Section title="Verificación">
        <p>
          Para evitar eliminar datos de otra persona, podemos pedirte que confirmes desde el mismo número o cuenta
          que usaste en la conversación. Nunca pedimos contraseñas ni datos de tarjeta.
        </p>
      </Section>

      <Section title="Contacto">
        <p>
          <a href="mailto:privacidad@r3soluciones.com">privacidad@r3soluciones.com</a> · Fast Livery, R3 Soluciones
          Informáticas.
        </p>
      </Section>

      <p style={{ marginTop: 40, fontSize: 13, color: "#64748b" }}>
        Fast Livery · <a href="/privacy">Política de privacidad</a> · <a href="/terms">Términos del servicio</a>
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

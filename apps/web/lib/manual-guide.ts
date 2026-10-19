export type GuideStep = {
  title: string;
  body: string[];
  result: string;
  href: string;
};

export type GuideIntegration = {
  name: string;
  what: string;
  where: string;
  needs: string;
};

export type GuideCopy = {
  eyebrow: string;
  title: string;
  intro: string;
  printLabel: string;
  whatTitle: string;
  what: string[];
  stepsTitle: string;
  stepsIntro: string;
  resultLabel: string;
  openLabel: string;
  steps: GuideStep[];
  integrationsTitle: string;
  integrationsIntro: string;
  colName: string;
  colWhat: string;
  colWhere: string;
  colNeeds: string;
  integrations: GuideIntegration[];
  errorsTitle: string;
  errors: { problem: string; fix: string }[];
  footer: string;
};

const en: GuideCopy = {
  eyebrow: "Operations manual",
  title: "How Fast Livery works",
  intro:
    "Fast Livery is your agency's platform. Every client gets AI agents that answer on WhatsApp and the web, a shared inbox where your team takes over, leads that arrive on their own, and content published to Instagram and LinkedIn.",
  printLabel: "Print or save as PDF",
  whatTitle: "The four moving parts",
  what: [
    "A client is an isolated space with its agents, channels, conversations, leads and portal.",
    "An agent is instructions plus knowledge, tools and an AI provider.",
    "A channel is WhatsApp (QR or Meta Cloud), the web widget or the client portal.",
    "The inbox holds every conversation; the AI answers unless an operator takes control.",
  ],
  stepsTitle: "Step by step",
  stepsIntro: "Do them in order the first time. Each step links to the real screen.",
  resultLabel: "You should see",
  openLabel: "Open",
  steps: [
    {
      title: "Create the client",
      body: [
        "Name and industry identify the workspace.",
        "General context is the raw material for every agent: what they sell, to whom, in what tone.",
        "Save; the portal slug is generated from the name.",
      ],
      result: "The client appears in the list with its own portal slug.",
      href: "/clients/new",
    },
    {
      title: "Create the agent",
      body: [
        "Assign it to the client.",
        "Write instructions as a brief for a new hire, not as a prompt trick.",
        "Fill products, audience and policies; pick model and temperature.",
      ],
      result: "An active agent that answers with the client's context.",
      href: "/agents/new",
    },
    {
      title: "Add knowledge and tools",
      body: [
        "Upload PDFs: they are split, embedded and retrieved on demand.",
        "Add HTTP or MCP tools when the agent must query a real system.",
        "Enable image or audio only if the channel sends media.",
      ],
      result: "Answers grounded in your documents, with sources shown in the playground.",
      href: "/agents",
    },
    {
      title: "Connect an AI provider",
      body: [
        "Paste an OpenAI, DeepSeek or compatible API key.",
        "Use a base URL for self-hosted or local gateways.",
        "Run the connection test before leaving the page.",
      ],
      result: "The credential is stored encrypted and the agent can reply.",
      href: "/settings",
    },
    {
      title: "Test in the Playground",
      body: [
        "Pick client, agent and channel.",
        "Ask a real customer question, then a hostile one.",
        "Check sources and tool calls under the answer.",
      ],
      result: "A coherent reply you would be comfortable sending.",
      href: "/playground",
    },
    {
      title: "Connect WhatsApp Business (Cloud API)",
      body: [
        "Open the client's WhatsApp Business channel.",
        "Use Connect with Meta, or paste phone number ID, WABA, token and app secret.",
        "Save and verify; the webhook registers itself and can be retried.",
      ],
      result: "Channel connected, webhook registered on the number, health card green.",
      href: "/clients",
    },
    {
      title: "Or connect WhatsApp by QR",
      body: [
        "Open the QR channel for the client.",
        "Scan from the phone that will answer.",
        "The session is encrypted before it reaches the database.",
      ],
      result: "A live channel without a Meta app.",
      href: "/clients",
    },
    {
      title: "Work the inbox",
      body: [
        "Filter by owner, channel, label or unread.",
        "Take control to answer as a human; the AI stops until you hand it back.",
        "Assign, label, and use saved replies with a leading slash.",
      ],
      result: "Conversations answered on time, with history preserved.",
      href: "/inbox",
    },
    {
      title: "Capture and qualify leads",
      body: [
        "Turn on lead capture and choose sources, pipeline and stage.",
        "Define the ideal customer: sectors, cities, keywords, disqualifiers, thresholds.",
        "Qualify all, or import a CSV; each lead gets a 0-100 score with reasons.",
      ],
      result: "A pipeline ordered by fit, not by arrival order.",
      href: "/clients",
    },
    {
      title: "Publish to Instagram and LinkedIn",
      body: [
        "Generate the carousel with the client's brand DNA.",
        "Approve slides before publishing.",
        "Connect each channel with OAuth when you want real publishing.",
      ],
      result: "A published post, tracked per slide and network.",
      href: "/carousels",
    },
    {
      title: "Open the portal and the widget",
      body: [
        "Enable the client portal, optionally on a verified custom domain.",
        "Set the widget colour and greeting for the website.",
        "Share the URL; the client signs in on their own.",
      ],
      result: "Self-service access without giving anyone your agency login.",
      href: "/clients",
    },
    {
      title: "Close with legal consent",
      body: [
        "Registration and channel connections record consent.",
        "Acceptances are audited per user, platform and channel.",
        "Review them before onboarding a regulated client.",
      ],
      result: "A traceable consent history.",
      href: "/settings",
    },
  ],
  integrationsTitle: "Integrations and plugins",
  integrationsIntro: "What each one unlocks and where it is configured.",
  colName: "Integration",
  colWhat: "What it unlocks",
  colWhere: "Where",
  colNeeds: "Requires",
  integrations: [
    { name: "OpenAI", what: "Replies, vision and audio", where: "Settings", needs: "API key" },
    { name: "DeepSeek or OpenAI-compatible", what: "Alternative model or gateway", where: "Settings", needs: "API key and base URL" },
    { name: "Ollama", what: "Local models with no per-token cost", where: "Settings", needs: "Server URL" },
    { name: "WhatsApp Cloud (Meta)", what: "Official channel, templates, signed webhook", where: "Client > WhatsApp Business", needs: "Meta app, WABA, token, app secret" },
    { name: "WhatsApp QR (bridge)", what: "A channel without a Meta app", where: "Client > WhatsApp", needs: "Scan the QR" },
    { name: "Instagram", what: "Publish carousels and campaigns", where: "Client > Instagram", needs: "Professional account linked to a Page" },
    { name: "LinkedIn", what: "Publish posts", where: "Client > LinkedIn", needs: "OAuth, or mock mode" },
    { name: "Meta DevTools MCP", what: "Inspect and health-check Meta apps", where: "Settings > Meta", needs: "Optional token" },
    { name: "HTTP tools", what: "Call the client's own APIs", where: "Agent > Tools", needs: "URL and headers" },
    { name: "MCP tools", what: "Attach MCP servers", where: "Agent > Tools", needs: "Endpoint" },
    { name: "Image providers (HF, FLUX, Ollama)", what: "Carousel slides", where: "Settings", needs: "Provider and token" },
    { name: "Lead capture (form or webhook)", what: "Leads from any external system", where: "Client > Leads", needs: "Ingest token" },
    { name: "Portal and web widget", what: "Client self-service and web chat", where: "Client > Portal / Widget", needs: "Nothing" },
  ],
  errorsTitle: "Common errors and their fix",
  errors: [
    { problem: "The agent replies that no provider is configured.", fix: "Add an API key in Settings and run the connection test." },
    { problem: "Meta says the webhook cannot be verified.", fix: "Verify token and app secret must match the channel exactly." },
    { problem: "The QR channel disconnects.", fix: "The WhatsApp Web session expired: reconnect and scan again." },
    { problem: "Instagram refuses to publish.", fix: "The account must be professional and the token must carry publishing scope." },
    { problem: "The carousel has no images.", fix: "Configure an image provider in Settings before generating." },
    { problem: "Opening the LinkedIn channel showed an error.", fix: "Fixed: two simultaneous loads no longer collide on the same row." },
  ],
  footer: "Technical installation and backups live in the self-hosting documentation.",
};

const es: GuideCopy = {
  eyebrow: "Manual de operación",
  title: "Cómo funciona Fast Livery",
  intro:
    "Fast Livery es la plataforma de tu agencia. Cada cliente tiene agentes de IA que atienden en WhatsApp y en la web, un inbox compartido donde tu equipo toma el control, leads que entran solos y contenido que se publica en Instagram y LinkedIn.",
  printLabel: "Imprimir o guardar en PDF",
  whatTitle: "Las cuatro piezas",
  what: [
    "Un cliente es un espacio aislado con sus agentes, canales, conversaciones, leads y portal.",
    "Un agente es instrucciones más conocimiento, herramientas y un proveedor de IA.",
    "Un canal es WhatsApp (QR o Meta Cloud), el widget web o el portal del cliente.",
    "El inbox reúne todas las conversaciones; la IA responde salvo que un operador tome el control.",
  ],
  stepsTitle: "Paso a paso",
  stepsIntro: "Hazlos en orden la primera vez. Cada paso enlaza a la pantalla real.",
  resultLabel: "Deberías ver",
  openLabel: "Abrir",
  steps: [
    {
      title: "Crea el cliente",
      body: [
        "Nombre e industria identifican el espacio.",
        "El contexto general alimenta a todos sus agentes: qué vende, a quién, con qué tono.",
        "Guarda; el slug del portal se genera del nombre.",
      ],
      result: "El cliente aparece en la lista con su slug de portal.",
      href: "/clients/new",
    },
    {
      title: "Crea el agente",
      body: [
        "Asígnalo al cliente.",
        "Escribe las instrucciones como un brief para alguien nuevo, no como un truco de prompt.",
        "Completa productos, audiencia y políticas; elige modelo y temperatura.",
      ],
      result: "Un agente activo que responde con el contexto del cliente.",
      href: "/agents/new",
    },
    {
      title: "Carga conocimiento y herramientas",
      body: [
        "Sube PDFs: se trocean, se convierten en vectores y se recuperan bajo demanda.",
        "Añade herramientas HTTP o MCP si el agente debe consultar un sistema real.",
        "Activa imagen o audio solo si el canal envía multimedia.",
      ],
      result: "Respuestas ancladas en tus documentos, con fuentes visibles en el playground.",
      href: "/agents",
    },
    {
      title: "Conecta un proveedor de IA",
      body: [
        "Pega una clave de OpenAI, DeepSeek o compatible.",
        "Usa base URL si es un gateway self-hosted o local.",
        "Prueba la conexión antes de salir de la página.",
      ],
      result: "La credencial queda cifrada y el agente puede responder.",
      href: "/settings",
    },
    {
      title: "Prueba en el Playground",
      body: [
        "Elige cliente, agente y canal.",
        "Haz una pregunta real de cliente y después una hostil.",
        "Revisa fuentes y llamadas a herramientas debajo de la respuesta.",
      ],
      result: "Una respuesta coherente que enviarías sin vergüenza.",
      href: "/playground",
    },
    {
      title: "Conecta WhatsApp Business (Cloud API)",
      body: [
        "Abre el canal WhatsApp Business del cliente.",
        "Usa Conectar con Meta, o pega phone number ID, WABA, token y app secret.",
        "Guarda y verifica; el webhook se registra solo y se puede reintentar.",
      ],
      result: "Canal conectado, webhook registrado en el número, tarjeta de salud en verde.",
      href: "/clients",
    },
    {
      title: "O conecta WhatsApp por QR",
      body: [
        "Abre el canal QR del cliente.",
        "Escanea desde el teléfono que va a responder.",
        "La sesión se cifra antes de llegar a la base de datos.",
      ],
      result: "Un canal en vivo sin necesidad de una Meta App.",
      href: "/clients",
    },
    {
      title: "Trabaja el inbox",
      body: [
        "Filtra por responsable, canal, etiqueta o no leídos.",
        "Toma el control para responder como humano; la IA se detiene hasta que se lo devuelvas.",
        "Asigna, etiqueta y usa respuestas guardadas con una barra inicial.",
      ],
      result: "Conversaciones atendidas a tiempo, con historial intacto.",
      href: "/inbox",
    },
    {
      title: "Captura y califica leads",
      body: [
        "Activa la captura y elige fuentes, pipeline y etapa inicial.",
        "Define el cliente ideal: sectores, ciudades, palabras clave, descartes y umbrales.",
        "Califica todos o importa un CSV; cada lead recibe un score de 0 a 100 con razones.",
      ],
      result: "Un pipeline ordenado por encaje, no por orden de llegada.",
      href: "/clients",
    },
    {
      title: "Publica en Instagram y LinkedIn",
      body: [
        "Genera el carrusel con la identidad de marca del cliente.",
        "Aprueba las láminas antes de publicar.",
        "Conecta cada canal con OAuth cuando quieras publicar de verdad.",
      ],
      result: "Una publicación hecha, con seguimiento por lámina y por red.",
      href: "/carousels",
    },
    {
      title: "Abre el portal y el widget",
      body: [
        "Activa el portal del cliente, opcionalmente en un dominio propio verificado.",
        "Define color y saludo del widget para su web.",
        "Comparte la URL; el cliente entra por su cuenta.",
      ],
      result: "Autoservicio sin prestar tu usuario de agencia.",
      href: "/clients",
    },
    {
      title: "Cierra con consentimiento legal",
      body: [
        "El registro y la conexión de canales registran consentimiento.",
        "Las aceptaciones quedan auditadas por usuario, plataforma y canal.",
        "Revísalas antes de incorporar un cliente regulado.",
      ],
      result: "Un historial de consentimiento trazable.",
      href: "/settings",
    },
  ],
  integrationsTitle: "Integraciones y plugins",
  integrationsIntro: "Qué desbloquea cada una y dónde se configura.",
  colName: "Integración",
  colWhat: "Qué desbloquea",
  colWhere: "Dónde",
  colNeeds: "Requiere",
  integrations: [
    { name: "OpenAI", what: "Respuestas, visión y audio", where: "Configuración", needs: "API key" },
    { name: "DeepSeek o compatible con OpenAI", what: "Modelo alternativo o gateway", where: "Configuración", needs: "API key y base URL" },
    { name: "Ollama", what: "Modelos locales sin costo por token", where: "Configuración", needs: "URL del servidor" },
    { name: "WhatsApp Cloud (Meta)", what: "Canal oficial, plantillas y webhook firmado", where: "Cliente > WhatsApp Business", needs: "Meta App, WABA, token, app secret" },
    { name: "WhatsApp QR (puente)", what: "Un canal sin Meta App", where: "Cliente > WhatsApp", needs: "Escanear el QR" },
    { name: "Instagram", what: "Publicar carruseles y campañas", where: "Cliente > Instagram", needs: "Cuenta profesional ligada a una Página" },
    { name: "LinkedIn", what: "Publicar posts", where: "Cliente > LinkedIn", needs: "OAuth, o modo mock" },
    { name: "Meta DevTools MCP", what: "Inspeccionar y diagnosticar Meta Apps", where: "Configuración > Meta", needs: "Token opcional" },
    { name: "Herramientas HTTP", what: "Llamar las APIs del cliente", where: "Agente > Herramientas", needs: "URL y cabeceras" },
    { name: "Herramientas MCP", what: "Conectar servidores MCP", where: "Agente > Herramientas", needs: "Endpoint" },
    { name: "Proveedores de imagen (HF, FLUX, Ollama)", what: "Láminas de carrusel", where: "Configuración", needs: "Proveedor y token" },
    { name: "Captura de leads (formulario o webhook)", what: "Leads desde cualquier sistema externo", where: "Cliente > Leads", needs: "Token de ingesta" },
    { name: "Portal y widget web", what: "Autoservicio del cliente y chat web", where: "Cliente > Portal / Widget", needs: "Nada" },
  ],
  errorsTitle: "Errores típicos y su arreglo",
  errors: [
    { problem: "El agente dice que no hay proveedor configurado.", fix: "Añade una API key en Configuración y ejecuta la prueba de conexión." },
    { problem: "Meta no puede verificar el webhook.", fix: "El verify token y el app secret deben coincidir exactamente con el canal." },
    { problem: "El canal QR se desconecta.", fix: "La sesión de WhatsApp Web caducó: reconecta y vuelve a escanear." },
    { problem: "Instagram rechaza la publicación.", fix: "La cuenta debe ser profesional y el token debe traer permiso de publicación." },
    { problem: "El carrusel sale sin imágenes.", fix: "Configura un proveedor de imágenes en Configuración antes de generar." },
    { problem: "Al abrir el canal de LinkedIn salía un error.", fix: "Corregido: dos cargas simultáneas ya no chocan sobre la misma fila." },
  ],
  footer: "La instalación técnica y los respaldos están en la documentación de self-hosting.",
};

export const manualGuide: Record<"en" | "es", GuideCopy> = { en, es };

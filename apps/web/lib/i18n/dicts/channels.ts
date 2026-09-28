// UI strings for the "channels" area. Fill `en` and mirror it in `es`.
const en = {
  head: {
    eyebrow: "Channels",
    title: "Channels",
    description: "Connect each client's number to its own agent and Inbox.",
  },
  toolbar: {
    clientLabel: "Client",
    allClients: "All clients",
    openClient: "Open client",
  },
  whatsappCloud: {
    status: "Available",
    title: "WhatsApp API",
    description:
      "Official WhatsApp Business Cloud API, hosted by Meta. Connect a number with your own Meta app credentials.",
    ownerPlaceholder: "Choose a client to configure its number",
    configure: "Configure WhatsApp API",
    selectClient: "Select a client",
  },
  whatsapp: {
    status: "Available",
    title: "WhatsApp QR",
    description:
      "Scan a QR with the WhatsApp app on your phone, reply with an agent, and let the team take over from the Inbox.",
    ownerPlaceholder: "Choose a client to configure its number",
    configure: "Configure WhatsApp QR",
    selectClient: "Select a client",
  },
  instagram: {
    status: "Available",
    title: "Instagram",
    description:
      "Connect a professional Instagram account per client. Guided Meta login when configured; otherwise a step-by-step guide to paste Graph credentials.",
    ownerPlaceholder: "Choose a client to configure Instagram",
    configure: "Configure Instagram",
    selectClient: "Select a client",
  },
  linkedin: {
    status: "Available · official API",
    title: "LinkedIn",
    description:
      "21 hook formulas, profile rewrite and local humanizer. Connect a personal profile and publish approved text through LinkedIn’s official API.",
    ownerPlaceholder: "Choose a client to open LinkedIn",
    configure: "Open LinkedIn desk",
    selectClient: "Select a client",
  },
  future: {
    comingSoon: "Coming soon",
    ownerPlaceholder: "Configurable inside each client",
    connect: "Connect channel",
    facebook: {
      name: "Facebook Messenger",
      description: "Connect your pages and keep consistent support.",
    },
    webchat: {
      name: "Webchat",
      description: "Embed an assistant on any website with a single line of code.",
    },
  },
  formsWebhook: {
    status: "Available",
    title: "Forms / Webhooks",
    description: "Public endpoint to receive form and webhook leads for this client. Copy the URL, rotate the token, and paste it in Typeform, Tally, Webflow, or your own backend.",
    configure: "Open setup",
    endpoint: "Public endpoint",
    token: "Token",
    copyUrl: "Copy endpoint",
    copied: "Copied",
    rotate: "Rotate token",
    tokenRotated: "Token rotated. Update the form or webhook that posts here.",
    statusLabel: "Status",
    lastReceived: "Last received",
    leadsCreated: "Leads created",
    never: "Never",
    idle: "Waiting for posts",
    payloadTitle: "Example payload",
    payloadHint: "POST JSON. Keep source as form or webhook. Do not share this URL outside this client.",
    guideTitle: "How to connect a form or webhook",
    guideIntro: "There is no OAuth for this channel. You copy the client endpoint and POST JSON from your form tool or backend.",
    step1: "Copy the public endpoint below. It already includes this client's token.",
    step2: "In Typeform, Tally, Webflow, Zapier, or your backend, add a webhook / HTTP request to that URL.",
    step3: "Send JSON with source, name, email, phone, and optional channel_identifier.",
    step4: "Submit a test. Last received and leads created should update here. Open Leads to see the opportunity.",
    step5: "If the token was exposed, rotate it and update the form. The previous URL stops working.",
  },
  note: {
    strong: "Each connection belongs to a single client.",
    rest: "Its number, agent, session, and conversations stay separate from other spaces.",
  },
};

const es: typeof en = {
  head: {
    eyebrow: "Canales",
    title: "Canales",
    description: "Conecta el número de cada cliente con su propio agente e Inbox.",
  },
  toolbar: {
    clientLabel: "Cliente",
    allClients: "Todos los clientes",
    openClient: "Abrir cliente",
  },
  whatsappCloud: {
    status: "Disponible",
    title: "WhatsApp API",
    description:
      "API oficial de WhatsApp Business Cloud, alojada por Meta. Conecta un número con las credenciales de tu propia app de Meta.",
    ownerPlaceholder: "Elige un cliente para configurar su número",
    configure: "Configurar WhatsApp API",
    selectClient: "Selecciona un cliente",
  },
  whatsapp: {
    status: "Disponible",
    title: "WhatsApp QR",
    description:
      "Escanea un QR con la app de WhatsApp de tu teléfono, responde con un agente y permite que el equipo tome el control desde el Inbox.",
    ownerPlaceholder: "Elige un cliente para configurar su número",
    configure: "Configurar WhatsApp QR",
    selectClient: "Selecciona un cliente",
  },
  instagram: {
    status: "Disponible",
    title: "Instagram",
    description:
      "Conecta una cuenta profesional de Instagram por cliente. Login guiado de Meta si está configurado; si no, guía paso a paso para pegar credenciales Graph.",
    ownerPlaceholder: "Elige un cliente para configurar Instagram",
    configure: "Configurar Instagram",
    selectClient: "Selecciona un cliente",
  },
  linkedin: {
    status: "Disponible · API oficial",
    title: "LinkedIn",
    description:
      "21 fórmulas de hook, reescritura de perfil y humanizador local. Conecta un perfil personal y publica texto aprobado con la API oficial.",
    ownerPlaceholder: "Elige un cliente para abrir LinkedIn",
    configure: "Abrir escritorio LinkedIn",
    selectClient: "Selecciona un cliente",
  },
  future: {
    comingSoon: "Próximamente",
    ownerPlaceholder: "Configurable dentro de cada cliente",
    connect: "Conectar canal",
    facebook: {
      name: "Facebook Messenger",
      description: "Conecta tus páginas y mantén una atención consistente.",
    },
    webchat: {
      name: "Webchat",
      description: "Inserta un asistente en cualquier sitio web con una línea de código.",
    },
  },
  formsWebhook: {
    status: "Disponible",
    title: "Formularios / Webhooks",
    description: "Endpoint público para recibir leads de formularios y webhooks de este cliente. Copia la URL, rota el token y pégala en Typeform, Tally, Webflow o tu backend.",
    configure: "Abrir configuración",
    endpoint: "Endpoint público",
    token: "Token",
    copyUrl: "Copiar endpoint",
    copied: "Copiado",
    rotate: "Rotar token",
    tokenRotated: "Token rotado. Actualiza el formulario o webhook que publica aquí.",
    statusLabel: "Estado",
    lastReceived: "Última recepción",
    leadsCreated: "Leads creados",
    never: "Nunca",
    idle: "Esperando envíos",
    payloadTitle: "Ejemplo de payload",
    payloadHint: "POST JSON. Deja source en form o webhook. No compartas esta URL fuera de este cliente.",
    guideTitle: "Cómo conectar un formulario o webhook",
    guideIntro: "Este canal no usa OAuth. Copias el endpoint del cliente y haces POST JSON desde tu formulario o backend.",
    step1: "Copia el endpoint público. Ya incluye el token de este cliente.",
    step2: "En Typeform, Tally, Webflow, Zapier o tu backend, agrega un webhook / petición HTTP a esa URL.",
    step3: "Envía JSON con source, name, email, phone y channel_identifier opcional.",
    step4: "Haz una prueba. Última recepción y leads creados deben actualizarse. Abre Leads para ver la oportunidad.",
    step5: "Si el token se filtró, rótalo y actualiza el formulario. La URL anterior deja de funcionar.",
  },
  note: {
    strong: "Cada conexión pertenece a un solo cliente.",
    rest: "Su número, agente, sesión y conversaciones permanecen separados de los demás espacios.",
  },
};

export const channels = { en, es };

// UI strings for carousels (Pomelli-like). Fill `en` and mirror it in `es`.
const en = {
  page: {
    eyebrow: "CONTENT",
    title: "Carousels",
    description: "Generate on-brand Instagram carousels, approve slide by slide, then send to the client.",
  },
  nav: "Carousels",
  list: {
    empty: "No carousels yet",
    emptyHint: "Create a draft from a client brief and brand DNA.",
    new: "New carousel",
    status: "Status",
  },
  status: {
    draft: "Draft",
    in_review: "In review",
    approved: "Approved",
    rejected: "Rejected",
    scheduled: "Scheduled",
    published: "Published",
    failed: "Failed",
  },
  slideStatus: {
    pending: "Pending",
    agency_ok: "Agency OK",
    client_ok: "Client OK",
    rejected: "Rejected",
  },
  form: {
    client: "Client",
    title: "Title",
    brief: "Brief",
    language: "Language",
    slides: "Slides",
    withImages: "Generate images",
    create: "Generate draft",
  },
  detail: {
    caption: "Caption",
    regenerate: "Regenerate",
    submitReview: "Send to client review",
    schedule: "Schedule Instagram",
    scheduleHint: "Requires client approval. Publishing runs when Instagram is connected.",
    agencyApprove: "Approve slide",
    agencyReject: "Reject slide",
    edit: "Edit",
    saveSlide: "Save slide",
  },
  portal: {
    title: "Carousel approvals",
    empty: "No carousels waiting for review",
    approveSlide: "Approve",
    rejectSlide: "Reject",
    approveSet: "Approve set",
    rejectSet: "Reject set",
    comment: "Comment",
  },
};

type Dict = typeof en;

const es: Dict = {
  page: {
    eyebrow: "CONTENIDO",
    title: "Carruseles",
    description: "Genera carruseles de Instagram con DNA de marca, aprueba slide a slide y envía al cliente.",
  },
  nav: "Carruseles",
  list: {
    empty: "Aún no hay carruseles",
    emptyHint: "Crea un borrador desde el brief del cliente y su DNA de marca.",
    new: "Nuevo carrusel",
    status: "Estado",
  },
  status: {
    draft: "Borrador",
    in_review: "En revisión",
    approved: "Aprobado",
    rejected: "Rechazado",
    scheduled: "Programado",
    published: "Publicado",
    failed: "Fallido",
  },
  slideStatus: {
    pending: "Pendiente",
    agency_ok: "OK agencia",
    client_ok: "OK cliente",
    rejected: "Rechazado",
  },
  form: {
    client: "Cliente",
    title: "Título",
    brief: "Brief",
    language: "Idioma",
    slides: "Slides",
    withImages: "Generar imágenes",
    create: "Generar borrador",
  },
  detail: {
    caption: "Caption",
    regenerate: "Regenerar",
    submitReview: "Enviar a revisión del cliente",
    schedule: "Programar Instagram",
    scheduleHint: "Requiere aprobación del cliente. La publicación corre cuando Instagram esté conectado.",
    agencyApprove: "Aprobar slide",
    agencyReject: "Rechazar slide",
    edit: "Editar",
    saveSlide: "Guardar slide",
  },
  portal: {
    title: "Aprobación de carruseles",
    empty: "No hay carruseles pendientes de revisión",
    approveSlide: "Aprobar",
    rejectSlide: "Rechazar",
    approveSet: "Aprobar set",
    rejectSet: "Rechazar set",
    comment: "Comentario",
  },
};

export const carousels = { en, es };

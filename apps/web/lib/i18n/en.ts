// English dictionary (source of truth), composed from per-area modules under
// ./dicts. `es.ts` mirrors this exact shape. Access with dotted paths, e.g.
// t("nav.clients"), t("clients.list.title").
import { core } from "./dicts/core";
import { home } from "./dicts/home";
import { clients } from "./dicts/clients";
import { agents } from "./dicts/agents";
import { channels } from "./dicts/channels";
import { settings } from "./dicts/settings";
import { meta } from "./dicts/meta";
import { playground } from "./dicts/playground";
import { portal } from "./dicts/portal";
import { inbox } from "./dicts/inbox";
import { tools } from "./dicts/tools";
import { carousels } from "./dicts/carousels";
import { automations } from "./dicts/automations";
import { instagram } from "./dicts/instagram";
import { linkedin } from "./dicts/linkedin";
import { leads } from "./dicts/leads";
import { manual } from "./dicts/manual";

export const en = {
  ...core.en,
  home: home.en,
  clients: clients.en,
  agents: agents.en,
  channels: channels.en,
  settings: settings.en,
  meta: meta.en,
  playground: playground.en,
  portal: portal.en,
  inbox: inbox.en,
  tools: tools.en,
  carousels: carousels.en,
  automations: automations.en,
  instagram: instagram.en,
  linkedin: linkedin.en,
  leads: leads.en,
  manual: manual.en,
};

export type Dictionary = typeof en;

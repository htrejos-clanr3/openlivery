import type { Dictionary } from "./en";
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

// Spanish dictionary. Composed from the same modules; typed as Dictionary so it
// must mirror the exact shape of `en` (each area's `es` mirrors its own `en`).
export const es: Dictionary = {
  ...core.es,
  home: home.es,
  clients: clients.es,
  agents: agents.es,
  channels: channels.es,
  settings: settings.es,
  meta: meta.es,
  playground: playground.es,
  portal: portal.es,
  inbox: inbox.es,
  tools: tools.es,
  carousels: carousels.es,
  automations: automations.es,
  instagram: instagram.es,
  linkedin: linkedin.es,
  leads: leads.es,
  manual: manual.es,
};

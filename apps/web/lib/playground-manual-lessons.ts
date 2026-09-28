export const MANUAL_LESSON_IDS = [
  "map",
  "home",
  "clients",
  "agents",
  "keys",
  "chat",
  "inbox",
  "carousels",
  "campaign",
  "linkedin",
  "live",
] as const;

export type ManualLessonId = (typeof MANUAL_LESSON_IDS)[number];

export type ManualPin = {
  id: string;
  x: number;
  y: number;
};

export type ManualLessonMeta = {
  id: ManualLessonId;
  minutes: number;
  href: string;
  hrefLabelKey: "openHome" | "openClients" | "openAgents" | "openSettings" | "openInbox" | "openCarousels" | "openInstagram" | "openLinkedIn" | "openChannels" | "practiceHere";
  capture: ManualLessonId;
  pins: ManualPin[];
  correctPin?: string;
  showLiveChat?: boolean;
};

export const MANUAL_LESSONS: ManualLessonMeta[] = [
  {
    id: "map",
    minutes: 3,
    href: "/",
    hrefLabelKey: "openHome",
    capture: "map",
    pins: [
      { id: "a", x: 18, y: 42 },
      { id: "b", x: 50, y: 42 },
      { id: "c", x: 82, y: 42 },
    ],
    correctPin: "a",
  },
  {
    id: "home",
    minutes: 3,
    href: "/",
    hrefLabelKey: "openHome",
    capture: "home",
    pins: [
      { id: "a", x: 10, y: 32 },
      { id: "b", x: 58, y: 36 },
      { id: "c", x: 10, y: 88 },
    ],
    correctPin: "c",
  },
  {
    id: "clients",
    minutes: 4,
    href: "/clients/new",
    hrefLabelKey: "openClients",
    capture: "clients",
    pins: [
      { id: "a", x: 28, y: 28 },
      { id: "b", x: 42, y: 62 },
      { id: "c", x: 88, y: 18 },
    ],
    correctPin: "b",
  },
  {
    id: "agents",
    minutes: 5,
    href: "/agents",
    hrefLabelKey: "openAgents",
    capture: "agents",
    pins: [
      { id: "a", x: 12, y: 28 },
      { id: "b", x: 58, y: 52 },
      { id: "c", x: 88, y: 16 },
    ],
    correctPin: "b",
  },
  {
    id: "keys",
    minutes: 3,
    href: "/settings",
    hrefLabelKey: "openSettings",
    capture: "keys",
    pins: [
      { id: "a", x: 28, y: 28 },
      { id: "b", x: 38, y: 52 },
      { id: "c", x: 88, y: 16 },
    ],
    correctPin: "b",
  },
  {
    id: "chat",
    minutes: 5,
    href: "/playground",
    hrefLabelKey: "practiceHere",
    capture: "chat",
    pins: [
      { id: "a", x: 12, y: 28 },
      { id: "b", x: 62, y: 86 },
      { id: "c", x: 88, y: 16 },
    ],
    correctPin: "a",
    showLiveChat: true,
  },
  {
    id: "inbox",
    minutes: 3,
    href: "/inbox",
    hrefLabelKey: "openInbox",
    capture: "inbox",
    pins: [
      { id: "a", x: 12, y: 18 },
      { id: "b", x: 12, y: 42 },
      { id: "c", x: 82, y: 16 },
    ],
    correctPin: "c",
  },
  {
    id: "carousels",
    minutes: 6,
    href: "/carousels",
    hrefLabelKey: "openCarousels",
    capture: "carousels",
    pins: [
      { id: "a", x: 32, y: 26 },
      { id: "b", x: 48, y: 58 },
      { id: "c", x: 88, y: 22 },
    ],
    correctPin: "b",
  },
  {
    id: "campaign",
    minutes: 4,
    href: "/channels",
    hrefLabelKey: "openInstagram",
    capture: "campaign",
    pins: [
      { id: "a", x: 22, y: 28 },
      { id: "b", x: 42, y: 52 },
      { id: "c", x: 42, y: 72 },
    ],
    correctPin: "c",
  },
  {
    id: "linkedin",
    minutes: 5,
    href: "/channels",
    hrefLabelKey: "openLinkedIn",
    capture: "linkedin",
    pins: [
      { id: "a", x: 22, y: 30 },
      { id: "b", x: 48, y: 58 },
      { id: "c", x: 78, y: 78 },
    ],
    correctPin: "c",
  },
  {
    id: "live",
    minutes: 4,
    href: "/channels",
    hrefLabelKey: "openChannels",
    capture: "live",
    pins: [
      { id: "a", x: 18, y: 48 },
      { id: "b", x: 50, y: 48 },
      { id: "c", x: 82, y: 48 },
    ],
    correctPin: "c",
  },
];

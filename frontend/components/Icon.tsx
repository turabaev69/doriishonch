import type { ReactNode } from "react";

export type IconName = "shield" | "scan" | "map" | "search" | "chat" | "arrow" | "camera" | "keyboard" | "pin" | "check" | "close" | "chevron" | "star" | "box" | "info" | "plus" | "locate" | "menu" | "user" | "clock" | "send";
const paths: Record<IconName, ReactNode> = {
  shield: <><path d="m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6l8-3Z" /><path d="m8 12 3 3 5-6" /></>,
  scan: <><path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m8 0h3a2 2 0 0 0 2-2v-3M3 12h18" /><path d="M8 8v1m4-1v1m4-1v1M8 15v1m4-1v1m4-1v1" /></>,
  map: <path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2V5Zm6-2v16m6-14v16" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
  chat: <><path d="M21 11a8 8 0 0 1-8 8H7l-4 3V11a9 9 0 0 1 18 0Z" /><path d="M7 10h10M7 14h6" /></>,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  camera: <><path d="m8 5 2-2h4l2 2h4a2 2 0 0 1 2 2v12H2V7a2 2 0 0 1 2-2h4Z" /><circle cx="12" cy="12" r="4" /></>,
  keyboard: <><rect x="2" y="5" width="20" height="14" rx="3" /><path d="M6 9h.01M10 9h.01M14 9h.01M18 9h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 15h10" /></>,
  pin: <><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  star: <path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z" />,
  box: <path d="m12 3 9 5v9l-9 5-9-5V8l9-5Zm-9 5 9 5 9-5M12 13v9M7 5.8l9 5" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10h.01" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  locate: <><circle cx="12" cy="12" r="7" /><circle cx="12" cy="12" r="2" /><path d="M12 2v3m0 14v3M2 12h3m14 0h3" /></>,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  user: <><circle cx="12" cy="7" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  send: <path d="m21 3-7 18-4-7-7-4 18-7Zm-11 11L21 3" />,
};
export function Icon({ name, size = 22, className = "" }: { name: IconName; size?: number; className?: string }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className}>{paths[name]}</svg>;
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Icon, IconName } from "./Icon";

const navigation: { href: string; label: string; icon: IconName }[] = [
  { href: "/", label: "Tekshirish", icon: "scan" },
  { href: "/xarita", label: "Dorixonalar", icon: "map" },
  { href: "/ballar", label: "Ballarim", icon: "star" },
  { href: "/yordamchi", label: "Yordamchi", icon: "chat" },
];

export function AppHeader() {
  const pathname = usePathname();
  const [largeText, setLargeText] = useState(false);
  const menuRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    try {
      const enabled = localStorage.getItem("doriishonch_large_text") === "true";
      setLargeText(enabled);
      document.documentElement.dataset.largeText = String(enabled);
    } catch {}
  }, []);
  useEffect(() => { if (menuRef.current) menuRef.current.open = false; }, [pathname]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape" && menuRef.current?.open) {
        menuRef.current.open = false;
        menuRef.current.querySelector("summary")?.focus();
      }
    };
    const outside = (event: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) menuRef.current.open = false;
    };
    document.addEventListener("keydown", close);
    document.addEventListener("pointerdown", outside);
    return () => { document.removeEventListener("keydown", close); document.removeEventListener("pointerdown", outside); };
  }, []);
  function toggleText() {
    const enabled = !largeText;
    setLargeText(enabled);
    document.documentElement.dataset.largeText = String(enabled);
    try { localStorage.setItem("doriishonch_large_text", String(enabled)); } catch {}
  }
  function active(href: string) {
    return href === "/" ? pathname === "/" : pathname.startsWith(href) || (href === "/dori" && pathname.startsWith("/drug/"));
  }
  return <>
    <a href="#main-content" className="skip-link">Asosiy qismga oʻtish</a>
    <header className="app-header"><div className="header-inner">
      <Link href="/" className="brand" aria-label="DoriIshonch — bosh sahifa"><span className="brand-symbol"><Icon name="shield" size={27} /></span><span>Dori<span className="brand-accent">Ishonch</span><small>Har bir qutida ishonch.</small></span></Link>
      <nav className="desktop-nav" aria-label="Asosiy sahifalar">{navigation.map(({ href, label, icon }) => <Link href={href} key={href} aria-current={active(href) ? "page" : undefined} className={active(href) ? "nav-link active" : "nav-link"}><Icon name={icon} size={19} />{label}</Link>)}</nav>
      <div className="header-actions">
        <button type="button" className="text-size-button" onClick={toggleText} aria-pressed={largeText} aria-label={largeText ? "Oddiy matn hajmi" : "Matnni kattalashtirish"} title="Matn hajmini oʻzgartirish"><span aria-hidden="true">A<span>A</span></span><span className="text-size-label">{largeText ? "Oddiy matn" : "Katta matn"}</span></button>
        <details ref={menuRef} className="more-menu"><summary className="icon-button" aria-label="Qoʻshimcha sahifalar"><Icon name="menu" /></summary><div className="menu-popover"><p>Xaridor uchun</p>{[["/dori", "Dori qidirish"], ["/demo-kodlar", "Namuna bilan sinash"]].map(([href, label]) => <Link key={href} href={href} aria-current={active(href) ? "page" : undefined} onClick={() => { if (menuRef.current) menuRef.current.open = false; }}>{label}<Icon name="chevron" size={16} /></Link>)}</div></details>
      </div>
    </div></header>
    <nav className="mobile-nav" aria-label="Asosiy sahifalar — mobil">{navigation.map(({ href, label, icon }) => <Link href={href} key={href} className={active(href) ? "active" : ""} aria-current={active(href) ? "page" : undefined}><Icon name={icon} size={23} /><span>{label}</span></Link>)}</nav>
  </>;
}

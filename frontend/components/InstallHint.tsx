"use client";

import { useEffect, useState } from "react";

// iPhone Safari da: "Bosh ekranga qoʻshish" boʻyicha bir martalik maslahat — sayt ilova kabi ochiladi.
export function InstallHint() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
      const standalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone;
      if (ios && !standalone && !localStorage.getItem("doriishonch_install_hint")) setShow(true);
    } catch {}
  }, []);
  if (!show) return null;
  const close = () => {
    setShow(false);
    try { localStorage.setItem("doriishonch_install_hint", "1"); } catch {}
  };
  return (
    <div className="fixed inset-x-3 bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-[1200] rounded-3xl bg-ink p-4 text-white shadow-2xl sm:hidden">
      <div className="flex items-start gap-3">
        <img src="/apple-touch-icon.png" alt="" className="h-12 w-12 rounded-2xl" />
        <div className="flex-1 text-sm">
          <div className="font-bold">Ilova sifatida oʻrnating</div>
          <div className="text-white/80">
            Pastdagi <span className="inline-block rounded bg-white/15 px-1">⬆︎ Ulashish</span> tugmasini bosing →
            <b> “Bosh ekranga qoʻshish”</b>. Keyin DoriIshonch telefoningizda ilova boʻlib ochiladi.
          </div>
        </div>
        <button onClick={close} className="rounded-full bg-white/15 px-2.5 py-1 text-sm" aria-label="Yopish">✕</button>
      </div>
    </div>
  );
}

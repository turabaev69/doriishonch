"use client";

import { useEffect, useRef, useState } from "react";

/** bwip-js bilan GS1 DataMatrix yoki QR kodni chizadi (demo sahifasi uchun). */
export function Barcode({ text, type, scale = 4 }: { text: string; type: "gs1datamatrix" | "qrcode"; scale?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    import("bwip-js/browser").then((mod) => {
      if (!alive || !ref.current) return;
      const bwip = (mod as unknown as { default?: typeof mod }).default ?? mod;
      try {
        // dontlint: demo GTIN larda GS1 nazorat raqami tekshirilmaydi
        (bwip as unknown as { toCanvas: (c: HTMLCanvasElement, o: object) => void }).toCanvas(ref.current, {
          bcid: type,
          text,
          scale,
          padding: 2,
          backgroundcolor: "FFFFFF",
          dontlint: true,
          parsefnc: false,
        });
      } catch (e) {
        setErr(String(e));
      }
    });
    return () => {
      alive = false;
    };
  }, [text, type, scale]);

  return err ? <p className="text-xs text-red-600">{err}</p> : <canvas ref={ref} className="h-auto max-w-full" />;
}

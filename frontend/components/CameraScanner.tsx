"use client";

import { useEffect, useRef, useState } from "react";
import { looksLikeMedicineCode } from "@/lib/geo";
import { Icon } from "./Icon";

type Controls = { stop: () => void };

/**
 * Kamera orqali DataMatrix / QR / shtrix-kodni oʻqiydi (@zxing/browser).
 * Telefon brauzerida kamera faqat HTTPS yoki localhost da ishlaydi.
 */
export function CameraScanner({ onCode, onClose }: { onCode: (text: string) => void; onClose: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const controlsRef = useRef<Controls | null>(null);
  const doneRef = useRef(false);
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");

  useEffect(() => {
    let cancelled = false;
    doneRef.current = false;
    (async () => {
      try {
        const [{ BrowserMultiFormatReader }, lib] = await Promise.all([
          import("@zxing/browser"),
          import("@zxing/library"),
        ]);
        const hints = new Map();
        hints.set(lib.DecodeHintType.POSSIBLE_FORMATS, [
          lib.BarcodeFormat.DATA_MATRIX,
          lib.BarcodeFormat.QR_CODE,
          lib.BarcodeFormat.EAN_13,
          lib.BarcodeFormat.EAN_8,
          lib.BarcodeFormat.UPC_A,
          lib.BarcodeFormat.CODE_128,
        ]);
        hints.set(lib.DecodeHintType.TRY_HARDER, true);
        const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 150 });
        if (cancelled || !videoRef.current) return;
        const controls = await reader.decodeFromConstraints(
          { video: { facingMode: { ideal: "environment" } } },
          videoRef.current,
          (result) => {
            if (result && !doneRef.current) {
              const text = result.getText();
              // Qutidagi reklama QR (Telegram, sayt) — dori kodi emas: oʻtkazib, skanerlashda davom etamiz
              if (!looksLikeMedicineCode(text)) {
                setHint("Bu reklama QR kodi, dori kodi emas. Shtrix-kod yoki kichik kvadrat kodni tuting.");
                return;
              }
              doneRef.current = true;
              controlsRef.current?.stop();
              if (navigator.vibrate) navigator.vibrate(60);
              onCode(text);
            }
          },
        );
        controlsRef.current = controls;
        if (cancelled) controls.stop();
      } catch (e) {
        if (cancelled) return;
        const msg = (e as Error).message || String(e);
        setError(
          /Permission|NotAllowed/i.test(msg)
            ? "Kameraga ruxsat berilmadi. Brauzer sozlamalarida kameraga ruxsat bering."
            : /secure|https|getUserMedia|undefined/i.test(msg)
              ? "Kamera faqat HTTPS orqali ochilgan sahifada ishlaydi. Surat yuklash yoki qoʻlda kiritishdan foydalaning."
              : `Kamerani ishga tushirib boʻlmadi: ${msg}`,
        );
      }
    })();
    return () => {
      cancelled = true;
      controlsRef.current?.stop();
    };
  }, [onCode]);

  return (
    <div className="scanner-shell">
      <div className="scanner-toolbar"><span>Kodni ramkaga tuting</span><button type="button" onClick={onClose}><Icon name="close" size={18} />Yopish</button></div>
      <div className="scanner-video">
        <video ref={videoRef} muted playsInline aria-label="Dori qutisini tekshirish kamerasi" />
        <div className="scanner-reticle pointer-events-none" />
        <p className="scanner-caption">Kichik kvadrat kod aniq koʻrinsin. Kamera oʻzi oʻqiydi.</p>
        {hint && (
          <p role="status" className="absolute left-2 right-2 top-2 rounded-lg bg-amber-100 px-3 py-2 text-center text-sm font-bold text-amber-950">{hint}</p>
        )}
      </div>
      {error && <p className="scanner-error" role="alert">{error} Kamerani yopib, surat yoki kod orqali ham tekshirishingiz mumkin.</p>}
    </div>
  );
}

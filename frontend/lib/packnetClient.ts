"use client";

import { PackNet, PackResult, PackSpec } from "./packnet";

let net: Promise<PackNet> | null = null;

/** Modelni bir marta yuklaydi (~100 KB), keyin brauzer keshidan. */
export function loadPackNet(): Promise<PackNet> {
  if (!net) {
    net = fetch("/models/packnet-v1.json")
      .then((r) => {
        if (!r.ok) throw new Error("Model fayli topilmadi");
        return r.json() as Promise<PackSpec>;
      })
      .then((spec) => new PackNet(spec))
      .catch((e) => {
        net = null;
        throw e;
      });
  }
  return net;
}

/** Surat → markaziy kvadrat → 128×128 → model. Hammasi brauzerda, surat serverga yuborilmaydi. */
export async function checkPackaging(source: Blob | HTMLImageElement, expectedGtin?: string | null): Promise<PackResult> {
  const model = await loadPackNet();
  const bmp = source instanceof Blob ? await createImageBitmap(source) : source;
  const w = "naturalWidth" in bmp ? bmp.naturalWidth : bmp.width;
  const h = "naturalHeight" in bmp ? bmp.naturalHeight : bmp.height;
  const s = Math.min(w, h);
  const S = model.size;
  const canvas = document.createElement("canvas");
  canvas.width = S;
  canvas.height = S;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(bmp, (w - s) / 2, (h - s) / 2, s, s, 0, 0, S, S);
  const px = ctx.getImageData(0, 0, S, S).data;
  // UI bloklanmasin: hisobni keyingi kadrga qoldiramiz
  await new Promise((r) => setTimeout(r, 0));
  return model.run(px, 4, expectedGtin);
}

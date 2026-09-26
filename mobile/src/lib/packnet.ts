/**
 * PackNet — qadoq surati modeli, qurilmada (brauzer / iPhone) ishlaydi, internet kerak emas.
 *
 * Ogʻirliklar: packnet-v1.json (ml/packnet/train.py). Hisob backend/app/ml/packnet.py bilan aynan bir xil:
 * markaziy kvadrat → 128×128 RGB → (x/255 − mean)/std → konvolyutsiyalar → mahsulot + "farq bor" ehtimoli.
 * Bu fayl frontend/lib va mobile/src/lib da bir xil — birini oʻzgartirsangiz, ikkinchisini ham yangilang.
 */

type Q = { w: string; scale: string; bias: string };
type LayerSpec = Q & { type: "conv" | "dw"; k: number; stride: number; pad: number; cin: number; cout: number; relu: boolean };
type HeadSpec = Q & { cin: number; cout: number };
export type PackCard = {
  version: string;
  input: { size: number; mean: number; std: number };
  classes: { gtin: string; name: string }[];
  other_index: number;
  thresholds: { known_min: number; fake: number };
  metrics_val_synthetic?: Record<string, unknown>;
  notes?: string;
};
export type PackSpec = { card: PackCard; layers: LayerSpec[]; heads: { product: HeadSpec; fake: HeadSpec } };

export type PackResult = {
  verdict: "asl" | "farq" | "boshqa" | "tanilmadi";
  title: string;
  text: string;
  product: { gtin: string; name: string; prob: number };
  fake_prob: number;
  model: string;
  on_device: boolean;
  ms?: number;
};

const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
const LOOKUP = (() => {
  const t = new Uint8Array(256);
  for (let i = 0; i < B64.length; i++) t[B64.charCodeAt(i)] = i;
  return t;
})();

export function b64bytes(s: string): Uint8Array {
  const len = s.length;
  const pad = s.endsWith("==") ? 2 : s.endsWith("=") ? 1 : 0;
  const out = new Uint8Array((len * 3) / 4 - pad);
  let o = 0;
  for (let i = 0; i < len; i += 4) {
    const n = (LOOKUP[s.charCodeAt(i)] << 18) | (LOOKUP[s.charCodeAt(i + 1)] << 12) |
      (LOOKUP[s.charCodeAt(i + 2)] << 6) | LOOKUP[s.charCodeAt(i + 3)];
    if (o < out.length) out[o++] = (n >> 16) & 255;
    if (o < out.length) out[o++] = (n >> 8) & 255;
    if (o < out.length) out[o++] = n & 255;
  }
  return out;
}

function f32(s: string): Float32Array {
  const b = b64bytes(s);
  return new Float32Array(b.buffer, b.byteOffset, b.byteLength / 4).slice();
}

/** int8 × kanal shkalasi → float32 (cout qator) */
function dequant(q: Q): { W: Float32Array; B: Float32Array } {
  const raw = b64bytes(q.w);
  const scale = f32(q.scale);
  const B = f32(q.bias);
  const per = raw.length / scale.length;
  const W = new Float32Array(raw.length);
  for (let o = 0; o < scale.length; o++) {
    const s = scale[o];
    for (let i = 0; i < per; i++) {
      const v = raw[o * per + i];
      W[o * per + i] = (v > 127 ? v - 256 : v) * s;
    }
  }
  return { W, B };
}

type Layer = LayerSpec & { W: Float32Array; B: Float32Array };

export class PackNet {
  card: PackCard;
  private layers: Layer[];
  private product: { W: Float32Array; B: Float32Array; cin: number; cout: number };
  private fake: { W: Float32Array; B: Float32Array; cin: number };

  constructor(spec: PackSpec) {
    this.card = spec.card;
    this.layers = spec.layers.map((L) => ({ ...L, ...dequant(L) }));
    const p = spec.heads.product, f = spec.heads.fake;
    this.product = { ...dequant(p), cin: p.cin, cout: p.cout };
    this.fake = { ...dequant(f), cin: f.cin };
  }

  get size() {
    return this.card.input.size;
  }

  /** rgba: size×size piksellar (RGBA yoki RGB), allaqachon markaziy kvadrat va kichraytirilgan. */
  run(pixels: Uint8Array | Uint8ClampedArray, channels: 3 | 4, expectedGtin?: string | null): PackResult {
    const t0 = Date.now();
    const S = this.size;
    const { mean, std } = this.card.input;
    let h: Float32Array = new Float32Array(S * S * 3);
    for (let i = 0, j = 0; i < S * S; i++, j += channels) {
      h[i * 3] = (pixels[j] / 255 - mean) / std;
      h[i * 3 + 1] = (pixels[j + 1] / 255 - mean) / std;
      h[i * 3 + 2] = (pixels[j + 2] / 255 - mean) / std;
    }
    let H = S, Wd = S, C = 3;
    for (const L of this.layers) {
      let out: Float32Array, oh: number, ow: number;
      if (L.type === "dw") {
        [out, oh, ow] = depthwise(h, H, Wd, C, L);
      } else if (L.k === 1) {
        [out, oh, ow] = [pointwise(h, H * Wd, C, L), H, Wd];
      } else {
        [out, oh, ow] = conv(h, H, Wd, C, L);
      }
      if (L.relu) for (let i = 0; i < out.length; i++) if (out[i] < 0) out[i] = 0;
      h = out; H = oh; Wd = ow; C = L.cout;
    }
    // global oʻrtacha
    const g = new Float32Array(C);
    const n = H * Wd;
    for (let p = 0; p < n; p++) for (let c = 0; c < C; c++) g[c] += h[p * C + c];
    for (let c = 0; c < C; c++) g[c] /= n;
    const logits = new Float32Array(this.product.cout);
    for (let o = 0; o < this.product.cout; o++) {
      let s = this.product.B[o];
      for (let c = 0; c < C; c++) s += g[c] * this.product.W[o * C + c];
      logits[o] = s;
    }
    let fz = this.fake.B[0];
    for (let c = 0; c < C; c++) fz += g[c] * this.fake.W[c];
    const probs = softmax(logits);
    const res = interpret(this.card, probs, 1 / (1 + Math.exp(-fz)), expectedGtin);
    return { ...res, on_device: true, ms: Date.now() - t0 };
  }
}

function conv(x: Float32Array, H: number, W: number, C: number, L: Layer): [Float32Array, number, number] {
  const { k, stride: s, pad: p, cout } = L;
  const oh = Math.floor((H + 2 * p - k) / s) + 1, ow = Math.floor((W + 2 * p - k) / s) + 1;
  const out = new Float32Array(oh * ow * cout);
  const Wt = L.W; // (cout, cin, k, k)
  for (let y = 0; y < oh; y++) for (let xx = 0; xx < ow; xx++) {
    const ob = (y * ow + xx) * cout;
    for (let o = 0; o < cout; o++) out[ob + o] = L.B[o];
    for (let i = 0; i < k; i++) {
      const iy = y * s + i - p;
      if (iy < 0 || iy >= H) continue;
      for (let j = 0; j < k; j++) {
        const ix = xx * s + j - p;
        if (ix < 0 || ix >= W) continue;
        const ib = (iy * W + ix) * C;
        for (let c = 0; c < C; c++) {
          const v = x[ib + c];
          if (v === 0) continue;
          for (let o = 0; o < cout; o++) out[ob + o] += v * Wt[((o * C + c) * k + i) * k + j];
        }
      }
    }
  }
  return [out, oh, ow];
}

function depthwise(x: Float32Array, H: number, W: number, C: number, L: Layer): [Float32Array, number, number] {
  const { k, stride: s, pad: p } = L;
  const oh = Math.floor((H + 2 * p - k) / s) + 1, ow = Math.floor((W + 2 * p - k) / s) + 1;
  const out = new Float32Array(oh * ow * C);
  const Wt = L.W; // (c, k, k)
  for (let y = 0; y < oh; y++) for (let xx = 0; xx < ow; xx++) {
    const ob = (y * ow + xx) * C;
    for (let c = 0; c < C; c++) out[ob + c] = L.B[c];
    for (let i = 0; i < k; i++) {
      const iy = y * s + i - p;
      if (iy < 0 || iy >= H) continue;
      for (let j = 0; j < k; j++) {
        const ix = xx * s + j - p;
        if (ix < 0 || ix >= W) continue;
        const ib = (iy * W + ix) * C, wo = i * k + j, kk = k * k;
        for (let c = 0; c < C; c++) out[ob + c] += x[ib + c] * Wt[c * kk + wo];
      }
    }
  }
  return [out, oh, ow];
}

function pointwise(x: Float32Array, n: number, C: number, L: Layer): Float32Array {
  const cout = L.cout, Wt = L.W, B = L.B;
  const out = new Float32Array(n * cout);
  for (let p = 0; p < n; p++) {
    const ib = p * C, ob = p * cout;
    for (let o = 0; o < cout; o++) {
      let s = B[o];
      const wb = o * C;
      for (let c = 0; c < C; c++) s += x[ib + c] * Wt[wb + c];
      out[ob + o] = s;
    }
  }
  return out;
}

function softmax(z: Float32Array): Float32Array {
  let m = -Infinity;
  for (const v of z) m = Math.max(m, v);
  const e = new Float32Array(z.length);
  let s = 0;
  for (let i = 0; i < z.length; i++) { e[i] = Math.exp(z[i] - m); s += e[i]; }
  for (let i = 0; i < z.length; i++) e[i] /= s;
  return e;
}

const r3 = (v: number) => Math.round(v * 1000) / 1000;

/** backend/app/ml/packnet.py → interpret() bilan bir xil */
export function interpret(card: PackCard, probs: Float32Array, fakeP: number, expectedGtin?: string | null):
  Omit<PackResult, "on_device" | "ms"> & { on_device: boolean } {
  const { classes, other_index: other, thresholds: thr } = card;
  let top = 0;
  for (let i = 1; i < probs.length; i++) if (probs[i] > probs[top]) top = i;
  const conf = probs[top];
  const exp = (expectedGtin || "").replace(/^0+/, "");
  const expIdx = exp ? classes.findIndex((c) => c.gtin && c.gtin.replace(/^0+/, "") === exp) : -1;
  const base = {
    product: { gtin: classes[top].gtin, name: classes[top].name, prob: r3(conf) },
    fake_prob: r3(fakeP), model: card.version, on_device: false,
  };
  if (top === other || conf < thr.known_min)
    return { ...base, verdict: "tanilmadi", title: "Model bu qadoqni tanimadi",
      text: "Model hozircha faqat demo dori qutilarini taniydi. Qutini toʻliq, yorugʻda suratga oling yoki boshqa tekshiruvlarga tayaning." };
  if (expIdx >= 0 && top !== expIdx)
    return { ...base, verdict: "boshqa", title: "Qadoq boshqa dori qutisiga oʻxshaydi",
      text: `Kod ${classes[expIdx].name} ga tegishli, surat esa ${classes[top].name} qutisiga oʻxshaydi.` };
  if (fakeP >= thr.fake)
    return { ...base, verdict: "farq", title: "Qadoq asl dizayndan farq qiladi",
      text: "Rang, shrift, yozuv yoki bosma sifati asl qutidan farq qilishi mumkin. Diqqat bilan solishtiring." };
  return { ...base, verdict: "asl", title: "Qadoq asl dizaynga mos",
    text: `Surat ${classes[top].name} ning asl qadogʻiga oʻxshaydi.` };
}

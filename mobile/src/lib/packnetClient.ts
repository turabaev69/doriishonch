import * as ImageManipulator from "expo-image-manipulator";
import decodeJpeg from "jpeg-js/lib/decoder";
import { b64bytes, PackNet, PackResult, PackSpec } from "./packnet";

let net: PackNet | null = null;

/** Model ilova ichida (assets/models/packnet-v1.json) — internet kerak emas. */
export function getPackNet(): PackNet {
  if (!net) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const spec = require("../../assets/models/packnet-v1.json") as PackSpec;
    net = new PackNet(spec);
  }
  return net;
}

/**
 * Surat → markaziy kvadrat → 128×128 → PackNet. Hammasi telefonda, surat hech qayerga yuborilmaydi.
 * width/height — suratning oʻlchami (ImagePicker natijasidan).
 */
export async function checkPackaging(uri: string, width: number, height: number, expectedGtin?: string | null): Promise<PackResult> {
  const model = getPackNet();
  const S = model.size;
  const s = Math.min(width, height);
  const ctx = ImageManipulator.ImageManipulator.manipulate(uri)
    .crop({ originX: Math.floor((width - s) / 2), originY: Math.floor((height - s) / 2), width: s, height: s })
    .resize({ width: S, height: S });
  const img = await ctx.renderAsync();
  const saved = await img.saveAsync({ format: ImageManipulator.SaveFormat.JPEG, compress: 1, base64: true });
  if (!saved.base64) throw new Error("Surat oʻqilmadi");
  const raw = decodeJpeg(b64bytes(saved.base64.replace(/\s/g, "")), { useTArray: true, formatAsRGBA: true });
  if (raw.width !== S || raw.height !== S) throw new Error("Surat oʻlchami notoʻgʻri");
  await new Promise((r) => setTimeout(r, 0));
  return model.run(raw.data, 4, expectedGtin);
}

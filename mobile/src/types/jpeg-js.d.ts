declare module "jpeg-js/lib/decoder" {
  export default function decode(
    data: Uint8Array,
    opts?: { useTArray?: boolean; formatAsRGBA?: boolean },
  ): { width: number; height: number; data: Uint8Array };
}

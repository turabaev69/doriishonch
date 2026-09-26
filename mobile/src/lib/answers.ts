// Natijani oddiy tilda: 4-5 ta savol va aniq javob (Ha / Yoʻq / Shubhali).
export type Answer = { q: string; a: "ha" | "yoq" | "shubha" | "nomalum"; note: string };

type C = { key: string; status: string; title: string; text: string };

const has = (cs: C[], keys: string[]) => cs.find((c) => keys.includes(c.key));

export function simpleAnswers(checks: C[], mode: "before" | "after" = "before"): Answer[] {
  const out: Answer[] = [];
  const reg = has(checks, ["unregistered"]);
  const regOk = has(checks, ["registered"]);
  out.push({
    q: "Dori davlat roʻyxatida bormi?",
    a: reg ? "yoq" : regOk ? "ha" : "nomalum",
    note: reg ? "Roʻyxatda yoʻq — qonuniy sotilmasligi kerak" : regOk ? "Roʻyxatdan oʻtgan" : "Tekshirib boʻlmadi",
  });

  const fake = has(checks, ["serial_unknown", "key_mismatch", "bad_gtin"]);
  const doubt = has(checks, ["clone", "not_introduced"]);
  const real = has(checks, ["in_stock", "sale_registered", "crypto_present", "expiry", "gtin_ok"]);
  out.push({
    q: "Quti haqiqiymi?",
    a: fake ? "yoq" : doubt ? "shubha" : real ? "ha" : "nomalum",
    note: fake ? fake.title : doubt ? doubt.title : real ? "Kod rasmiy bazadagi qutiga mos" : "Tekshirib boʻlmadi",
  });

  const sold = has(checks, ["already_sold", "already_claimed", "double_claim"]);
  const soldDoubt = has(checks, ["just_sold", "sold_elsewhere", "other_owner", "not_delivered", "sale_not_registered"]);
  const notSold = has(checks, ["in_stock", "first_scan", "sale_registered", "prior_scans"]);
  out.push({
    q: mode === "after" ? "Sotuv toʻgʻri qayd etildimi?" : "Quti oldin sotilmaganmi?",
    a: sold ? "yoq" : soldDoubt ? "shubha" : fake ? "nomalum" : notSold ? "ha" : "nomalum",
    note: sold ? "Bu quti oldin sotilgan — qayta ishlatilgan boʻlishi mumkin"
      : soldDoubt ? soldDoubt.title : fake ? "Quti rasmiy bazada topilmadi" : notSold ? "Hammasi joyida" : "Tekshirib boʻlmadi",
  });

  const bad = has(checks, ["expired", "withdrawn", "batch_alert"]);
  const exp = has(checks, ["expiry"]);
  out.push({
    q: "Muddati va sifati joyidami?",
    a: bad ? "yoq" : exp ? "ha" : "nomalum",
    note: bad ? bad.title : exp ? exp.text : "Maʼlumot yoʻq",
  });

  const cust = has(checks, ["no_customs", "importer_license"]);
  const custOk = has(checks, ["customs", "produced"]);
  if (cust || custOk)
    out.push({
      q: custOk?.key === "produced" ? "Qayerda ishlab chiqarilgan?" : "Bojxonadan rasmiy oʻtganmi?",
      a: cust ? "shubha" : "ha",
      note: cust ? cust.title : custOk!.key === "produced" ? "Oʻzbekistonda ishlab chiqarilgan" : "Rasmiy import",
    });

  const price = has(checks, ["price_too_low"]);
  if (price) out.push({ q: "Narxi normalmi?", a: "shubha", note: price.title });
  return out;
}

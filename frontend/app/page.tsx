import { ScanHome } from "@/components/ScanHome";

type SearchParams = { rejim?: string | string[]; dorixona?: string | string[] };

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const modeParam = Array.isArray(params.rejim) ? params.rejim[0] : params.rejim;
  const pharmacyParam = Array.isArray(params.dorixona) ? params.dorixona[0] : params.dorixona;
  const initialMode = modeParam === "after" ? "after" : "before";
  const pharmacyNumber = Number(pharmacyParam);
  const initialPharmacyId = Number.isSafeInteger(pharmacyNumber) && pharmacyNumber > 0 ? pharmacyNumber : null;

  return <>
    <noscript><p className="info-notice">Qutini tekshirish va xaritadan foydalanish uchun brauzeringizda JavaScript yoqilgan boʻlishi kerak.</p></noscript>
    <ScanHome key={`${initialMode}:${initialPharmacyId ?? ""}`} initialMode={initialMode} initialPharmacyId={initialPharmacyId} />
  </>;
}

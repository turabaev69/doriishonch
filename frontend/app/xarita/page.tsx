import { PharmacyMap } from "@/components/PharmacyMap";

export const metadata = { title: "Dorixonalar xaritasi" };

export default function MapPage() {
  return (
    <div>
      <div className="page-heading"><div><h1>Namangan dorixonalari</h1></div></div>
      <PharmacyMap />
      <p className="mt-3 text-sm text-slate-500">Manba: OpenStreetMap. Ish vaqti va litsenziya tasdiqlanmagan.</p>
    </div>
  );
}

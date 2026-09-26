# Namangan pilot — 2026-09-26

- Default coverage: Namangan (`PHARMACY_REGION=Namangan`). Pharmacy lists, map,
  missions and pharmacy selection in scan endpoints enforce this scope. Demo
  pharmacy records remain in the database but are hidden from buyer selection.
- Imported 44 OpenStreetMap pharmacy records from administrative area `UZ-NG`.
  Snapshot time: `2026-09-26T12:15:05Z`. OSM records do not verify opening hours,
  licensing, medicine availability or participation in DoriIshonch.
- Query: `[out:json][timeout:25];area["ISO3166-2"="UZ-NG"]["boundary"="administrative"]->.pilot;nwr["amenity"="pharmacy"](area.pilot);out center;`
- Maintenance import: `cd backend && .venv/bin/python scripts/import_namangan.py /path/to/namangan-osm.json`.
  Only use the snapshot returned by this area query. Back up the database first.
  The importer upserts by OSM ID and does not reset demo data or the ledger.
- OSM data attribution: https://www.openstreetmap.org/copyright (ODbL).

## Result wording

An `at_pharmacy` demo pack scanned in `after` mode has no sale record in the
demo database. It does not prove a cash-register violation. The result now says
“Sotuv qaydi topilmadi” and explicitly identifies demo results. The warning
severity is retained; a missing sale is never converted to an authenticity claim.

The main result shows the medicine, expiry and source. Checks, manufacturer and
chain history are available under “Batafsil maʼlumot”. The scan page and map
remove repeated explanatory panels. Existing buyer account/photo reward work
remains unimplemented; current points are demo points.

## Deployment

Keep the existing Cloudflare tunnel. Build outside the live `.next` directory,
preserve prior static chunks, back up SQLite, import the OSM snapshot and restart
the backend with `SEED_ON_STARTUP=false`. No schema reset or migration is needed.

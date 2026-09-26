import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal
from app.models import Participant
from app.services.places import _place


def import_snapshot(path: Path) -> int:
    data = json.loads(path.read_text())
    elements = data["elements"]
    if not isinstance(elements, list) or not data.get("osm3s", {}).get("timestamp_osm_base"):
        raise ValueError("OpenStreetMap snapshot talab qilinadi")
    imported = 0
    with SessionLocal() as db:
        for element in elements:
            place = _place(element)
            if not place or (element.get("tags") or {}).get("amenity") != "pharmacy":
                continue
            pharmacy = db.query(Participant).filter(Participant.osm_id == place.osm_id).first()
            if pharmacy is None:
                pharmacy = Participant(kind="pharmacy", osm_id=place.osm_id, license_ok=False, is_demo=False)
                db.add(pharmacy)
            pharmacy.name = place.name
            pharmacy.address = place.address
            pharmacy.lat, pharmacy.lon = place.lat, place.lon
            pharmacy.region = "Namangan"
            imported += 1
        db.commit()
    return imported


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UZ-NG hududidan olingan OSM dorixona snapshotini import qilish")
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    print(f"Namangan: {import_snapshot(args.snapshot)} ta OSM yozuvi saqlandi")

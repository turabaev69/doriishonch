"""Oʻzbekiston hududlari (14 ta) — xarita va statistika uchun maʼlumotnoma.

Koordinata — hudud markazi (xaritani yaqinlashtirish uchun). `aliases` — bazadagi region yozuvlari.
"""

REGIONS = [
    {"key": "toshkent_sh", "name": "Toshkent shahri", "center": "Toshkent", "lat": 41.3111, "lon": 69.2797, "aliases": ["Toshkent", "Toshkent sh."]},
    {"key": "toshkent_v", "name": "Toshkent viloyati", "center": "Nurafshon", "lat": 41.0406, "lon": 69.3533, "aliases": ["Toshkent viloyati"]},
    {"key": "andijon", "name": "Andijon", "center": "Andijon", "lat": 40.7821, "lon": 72.3442, "aliases": ["Andijon"]},
    {"key": "namangan", "name": "Namangan", "center": "Namangan", "lat": 40.9983, "lon": 71.6726, "aliases": ["Namangan", "Namangan viloyati", "Namangan shahri"]},
    {"key": "fargona", "name": "Fargʻona", "center": "Fargʻona", "lat": 40.3864, "lon": 71.7864, "aliases": ["Fargʻona"]},
    {"key": "sirdaryo", "name": "Sirdaryo", "center": "Guliston", "lat": 40.4897, "lon": 68.7842, "aliases": ["Sirdaryo"]},
    {"key": "jizzax", "name": "Jizzax", "center": "Jizzax", "lat": 40.1158, "lon": 67.8422, "aliases": ["Jizzax"]},
    {"key": "samarqand", "name": "Samarqand", "center": "Samarqand", "lat": 39.6542, "lon": 66.9597, "aliases": ["Samarqand"]},
    {"key": "qashqadaryo", "name": "Qashqadaryo", "center": "Qarshi", "lat": 38.8606, "lon": 65.7891, "aliases": ["Qashqadaryo"]},
    {"key": "surxondaryo", "name": "Surxondaryo", "center": "Termiz", "lat": 37.2242, "lon": 67.2783, "aliases": ["Surxondaryo"]},
    {"key": "navoiy", "name": "Navoiy", "center": "Navoiy", "lat": 40.0844, "lon": 65.3792, "aliases": ["Navoiy"]},
    {"key": "buxoro", "name": "Buxoro", "center": "Buxoro", "lat": 39.7747, "lon": 64.4286, "aliases": ["Buxoro"]},
    {"key": "xorazm", "name": "Xorazm", "center": "Urganch", "lat": 41.5500, "lon": 60.6333, "aliases": ["Xorazm"]},
    {"key": "qoraqalpogiston", "name": "Qoraqalpogʻiston Respublikasi", "center": "Nukus", "lat": 42.4600, "lon": 59.6100, "aliases": ["Qoraqalpogʻiston"]},
]
UZ_CENTER = {"lat": 41.3, "lon": 64.6, "zoom": 5.4}


def region_key(name: str) -> str | None:
    for r in REGIONS:
        if name in r["aliases"] or name == r["name"]:
            return r["key"]
    return None

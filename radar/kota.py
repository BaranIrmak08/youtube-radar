"""Günlük YouTube kota defteri (data/kota.json).

YouTube kotası Pasifik saatiyle gece yarısı sıfırlanır (TSİ 11:00, yaz saatinde 10:00).
Günlük tarama ve konu aramaları harcadıklarını buraya yazar; konu araması, o gün
taramaya yer kalacak kadar bütçe yoksa başlamaz.
"""
from datetime import datetime, timedelta
from pathlib import Path

from radar.store import kaydet, yukle

TAVAN = 9_500          # günlük 10.000 birimin güvenli üst sınırı
TARAMA_PAYI = 7_500    # o gün tarama henüz yapılmadıysa ona ayrılan pay
KONU_EN_COK = 1_200    # tek bir konu araması en çok bu kadar harcar
SAKLA_GUN = 14

try:
    from zoneinfo import ZoneInfo
    _PASIFIK = ZoneInfo("America/Los_Angeles")
except Exception:  # Windows'ta tzdata yoksa: kış saati (UTC-8) varsayılır
    _PASIFIK = None


def kota_gunu(now: datetime) -> str:
    yerel = now.astimezone(_PASIFIK) if _PASIFIK else now - timedelta(hours=8)
    return yerel.strftime("%Y-%m-%d")


def bugun(yol: Path, now: datetime) -> dict:
    kayit = yukle(yol).get(kota_gunu(now)) or {}
    return {"toplam": kayit.get("toplam", 0), "tarama": bool(kayit.get("tarama"))}


def ekle(yol: Path, now: datetime, birim: int, tarama: bool = False) -> None:
    defter = yukle(yol)
    gun = kota_gunu(now)
    kayit = defter.get(gun) or {"toplam": 0, "tarama": False}
    kayit["toplam"] = kayit.get("toplam", 0) + int(birim)
    kayit["tarama"] = bool(kayit.get("tarama")) or tarama
    defter[gun] = kayit
    for eski in sorted(defter)[:-SAKLA_GUN]:
        defter.pop(eski)
    kaydet(yol, defter)


def tarama_butcesi(yol: Path, now: datetime) -> int:
    return max(0, TAVAN - bugun(yol, now)["toplam"])


def konu_butcesi(yol: Path, now: datetime) -> int:
    b = bugun(yol, now)
    kalan = TAVAN - b["toplam"] - (0 if b["tarama"] else TARAMA_PAYI)
    return max(0, min(KONU_EN_COK, kalan))

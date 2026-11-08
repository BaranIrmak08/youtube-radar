"""Kat skoru: videonun izlenmesi ÷ kanalın normali."""
import math
import statistics
from datetime import datetime

NORMAL_VIDEO = 20
NORMAL_MIN_VIDEO = 5
YENI_KANAL_GUN = 30
YAS_REFERANS_GUN = 7  # ilk gerçek verilerle ayarlanacak
YAS_MIN_GUN = 0.25


def zaman(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def yas_gun(iso: str, now: datetime) -> float:
    return (now - zaman(iso)).total_seconds() / 86400


def normal(views: list[int]) -> float | None:
    """views: en yeniden eskiye. Son 20 videonun ortancası; yetersizse None."""
    son = views[:NORMAL_VIDEO]
    if len(son) < NORMAL_MIN_VIDEO:
        return None
    m = statistics.median(son)
    return m if m > 0 else None


def yeni_kanal_mi(channel: dict, now: datetime) -> bool:
    if (channel.get("video_count") or 0) < NORMAL_MIN_VIDEO:
        return True
    pub = channel.get("published")
    return bool(pub) and yas_gun(pub, now) < YENI_KANAL_GUN


def yas_carpani(age_days: float) -> float:
    return min(1.0, math.sqrt(max(age_days, YAS_MIN_GUN) / YAS_REFERANS_GUN))


def skorla(video: dict, normal_deger: float, now: datetime) -> dict:
    kat = video["views"] / normal_deger
    return {"kat": kat, "duzeltilmis": kat / yas_carpani(yas_gun(video["published"], now))}

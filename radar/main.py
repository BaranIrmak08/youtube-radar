"""Günlük tarama: keşif, havuz takibi, kanal normalleri, liste üretimi."""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.api import KotaBitti, YouTube
from radar.plan import gunun_aramalari, gunun_ulkeleri
from radar.score import normal, skorla, yas_gun, yeni_kanal_mi
from radar.store import kaydet, yukle

LISTE_GUN = 7
ARAMA_SAAT = 48
ALT_SINIR = 5_000
HAVUZ_GUNLUK = 300
HAVUZ_SON = 5
NORMAL_TAZE_GUN = 3
KAT_MIN = 5
DILLER = {"tr", "en"}
INGILIZCE_ULKELER = {"US", "GB", "CA", "AU", "IE", "NZ"}
REKLAM_BEGENI_ORANI = 0.001  # beğeni/izlenme bunun altındaysa muhtemel reklam


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _ulke_dili(ulke: str | None) -> str | None:
    if not ulke:
        return None
    if ulke == "TR":
        return "tr"
    return "en" if ulke in INGILIZCE_ULKELER else ulke.lower()


def dil(v: dict, ch: dict | None = None) -> str | None:
    """Videonun dili: ses dili, yoksa kanal ülkesi, yoksa bulunduğu arama ülkesi."""
    return v.get("lang") or _ulke_dili((ch or {}).get("country")) or _ulke_dili(v.get("bulundu"))


def on_eleme(v: dict) -> bool:
    """Kanal bilgisi gerekmeden elenebilenler (kota harcanmadan önce)."""
    if v.get("is_live"):
        return False
    if (v.get("channel_title") or "").endswith(" - Topic"):
        return False
    likes = v.get("likes")
    if likes is not None and v["views"] >= ALT_SINIR and likes / v["views"] < REKLAM_BEGENI_ORANI:
        return False
    d = dil(v)
    return d is None or d in DILLER


def _kesif(yt, kanallar: dict, now: datetime, bulunan: dict, taze: dict) -> None:
    gun_no = now.toordinal()
    for r in gunun_ulkeleri(gun_no):
        for v in yt.trend(r):
            bulunan.setdefault(v["id"], r)
            taze[v["id"]] = v
    after = _iso(now - timedelta(hours=ARAMA_SAAT))
    for r, k in gunun_aramalari(gun_no):
        for i in yt.ara(r, k, after):
            bulunan.setdefault(i, r)
    sirali = sorted(kanallar.values(), key=lambda c: c.get("kontrol") or "")
    for ch in sirali[:HAVUZ_GUNLUK]:
        if ch.get("uploads"):
            for i in yt.son_yuklemeler(ch["uploads"], HAVUZ_SON):
                bulunan.setdefault(i, ch.get("country") or "")
        ch["kontrol"] = _iso(now)


def _normaller(yt, videolar: dict, kanallar: dict, now: datetime) -> None:
    sinir = _iso(now - timedelta(days=NORMAL_TAZE_GUN))
    gerek = []
    for v in sorted(videolar.values(), key=lambda v: -v["views"]):
        if v["views"] < ALT_SINIR:
            continue
        ch = kanallar.get(v["channel_id"])
        if (ch is None or (ch.get("normal_tarih") or "") < sinir) and v["channel_id"] not in gerek:
            gerek.append(v["channel_id"])
    for ch in yt.kanallar(gerek):
        eski = kanallar.get(ch["id"], {})
        kayit = {**eski, **ch}
        kayit.setdefault("kontrol", _iso(now))
        kanallar[ch["id"]] = kayit
        if ch.get("uploads"):
            ids = yt.son_yuklemeler(ch["uploads"], 20)
            gorulen = {v["id"]: v["views"] for v in yt.videolar(ids)}
            kayit["normal_views"] = {i: gorulen[i] for i in ids if i in gorulen}
        kayit["normal_tarih"] = _iso(now)


def _satir(v: dict, ch: dict) -> dict:
    return {
        "id": v["id"], "title": v["title"], "channel_id": v["channel_id"],
        "channel_title": v.get("channel_title") or ch.get("title", ""),
        "views": v["views"], "published": v["published"], "is_short": v["is_short"],
        "thumb": v.get("thumb"), "category_id": v.get("category_id"),
        "ulke": (dil(v, ch) or "").upper(),
    }


def liste_kur(videolar: dict, kanallar: dict, now: datetime) -> tuple[list, list]:
    satirlar, yeniler = [], {}
    for v in videolar.values():
        ch = kanallar.get(v["channel_id"])
        if v["views"] < ALT_SINIR or ch is None or not on_eleme(v):
            continue
        if dil(v, ch) not in DILLER or (ch.get("title") or "").endswith(" - Topic"):
            continue
        digerleri = [n for i, n in (ch.get("normal_views") or {}).items() if i != v["id"]]
        n = normal(digerleri)
        satir = _satir(v, ch)
        if n is None or yeni_kanal_mi(ch, now):
            onceki = yeniler.get(ch["id"])
            if onceki is None or v["views"] > onceki["en_iyi"]["views"]:
                yeniler[ch["id"]] = {
                    "channel_id": ch["id"], "channel_title": ch.get("title") or satir["channel_title"],
                    "kanal_yasi_gun": round(yas_gun(ch["published"], now), 1) if ch.get("published") else None,
                    "video_sayisi": ch.get("video_count"), "subs": ch.get("subs"), "en_iyi": satir,
                }
            continue
        s = skorla(v, n, now)
        if s["kat"] < KAT_MIN:
            continue
        satirlar.append({**satir, "normal": n, "kat": round(s["kat"], 2), "duzeltilmis": round(s["duzeltilmis"], 2)})
    satirlar.sort(key=lambda r: -r["duzeltilmis"])
    yeni = sorted(yeniler.values(), key=lambda k: -k["en_iyi"]["views"])
    return satirlar, yeni


def calistir(yt, veri_dir: Path, site_dir: Path, now: datetime) -> dict:
    veri_dir, site_dir = Path(veri_dir), Path(site_dir)
    videolar = yukle(veri_dir / "videolar.json")
    kanallar = yukle(veri_dir / "kanallar.json")
    bulunan, taze = {}, {}
    kota_bitti = False
    try:
        _kesif(yt, kanallar, now, bulunan, taze)
        eksik = [i for i in dict.fromkeys(list(bulunan) + list(videolar)) if i not in taze]
        for v in yt.videolar(eksik):
            taze[v["id"]] = v
    except KotaBitti:
        kota_bitti = True

    for i, v in taze.items():
        if yas_gun(v["published"], now) > LISTE_GUN:
            continue
        kayit = videolar.get(i, {})
        gecmis = kayit.get("gecmis", [])
        bulundu = kayit.get("bulundu") or bulunan.get(i, "")
        kayit.update(v)
        kayit["bulundu"] = bulundu
        kayit["gecmis"] = gecmis + [[_iso(now), v["views"]]]
        videolar[i] = kayit
    videolar = {i: v for i, v in videolar.items()
                if yas_gun(v["published"], now) <= LISTE_GUN and on_eleme(v)}

    if not kota_bitti:
        try:
            _normaller(yt, videolar, kanallar, now)
        except KotaBitti:
            kota_bitti = True

    satirlar, yeni = liste_kur(videolar, kanallar, now)
    liste = {"guncellendi": _iso(now), "harcanan": yt.harcanan, "kota_bitti": kota_bitti,
             "videolar": satirlar, "yeni_kanallar": yeni}
    kaydet(veri_dir / "videolar.json", videolar)
    kaydet(veri_dir / "kanallar.json", kanallar)
    kaydet(site_dir / "liste.json", liste)
    return liste


def sadece_liste(veri_dir: Path, site_dir: Path, now: datetime) -> dict:
    """API'ye gitmeden, kayıtlı veriden listeyi yeniden üretir (filtre değişikliği sonrası)."""
    veri_dir, site_dir = Path(veri_dir), Path(site_dir)
    videolar = yukle(veri_dir / "videolar.json")
    kanallar = yukle(veri_dir / "kanallar.json")
    eski = yukle(site_dir / "liste.json")
    satirlar, yeni = liste_kur(videolar, kanallar, now)
    liste = {"guncellendi": eski.get("guncellendi") or _iso(now), "harcanan": eski.get("harcanan", 0),
             "kota_bitti": eski.get("kota_bitti", False), "videolar": satirlar, "yeni_kanallar": yeni}
    kaydet(site_dir / "liste.json", liste)
    return liste


def main() -> int:
    kok = Path(__file__).resolve().parent.parent
    if "--sadece-liste" in sys.argv:
        eski = yukle(kok / "site" / "liste.json")
        an = datetime.fromisoformat(eski["guncellendi"].replace("Z", "+00:00")) if eski.get("guncellendi") \
            else datetime.now(timezone.utc)
        liste = sadece_liste(kok / "data", kok / "site", an)
        print(f"Liste yeniden üretildi: {len(liste['videolar'])} video, {len(liste['yeni_kanallar'])} yeni kanal")
        return 0
    key = os.environ.get("YT_API_KEY")
    if not key:
        print("Hata: YT_API_KEY ortam değişkeni ayarlı değil.", file=sys.stderr)
        return 1
    liste = calistir(YouTube(key), kok / "data", kok / "site", datetime.now(timezone.utc))
    print(f"Tarama bitti: {len(liste['videolar'])} video, {len(liste['yeni_kanallar'])} yeni kanal, "
          f"{liste['harcanan']} birim kota" + (" (kota bitti)" if liste["kota_bitti"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

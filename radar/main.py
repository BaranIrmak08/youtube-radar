"""Günlük tarama: keşif, havuz takibi, kanal normalleri, liste üretimi."""
import os
import re
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
NORMAL_MIN_YAS_GUN = 3  # normal hesabına bundan genç yüklemeler girmez (henüz izlenmediler)
NORMAL_SAYFA = 3        # çok yükleyen kanallarda en çok 3 × 50 yükleme geriye gidilir
NORMAL_SURUM = 2        # normal hesabı değişince eski kayıtlar yeniden çekilsin
KAT_MIN = 5
DILLER = {"tr", "en"}
INGILIZCE_ULKELER = {"US", "GB", "CA", "AU", "IE", "NZ"}
REKLAM_BEGENI_ORANI = 0.001  # beğeni/izlenme bunun altındaysa muhtemel reklam
# Kurum (haber, dizi, film, spor kulübü, TV) kanalları: yalnızca bağımsız üreticiler kalsın.
KURUM_KATEGORILER = {"25"}  # Haber ve Politika
KURUM_BASLIK = re.compile(
    r"(?i)(\bbölüm\b|\bfragman|\btanıtım\b|\bepisode\b|\bep\.?\s*\d+|\btrailer\b|\bteaser\b|\bfull movie\b"
    r"|maç özeti|\bhighlights?\b|\beng sub\b|\bfull game\b)")
KURUM_KANAL = re.compile(
    r"(?i)(\btv\b|\bnews\b|\bhaber|\bsports?\b|\bspor\b|\bnetwork\b|\bpictures\b|\bfilms?\b|\brecords\b"
    r"|official|\bmedia\b|\bmedya\b|\bfm\b|\bradio\b|\bgeo\b|\bspotv\b|\bhighlights?\b|\bmovies?\b"
    r"|\bfc\b|\bleague\b|\bclips?\b|\bcinema\b|\bkino)")
YASAK_ULKELER = {"IN", "PK", "BD"}  # videolarını sık sık yanlışlıkla İngilizce işaretliyorlar
# Arap (Urduca dahil) ve Hint alfabeleri (Devanagari, Bengal, Gurmukhi, Tamil, Telugu vb.)
YABANCI_YAZI = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\u0900-\u0DFF]")


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
    if YABANCI_YAZI.search(v.get("title") or ""):
        return False
    likes = v.get("likes")
    if likes is not None and v["views"] >= ALT_SINIR and likes / v["views"] < REKLAM_BEGENI_ORANI:
        return False
    d = dil(v)
    return d is None or d in DILLER


def kurum_nedeni(v: dict) -> str | None:
    """Videonun kendisinden anlaşılan kurum işareti (kanal bilgisi gerekmez)."""
    if v.get("category_id") in KURUM_KATEGORILER:
        return "haber kategorisi"
    if KURUM_BASLIK.search(v.get("title") or ""):
        return "başlık"
    if KURUM_KANAL.search(v.get("channel_title") or ""):
        return "kanal adı"
    return None


def engel_yukle(yol: Path) -> set[str]:
    """data/engel.txt ve data/izin.txt: her satırda bir kanal ID'si ya da kanal adı; # ile başlayanlar açıklama."""
    try:
        satirlar = Path(yol).read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    out = set()
    for s in satirlar:
        s = s.split(" #")[0].strip()  # "UC... # Kanal adı" biçimindeki açıklamayı at
        if s and not s.startswith("#"):
            out.add(s.casefold())
    return out


def kurum_kanallari(videolar: dict, kanallar: dict, engel: set[str],
                    izin: set[str] = frozenset()) -> dict[str, str]:
    """Elenecek kanallar: kanal kaydında işaretli, bir videosu kurum işareti taşıyan ya da engel listesinde.
    İzin listesindeki kanallar (yanlış alarm) hiçbir durumda elenmez."""
    # "engel listesi" işareti kalıcı değil: listeden çıkarılan kanal geri gelir.
    out = {cid: ch["kurum"] for cid, ch in kanallar.items() if ch.get("kurum") and ch["kurum"] != "engel listesi"}
    for cid, ch in kanallar.items():
        if cid.casefold() in engel or (ch.get("title") or "").strip().casefold() in engel:
            out.setdefault(cid, "engel listesi")
    for v in videolar.values():
        cid = v["channel_id"]
        if cid in out:
            continue
        neden = kurum_nedeni(v)
        if neden is None and (cid.casefold() in engel or (v.get("channel_title") or "").strip().casefold() in engel):
            neden = "engel listesi"
        if neden:
            out[cid] = neden
    if izin:
        adlar = {cid: (ch.get("title") or "").strip().casefold() for cid, ch in kanallar.items()}
        adlar.update({v["channel_id"]: (v.get("channel_title") or "").strip().casefold() for v in videolar.values()})
        out = {cid: n for cid, n in out.items() if cid.casefold() not in izin and adlar.get(cid) not in izin}
    return out


def _yasak_ulke(ch: dict | None) -> bool:
    return (ch or {}).get("country") in YASAK_ULKELER


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
    sirali = sorted((c for c in kanallar.values()
                     if c.get("uploads") and not c.get("kurum") and not _yasak_ulke(c)),
                    key=lambda c: c.get("kontrol") or "")
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
        bayat = ch is None or (ch.get("normal_tarih") or "") < sinir or ch.get("normal_surum") != NORMAL_SURUM
        if bayat and v["channel_id"] not in gerek:
            gerek.append(v["channel_id"])
    for ch in yt.kanallar(gerek):
        eski = kanallar.get(ch["id"], {})
        kayit = {**eski, **ch}
        kayit.setdefault("kontrol", _iso(now))
        kanallar[ch["id"]] = kayit
        if ch.get("uploads") and not _yasak_ulke(ch):
            once = _iso(now - timedelta(days=NORMAL_MIN_YAS_GUN))
            ids = yt.son_yuklemeler(ch["uploads"], 20, once=once, sayfa=NORMAL_SAYFA)
            gorulen = {v["id"]: v["views"] for v in yt.videolar(ids)}
            kayit["normal_views"] = {i: gorulen[i] for i in ids if i in gorulen}
        kayit["normal_tarih"] = _iso(now)
        kayit["normal_surum"] = NORMAL_SURUM


def _satir(v: dict, ch: dict) -> dict:
    return {
        "id": v["id"], "title": v["title"], "channel_id": v["channel_id"],
        "channel_title": v.get("channel_title") or ch.get("title", ""),
        "views": v["views"], "published": v["published"], "is_short": v["is_short"],
        "thumb": v.get("thumb"), "category_id": v.get("category_id"),
        "ulke": (dil(v, ch) or "").upper(),
    }


def liste_kur(videolar: dict, kanallar: dict, now: datetime, engel: set[str] = frozenset(),
              izin: set[str] = frozenset()) -> tuple[list, list]:
    satirlar, yeniler = [], {}
    kurumlar = kurum_kanallari(videolar, kanallar, engel, izin)
    for v in videolar.values():
        ch = kanallar.get(v["channel_id"])
        if v["views"] < ALT_SINIR or ch is None or not on_eleme(v):
            continue
        if v["channel_id"] in kurumlar or _yasak_ulke(ch):
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
    engel, izin = engel_yukle(veri_dir / "engel.txt"), engel_yukle(veri_dir / "izin.txt")
    kurumlar = kurum_kanallari(videolar, kanallar, engel, izin)
    for cid, ch in kanallar.items():
        if ch.get("kurum") and cid not in kurumlar:
            ch.pop("kurum")  # izin listesine alınmış
    for cid, neden in kurumlar.items():
        if not kanallar.get(cid, {}).get("kurum"):
            ad = next((v.get("channel_title") for v in videolar.values() if v["channel_id"] == cid), "")
            kanallar.setdefault(cid, {"id": cid, "title": ad})["kurum"] = neden
    videolar = {i: v for i, v in videolar.items()
                if yas_gun(v["published"], now) <= LISTE_GUN and on_eleme(v)
                and v["channel_id"] not in kurumlar
                and not _yasak_ulke(kanallar.get(v["channel_id"]))}

    if not kota_bitti:
        try:
            _normaller(yt, videolar, kanallar, now)
        except KotaBitti:
            kota_bitti = True

    satirlar, yeni = liste_kur(videolar, kanallar, now, engel, izin)
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
    satirlar, yeni = liste_kur(videolar, kanallar, now, engel_yukle(veri_dir / "engel.txt"),
                               engel_yukle(veri_dir / "izin.txt"))
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

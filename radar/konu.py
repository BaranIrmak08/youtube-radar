"""Konuya göre viral video araması.

Çekirdek (`konu_ara`, `calistir_konu`) GitHub'dan bağımsızdır: bir YouTube istemcisi, veri klasörü
ve bir istek alır, sonucu `site/konular/` altına JSON olarak yazar. Bugün GitHub Actions'tan
`python -m radar.konu` ile çağrılıyor (istek: data/konu-istek.json). Halka açık bir sunucuya
geçilirse aynı fonksiyon bir HTTP uç noktasından çağrılabilir.
"""
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar import kota
from radar.api import KotaBitti, YouTube
from radar.main import (_iso, _normaller, engel_yukle, kurumlari_isle, liste_kur, on_eleme)
from radar.score import yas_gun
from radar.store import kaydet, yukle

KONU_GUN = 7
KONU_KAT_MIN = 3          # konu sonuçları azdır; günlük taramadaki 5 yerine 3
EN_COK_IFADE = 3
IFADE_UZUNLUK = 60
KONU_SAKLA = 10
KONU_BOLGELER = ("US", "TR")
KONU_EN_AZ_BUTCE = 500    # bundan az kota kaldıysa arama başlamaz
ID_DESENI = re.compile(r"^[a-z0-9-]{1,40}$")


def ifadeleri_ayir(metin: str) -> list[str]:
    parcalar = [p.strip()[:IFADE_UZUNLUK] for p in (metin or "").split(",")]
    return [p for p in parcalar if p][:EN_COK_IFADE]


def istek_gecerli(istek) -> bool:
    return (isinstance(istek, dict) and isinstance(istek.get("id"), str) and bool(ID_DESENI.match(istek["id"]))
            and isinstance(istek.get("konu"), str) and len(istek["konu"]) <= 200
            and bool(ifadeleri_ayir(istek["konu"])))


def konu_ara(yt, ifadeler: list[str], kanallar: dict, now: datetime,
             engel: set[str], izin: set[str]) -> tuple[list, list, bool]:
    """İfadeleri son KONU_GUN günde arar, mevcut kat hesabı ve filtrelerle sıralar."""
    after = _iso(now - timedelta(days=KONU_GUN))
    bulunan, videolar, kota_bitti = {}, {}, False
    try:
        for ifade in ifadeler:
            for bolge in KONU_BOLGELER:
                for i in yt.ara(bolge, "", after, q=ifade):
                    bulunan.setdefault(i, bolge)
        for v in yt.videolar(list(bulunan)):
            videolar[v["id"]] = {**v, "bulundu": bulunan.get(v["id"], "")}
    except KotaBitti:
        kota_bitti = True
    videolar = {i: v for i, v in videolar.items() if yas_gun(v["published"], now) <= KONU_GUN and on_eleme(v)}
    kurumlar = kurumlari_isle(videolar, kanallar, engel, izin)
    videolar = {i: v for i, v in videolar.items() if v["channel_id"] not in kurumlar}
    if not kota_bitti:
        try:
            _normaller(yt, videolar, kanallar, now)
        except KotaBitti:
            kota_bitti = True
    satirlar, yeni = liste_kur(videolar, kanallar, now, engel, izin, kat_min=KONU_KAT_MIN)
    return satirlar, yeni, kota_bitti


def _dizin_oku(yol: Path) -> list:
    d = yukle(yol)
    return d if isinstance(d, list) else []


def calistir_konu(yt, veri_dir: Path, site_dir: Path, istek: dict, now: datetime) -> dict | None:
    """İsteği işler, sonucu site/konular/<id>.json ve index.json'a yazar. Aynı istek ikinci kez işlenmez."""
    veri_dir, konular = Path(veri_dir), Path(site_dir) / "konular"
    dizin = _dizin_oku(konular / "index.json")
    if any(d.get("id") == istek["id"] for d in dizin):
        return None
    ifadeler = ifadeleri_ayir(istek["konu"])
    sonuc = {"id": istek["id"], "konu": istek["konu"].strip(), "ifadeler": ifadeler, "tarih": _iso(now),
             "harcanan": 0, "kota_bitti": False, "videolar": [], "yeni_kanallar": []}
    if kota.konu_butcesi(veri_dir / "kota.json", now) < KONU_EN_AZ_BUTCE:
        sonuc["hata"] = "Bugünlük kota yetmiyor. Kota TSİ 11:00'de yenilenir, sonra tekrar dene."
    else:
        kanallar = yukle(veri_dir / "kanallar.json")
        satirlar, yeni, kota_bitti = konu_ara(yt, ifadeler, kanallar, now, engel_yukle(veri_dir / "engel.txt"),
                                              engel_yukle(veri_dir / "izin.txt"))
        kaydet(veri_dir / "kanallar.json", kanallar)
        kota.ekle(veri_dir / "kota.json", now, yt.harcanan)
        sonuc.update(harcanan=yt.harcanan, kota_bitti=kota_bitti, videolar=satirlar, yeni_kanallar=yeni)
    kaydet(konular / f"{istek['id']}.json", sonuc)
    ozet = {"id": sonuc["id"], "konu": sonuc["konu"], "tarih": sonuc["tarih"],
            "video_sayisi": len(sonuc["videolar"]) + len(sonuc["yeni_kanallar"])}
    if "hata" in sonuc:
        ozet["hata"] = sonuc["hata"]
    dizin = [ozet] + dizin
    for eski in dizin[KONU_SAKLA:]:
        if ID_DESENI.match(str(eski.get("id", ""))):
            (konular / f"{eski['id']}.json").unlink(missing_ok=True)
    kaydet(konular / "index.json", dizin[:KONU_SAKLA])
    return sonuc


def main() -> int:
    kok = Path(__file__).resolve().parent.parent
    if len(sys.argv) > 1 and sys.argv[1] != "--istek":
        istek = {"id": "e" + format(int(time.time()), "x"), "konu": " ".join(sys.argv[1:])}  # elle: python -m radar.konu ai shorts
    else:
        istek = yukle(kok / "data" / "konu-istek.json")
        if not istek:
            print("Bekleyen konu isteği yok.")
            return 0
    if not istek_gecerli(istek):
        print("Geçersiz konu isteği.", file=sys.stderr)
        return 1
    key = os.environ.get("YT_API_KEY")
    if not key:
        print("Hata: YT_API_KEY ortam değişkeni ayarlı değil.", file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc)
    yt = YouTube(key, butce=kota.konu_butcesi(kok / "data" / "kota.json", now))
    sonuc = calistir_konu(yt, kok / "data", kok / "site", istek, now)
    if sonuc is None:
        print("Bu istek daha önce işlenmiş.")
    elif "hata" in sonuc:
        print("Konu araması yapılmadı:", sonuc["hata"])
    else:
        print(f"Konu araması bitti: {len(sonuc['videolar'])} video, {len(sonuc['yeni_kanallar'])} yeni kanal, "
              f"{sonuc['harcanan']} birim kota")
    return 0


if __name__ == "__main__":
    sys.exit(main())

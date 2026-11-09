import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from radar import main as radar_main
from radar.main import calistir
from tests.fake_yt import FakeYT

NOW = datetime(2026, 11, 8, 3, 0, tzinfo=timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def vid(i, ch, views, gun, **ek):
    v = {"id": i, "channel_id": ch, "channel_title": ch.upper(), "title": f"T {i}",
         "published": iso(NOW - timedelta(days=gun)), "views": views, "likes": views // 50,
         "is_live": False, "duration_s": 50, "is_short": True, "thumb": None, "category_id": "27", "lang": None}
    v.update(ek)
    return v


def dunya():
    videos = {
        "hit": vid("hit", "c_eski", 350_000, 1),
        "orta": vid("orta", "c_eski", 30_000, 1),
        "az": vid("az", "c_eski", 4_999, 1),
        "eski": vid("eski", "c_eski", 900_000, 8),
        "yeni1": vid("yeni1", "c_yeni", 1_000_000, 1),
        "canli": vid("canli", "c_eski", 500_000, 1, is_live=True),
        "hintce": vid("hintce", "c_hint", 500_000, 1, lang="hi"),
        "reklam": vid("reklam", "c_rek", 4_000_000, 1, likes=100),
        "sarki": vid("sarki", "c_topic", 800_000, 1, channel_title="Sanatçı - Topic"),
    }
    for n in range(20):
        videos[f"b{n}"] = vid(f"b{n}", "c_eski", 10_000, 30 + n)
    channels = {
        "c_eski": {"id": "c_eski", "title": "Eski", "country": "TR", "published": iso(NOW - timedelta(days=700)),
                   "video_count": 100, "subs": 50_000, "uploads": "U_eski"},
        "c_yeni": {"id": "c_yeni", "title": "Yeni", "country": "US", "published": iso(NOW - timedelta(days=2)),
                   "video_count": 1, "subs": None, "uploads": "U_yeni"},
    }
    uploads = {"U_eski": ["hit", "orta", "az"] + [f"b{n}" for n in range(20)], "U_yeni": ["yeni1"]}
    search = {"TR": ["hit", "orta", "az", "canli"], "US": ["yeni1", "hintce", "reklam", "sarki"]}
    return dict(videos=videos, channels=channels, uploads=uploads, search=search)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.veri = Path(self.tmp.name) / "data"
        self.site = Path(self.tmp.name) / "site"

    def tearDown(self):
        self.tmp.cleanup()

    def calis(self, **kw):
        return calistir(FakeYT(**{**dunya(), **kw}), self.veri, self.site, NOW)

    def test_patlayan_video_ust_sirada(self):
        liste = self.calis()
        ids = [v["id"] for v in liste["videolar"]]
        self.assertEqual(ids, ["hit"])
        self.assertEqual(liste["videolar"][0]["kat"], 35.0)
        self.assertEqual(liste["videolar"][0]["normal"], 10_000)
        self.assertEqual(liste["videolar"][0]["ulke"], "TR")

    def test_yeni_kanal_sekmesi(self):
        liste = self.calis()
        self.assertEqual([k["channel_id"] for k in liste["yeni_kanallar"]], ["c_yeni"])
        self.assertEqual(liste["yeni_kanallar"][0]["en_iyi"]["id"], "yeni1")
        self.assertNotIn("yeni1", [v["id"] for v in liste["videolar"]])

    def test_alt_sinir(self):
        liste = self.calis()
        hepsi = [v["id"] for v in liste["videolar"]] + [k["en_iyi"]["id"] for k in liste["yeni_kanallar"]]
        self.assertNotIn("az", hepsi)

    def test_kat_5_alti_listelenmez(self):
        liste = self.calis()
        self.assertNotIn("orta", [v["id"] for v in liste["videolar"]])
        self.assertTrue(all(v["kat"] >= 5 for v in liste["videolar"]))

    def test_ayiklananlar_listede_yok_ve_kota_harcamaz(self):
        yt = FakeYT(**dunya())
        liste = calistir(yt, self.veri, self.site, NOW)
        hepsi = [v["id"] for v in liste["videolar"]] + [k["en_iyi"]["id"] for k in liste["yeni_kanallar"]]
        for i in ("canli", "hintce", "reklam", "sarki"):
            self.assertNotIn(i, hepsi)
        for c in ("c_hint", "c_rek", "c_topic"):
            self.assertNotIn(c, yt.istenen_kanallar)
        kayit = json.loads((self.veri / "videolar.json").read_text(encoding="utf-8"))
        for i in ("canli", "hintce", "reklam", "sarki"):
            self.assertNotIn(i, kayit)

    def test_dil_kanal_ulkesinden(self):
        # dil bilgisi yok, kanal ülkesi Hindistan: elenir
        d = dunya()
        d["channels"]["c_eski"]["country"] = "IN"
        liste = calistir(FakeYT(**d), self.veri, self.site, NOW)
        self.assertEqual(liste["videolar"], [])

    def test_normal_taze_yuklemeleri_saymaz(self):
        # Çok yükleyen haber kanalı: son 25 yükleme birkaç saatlik, az izlenmiş.
        d = dunya()
        d["channels"]["c_haber"] = {"id": "c_haber", "title": "Haber", "country": "GB",
                                    "published": iso(NOW - timedelta(days=900)), "video_count": 5000,
                                    "subs": 1_000_000, "uploads": "U_haber"}
        d["videos"]["manset"] = vid("manset", "c_haber", 400_000, 0.5)
        taze = [f"t{n}" for n in range(25)]
        eski = [f"e{n}" for n in range(30)]
        for i in taze:
            d["videos"][i] = vid(i, "c_haber", 200, 0.2)
        for i in eski:
            d["videos"][i] = vid(i, "c_haber", 50_000, 4)
        d["uploads"]["U_haber"] = ["manset"] + taze + eski
        d["search"]["GB"] = ["manset"]
        liste = calistir(FakeYT(**d), self.veri, self.site, NOW)
        satir = next(v for v in liste["videolar"] if v["id"] == "manset")
        self.assertEqual(satir["normal"], 50_000)
        self.assertEqual(satir["kat"], 8.0)

    def test_eski_surum_normal_yenilenir(self):
        # Önceki sürümle (taze videolar dahil) hesaplanmış, henüz bayatlamamış normal yeniden çekilir.
        self.veri.mkdir(parents=True)
        eski_kayit = {**dunya()["channels"]["c_eski"], "normal_tarih": iso(NOW),
                      "normal_views": {f"x{n}": 100 for n in range(20)}}
        (self.veri / "kanallar.json").write_text(json.dumps({"c_eski": eski_kayit}), encoding="utf-8")
        liste = self.calis()
        self.assertEqual(liste["videolar"][0]["normal"], 10_000)

    def test_hint_arap_yazili_baslik_elenir(self):
        d = dunya()
        d["videos"]["mantra"] = vid("mantra", "c_eski", 400_000, 1, title="Kuber Mantra | कुबेर मंत्र")
        d["videos"]["urdu"] = vid("urdu", "c_eski", 400_000, 1, title="Drama 5 | ڈرامہ")
        d["search"]["TR"] = d["search"]["TR"] + ["mantra", "urdu"]
        liste = calistir(FakeYT(**d), self.veri, self.site, NOW)
        ids = [v["id"] for v in liste["videolar"]]
        self.assertIn("hit", ids)
        self.assertNotIn("mantra", ids)
        self.assertNotIn("urdu", ids)

    def _kanal(self, d, cid, ad, ulke="US", gun=500):
        d["channels"][cid] = {"id": cid, "title": ad, "country": ulke, "published": iso(NOW - timedelta(days=gun)),
                              "video_count": 300, "subs": 10_000, "uploads": "U_" + cid}
        d["uploads"]["U_" + cid] = [f"{cid}_b{n}" for n in range(20)]
        for n in range(20):
            d["videos"][f"{cid}_b{n}"] = vid(f"{cid}_b{n}", cid, 10_000, 30 + n, channel_title=ad)

    def _hepsi(self, liste):
        return [v["id"] for v in liste["videolar"]] + [k["en_iyi"]["id"] for k in liste["yeni_kanallar"]]

    def test_haber_kategorisi_elenir(self):
        d = dunya()
        self._kanal(d, "c_yorum", "Yorumcu")
        d["videos"]["siyaset"] = vid("siyaset", "c_yorum", 400_000, 1, category_id="25", channel_title="Yorumcu")
        d["search"]["US"] = d["search"]["US"] + ["siyaset"]
        yt = FakeYT(**d)
        liste = calistir(yt, self.veri, self.site, NOW)
        self.assertNotIn("siyaset", self._hepsi(liste))
        self.assertIn("hit", self._hepsi(liste))
        self.assertNotIn("c_yorum", yt.istenen_kanallar)

    def test_dizi_kanali_tumuyle_elenir(self):
        # Başlıkta "Bölüm" geçen kanalın sıradan videosu da listeden çıkar.
        d = dunya()
        self._kanal(d, "c_dizi", "Kara Sevda")
        d["videos"]["bolum"] = vid("bolum", "c_dizi", 900_000, 1, title="Kara Sevda 12. Bölüm", channel_title="Kara Sevda")
        d["videos"]["kamera"] = vid("kamera", "c_dizi", 400_000, 1, title="Kamera arkası", channel_title="Kara Sevda")
        d["search"]["TR"] = d["search"]["TR"] + ["bolum", "kamera"]
        liste = calistir(FakeYT(**d), self.veri, self.site, NOW)
        self.assertNotIn("bolum", self._hepsi(liste))
        self.assertNotIn("kamera", self._hepsi(liste))
        kanallar = json.loads((self.veri / "kanallar.json").read_text(encoding="utf-8"))
        self.assertTrue(kanallar["c_dizi"]["kurum"])

    def test_kurum_kanal_adi_elenir(self):
        d = dunya()
        self._kanal(d, "c_tv", "Show TV")
        d["videos"]["klip"] = vid("klip", "c_tv", 400_000, 1, title="Komik an", channel_title="Show TV")
        d["search"]["TR"] = d["search"]["TR"] + ["klip"]
        liste = calistir(FakeYT(**d), self.veri, self.site, NOW)
        self.assertNotIn("klip", self._hepsi(liste))

    def test_engel_listesi(self):
        d = dunya()
        self._kanal(d, "c_snl", "Saturday Night Live")
        d["videos"]["skec"] = vid("skec", "c_snl", 400_000, 1, title="Cold Open", channel_title="Saturday Night Live")
        d["search"]["US"] = d["search"]["US"] + ["skec"]
        self.veri.mkdir(parents=True)
        (self.veri / "engel.txt").write_text("# kurumlar" + chr(10) + "saturday night live" + chr(10), encoding="utf-8")
        liste = calistir(FakeYT(**d), self.veri, self.site, NOW)
        self.assertNotIn("skec", self._hepsi(liste))
        self.assertIn("hit", self._hepsi(liste))

    def test_izin_listesi_kurum_isaretini_kaldirir(self):
        d = dunya()
        self._kanal(d, "c_vlog", "Ayşe Vlog")
        d["videos"]["ozet"] = vid("ozet", "c_vlog", 400_000, 1, title="Tatil highlights", channel_title="Ayşe Vlog")
        d["search"]["TR"] = d["search"]["TR"] + ["ozet"]
        self.veri.mkdir(parents=True)
        calistir(FakeYT(**d), self.veri, self.site, NOW)
        (self.veri / "izin.txt").write_text("Ayşe Vlog" + chr(10), encoding="utf-8")
        liste = calistir(FakeYT(**d), self.veri, self.site, NOW)
        self.assertIn("ozet", self._hepsi(liste))
        kanallar = json.loads((self.veri / "kanallar.json").read_text(encoding="utf-8"))
        self.assertNotIn("kurum", kanallar["c_vlog"])

    def test_hint_kanali_ingilizce_isaretlese_de_elenir(self):
        d = dunya()
        self._kanal(d, "c_in", "Bhajan Songs", ulke="IN")
        d["videos"]["bhajan"] = vid("bhajan", "c_in", 400_000, 1, lang="en", channel_title="Bhajan Songs")
        d["search"]["US"] = d["search"]["US"] + ["bhajan"]
        liste = calistir(FakeYT(**d), self.veri, self.site, NOW)
        self.assertNotIn("bhajan", self._hepsi(liste))

    def test_sadece_liste_api_kullanmaz(self):
        self.calis()
        liste = radar_main.sadece_liste(self.veri, self.site, NOW)
        self.assertEqual([v["id"] for v in liste["videolar"]], ["hit"])

    def test_yedi_gun_temizlik(self):
        self.veri.mkdir(parents=True)
        (self.veri / "videolar.json").write_text(json.dumps({"eski": {**vid("eski", "c_eski", 1, 8), "gecmis": []}}),
                                                 encoding="utf-8")
        self.calis()
        kayit = json.loads((self.veri / "videolar.json").read_text(encoding="utf-8"))
        self.assertNotIn("eski", kayit)
        self.assertIn("hit", kayit)

    def test_gecmis_birikir(self):
        self.calis()
        self.calis()
        kayit = json.loads((self.veri / "videolar.json").read_text(encoding="utf-8"))
        self.assertEqual(len(kayit["hit"]["gecmis"]), 2)

    def test_kota_bitince_kismi_kayit(self):
        liste = self.calis(patla=3)
        self.assertTrue(liste["kota_bitti"])
        self.assertTrue((self.site / "liste.json").exists())
        self.assertTrue((self.veri / "videolar.json").exists())

    def test_anahtar_yoksa_cikis(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(radar_main.main(), 1)


if __name__ == "__main__":
    unittest.main()

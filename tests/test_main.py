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

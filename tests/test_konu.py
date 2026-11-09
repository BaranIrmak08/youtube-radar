import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar import kota
from radar.konu import calistir_konu, ifadeleri_ayir, istek_gecerli
from tests.fake_yt import FakeYT
from tests.test_main import NOW, iso, vid


def dunya():
    videos = {
        "ai1": vid("ai1", "c_ai", 600_000, 2, title="AI animation of a cat"),
        "ai2": vid("ai2", "c_ai", 20_000, 2, title="AI short"),
        "tv1": vid("tv1", "c_tv", 900_000, 1, title="AI news", channel_title="Big News"),
        "eski": vid("eski", "c_ai", 900_000, 9, title="AI eski"),
    }
    for n in range(20):
        videos[f"b{n}"] = vid(f"b{n}", "c_ai", 10_000, 30 + n)
    channels = {
        "c_ai": {"id": "c_ai", "title": "AI Kedi", "country": "US", "published": iso(NOW - timedelta(days=400)),
                 "video_count": 200, "subs": 10_000, "uploads": "U_ai"},
        "c_tv": {"id": "c_tv", "title": "Big News", "country": "US", "published": iso(NOW - timedelta(days=900)),
                 "video_count": 9000, "subs": 1_000_000, "uploads": "U_tv"},
    }
    uploads = {"U_ai": [f"b{n}" for n in range(20)], "U_tv": []}
    search = {("US", "ai animation"): ["ai1", "ai2", "tv1", "eski"], ("TR", "ai animation"): ["ai1"]}
    return dict(videos=videos, channels=channels, uploads=uploads, search=search)


class IfadeTest(unittest.TestCase):
    def test_ayir(self):
        self.assertEqual(ifadeleri_ayir(" ai animation, ai shorts ,, x, y "), ["ai animation", "ai shorts", "x"])

    def test_bos(self):
        self.assertEqual(ifadeleri_ayir(" , "), [])

    def test_uzun_kirpilir(self):
        self.assertEqual(len(ifadeleri_ayir("a" * 200)[0]), 60)

    def test_istek_gecerli(self):
        self.assertTrue(istek_gecerli({"id": "lx3k9a", "konu": "ai animation"}))
        self.assertFalse(istek_gecerli({"id": "../x", "konu": "ai"}))
        self.assertFalse(istek_gecerli({"id": "abc", "konu": ""}))


class KonuTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.veri = Path(self.tmp.name) / "data"
        self.site = Path(self.tmp.name) / "site"
        self.veri.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def calis(self, yt=None, istek=None):
        yt = yt or FakeYT(**dunya())
        istek = istek or {"id": "k1", "konu": "ai animation"}
        return yt, calistir_konu(yt, self.veri, self.site, istek, NOW)

    def test_konu_sonucu_ve_dizin(self):
        yt, sonuc = self.calis()
        ids = [v["id"] for v in sonuc["videolar"]]
        self.assertEqual(ids, ["ai1"])               # kat 60; ai2 kat 2 < 3; eski 7 günden eski
        self.assertNotIn("tv1", ids)                 # kurum kanalı
        self.assertIn(("US", "ai animation"), yt.aranan)
        dosya = json.loads((self.site / "konular" / "k1.json").read_text(encoding="utf-8"))
        self.assertEqual(dosya["konu"], "ai animation")
        dizin = json.loads((self.site / "konular" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(dizin[0]["id"], "k1")
        self.assertEqual(dizin[0]["video_sayisi"], 1)

    def test_kanal_normalleri_paylasilir(self):
        self.calis()
        kanallar = json.loads((self.veri / "kanallar.json").read_text(encoding="utf-8"))
        self.assertIn("normal_views", kanallar["c_ai"])
        self.assertTrue(kanallar["c_tv"]["kurum"])

    def test_engel_listesi(self):
        (self.veri / "engel.txt").write_text("c_ai # AI Kedi" + chr(10), encoding="utf-8")
        _, sonuc = self.calis()
        self.assertEqual(sonuc["videolar"], [])

    def test_kota_yetmezse_aramaz(self):
        kota.ekle(self.veri / "kota.json", NOW, 9_200, tarama=True)
        yt, sonuc = self.calis()
        self.assertIn("kota", sonuc["hata"])
        self.assertEqual(yt.harcanan, 0)
        dizin = json.loads((self.site / "konular" / "index.json").read_text(encoding="utf-8"))
        self.assertIn("hata", dizin[0])

    def test_harcama_deftere_yazilir(self):
        yt, _ = self.calis()
        self.assertEqual(kota.bugun(self.veri / "kota.json", NOW)["toplam"], yt.harcanan)

    def test_ayni_istek_iki_kez_islenmez(self):
        self.calis()
        yt2, sonuc = self.calis()
        self.assertIsNone(sonuc)
        self.assertEqual(yt2.harcanan, 0)

    def test_en_cok_10_arama_saklanir(self):
        for n in range(12):
            self.calis(istek={"id": f"k{n:02d}", "konu": "ai animation"})
        dizin = json.loads((self.site / "konular" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(dizin), 10)
        self.assertEqual(dizin[0]["id"], "k11")
        self.assertFalse((self.site / "konular" / "k00.json").exists())


class KotaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / "kota.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_gun_pasifik_saatine_gore(self):
        # 07:59 UTC hâlâ bir önceki Pasifik günü, 08:00 UTC yeni gün (kış saati)
        a = datetime(2026, 11, 9, 7, 59, tzinfo=timezone.utc)
        b = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)
        self.assertEqual(kota.kota_gunu(a), "2026-11-08")
        self.assertEqual(kota.kota_gunu(b), "2026-11-09")

    def test_ekle_ve_oku(self):
        kota.ekle(self.yol, NOW, 100)
        kota.ekle(self.yol, NOW, 50, tarama=True)
        self.assertEqual(kota.bugun(self.yol, NOW), {"toplam": 150, "tarama": True})

    def test_konu_butcesi(self):
        self.assertEqual(kota.konu_butcesi(self.yol, NOW), 1_200)        # tarama payı ayrılır, üst sınır
        kota.ekle(self.yol, NOW, 8_800, tarama=True)
        self.assertEqual(kota.konu_butcesi(self.yol, NOW), 700)          # 9.500 - 8.800

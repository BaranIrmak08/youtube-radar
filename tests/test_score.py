import math
import unittest
from datetime import datetime, timedelta, timezone

from radar.plan import DIL, SABIT, gunun_aramalari, gunun_ulkeleri
from radar.score import normal, skorla, yas_carpani, yeni_kanal_mi

NOW = datetime(2026, 11, 8, 3, 0, tzinfo=timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ScoreTest(unittest.TestCase):
    def test_normal_ortanca(self):
        self.assertEqual(normal([1000] * 19 + [1_000_000]), 1000)

    def test_normal_son_20(self):
        # yalnızca ilk 20 değer (en yeni 20 video) kullanılır
        self.assertEqual(normal([100] * 20 + [9_999_999] * 30), 100)

    def test_normal_sifir_ise_none(self):
        self.assertIsNone(normal([0] * 10))
        self.assertIsNone(normal([5000] * 4))

    def test_yeni_kanal(self):
        def ch(gun, vc):
            return {"published": iso(NOW - timedelta(days=gun)), "video_count": vc}
        self.assertTrue(yeni_kanal_mi(ch(10, 50), NOW))
        self.assertTrue(yeni_kanal_mi(ch(200, 3), NOW))
        self.assertFalse(yeni_kanal_mi(ch(200, 50), NOW))

    def test_yas_carpani(self):
        self.assertEqual(yas_carpani(7), 1.0)
        self.assertEqual(yas_carpani(30), 1.0)
        self.assertAlmostEqual(yas_carpani(0), math.sqrt(0.25 / 7))

    def test_skor_ornek(self):
        v = {"views": 350_000, "published": iso(NOW - timedelta(days=7))}
        s = skorla(v, 10_000, NOW)
        self.assertEqual(s["kat"], 35.0)
        self.assertEqual(s["duzeltilmis"], 35.0)

    def test_genc_video_one_cikar(self):
        genc = skorla({"views": 100_000, "published": iso(NOW - timedelta(days=1))}, 10_000, NOW)
        yasli = skorla({"views": 100_000, "published": iso(NOW - timedelta(days=7))}, 10_000, NOW)
        self.assertGreater(genc["duzeltilmis"], yasli["duzeltilmis"])


class PlanTest(unittest.TestCase):
    def test_plan_adet_ve_tekrarsiz(self):
        p = gunun_aramalari(739000)
        self.assertEqual(len(p), 60)
        self.assertEqual(len(set(p)), 60)

    def test_plan_yalniz_tr_en_ulkeleri(self):
        p = gunun_aramalari(739000)
        self.assertTrue(all(r in SABIT for r, _ in p))
        for r in SABIT:
            self.assertGreaterEqual(sum(1 for x, _ in p if x == r), 12)

    def test_plan_doner(self):
        self.assertNotEqual(gunun_aramalari(0), gunun_aramalari(1))

    def test_ulkeler_ve_dil(self):
        self.assertEqual(gunun_ulkeleri(0), SABIT)
        self.assertEqual(DIL["TR"], "tr")
        self.assertTrue(all(DIL[r] == "en" for r in SABIT if r != "TR"))


if __name__ == "__main__":
    unittest.main()

import math
import unittest
from datetime import datetime, timedelta, timezone

from radar.plan import DONUSUMLU, SABIT, gunun_aramalari, gunun_ulkeleri
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

    def test_plan_yarisi_sabit(self):
        p = gunun_aramalari(739000)
        sabit = [r for r, _ in p if r in SABIT]
        self.assertEqual(len(sabit), 30)
        for r in SABIT:
            self.assertGreaterEqual(sabit.count(r), 7)

    def test_plan_doner(self):
        a = [x for x in gunun_aramalari(0) if x[0] not in SABIT]
        b = [x for x in gunun_aramalari(1) if x[0] not in SABIT]
        self.assertNotEqual(a, b)

    def test_ulkeler(self):
        u = gunun_ulkeleri(0)
        self.assertEqual(u[:4], SABIT)
        self.assertEqual(len(u), 7)
        self.assertTrue(all(x in DONUSUMLU for x in u[4:]))


if __name__ == "__main__":
    unittest.main()

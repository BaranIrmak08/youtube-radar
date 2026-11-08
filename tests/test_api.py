import io
import json
import unittest
import urllib.error

from radar.api import KotaBitti, YouTube


class Yanit:
    def __init__(self, obj):
        self.b = json.dumps(obj).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_hata(kod, govde=b"{}"):
    return urllib.error.HTTPError("http://x?key=GIZLI123", kod, "hata", {}, io.BytesIO(govde))


class SahteOpener:
    def __init__(self, *yanitlar):
        self.yanitlar = list(yanitlar)
        self.urller = []

    def __call__(self, url, timeout=None):
        self.urller.append(url)
        y = self.yanitlar.pop(0) if self.yanitlar else {"items": []}
        if isinstance(y, Exception):
            raise y
        return Yanit(y)


class ApiTest(unittest.TestCase):
    def test_butce_asilinca_kotabitti(self):
        op = SahteOpener({"items": [{"id": {"videoId": "a"}}]})
        yt = YouTube("K", butce=150, opener=op)
        self.assertEqual(yt.ara("TR", "", "2026-11-06T00:00:00Z"), ["a"])
        with self.assertRaises(KotaBitti):
            yt.ara("TR", "10", "2026-11-06T00:00:00Z")
        self.assertEqual(yt.harcanan, 100)
        self.assertEqual(len(op.urller), 1)

    def test_ara_parametreleri(self):
        op = SahteOpener()
        YouTube("K", opener=op).ara("TR", "10", "2026-11-06T00:00:00Z")
        u = op.urller[0]
        for p in ("regionCode=TR", "videoCategoryId=10", "order=viewCount", "type=video", "maxResults=50"):
            self.assertIn(p, u)
        op = SahteOpener()
        YouTube("K", opener=op).ara("TR", "", "2026-11-06T00:00:00Z")
        self.assertNotIn("videoCategoryId", op.urller[0])

    def test_403_quota(self):
        op = SahteOpener(http_hata(403, b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}'))
        with self.assertRaises(KotaBitti):
            YouTube("K", opener=op).ara("TR", "", "x")

    def test_5xx_tekrar_sonra_atla(self):
        op = SahteOpener(http_hata(500), http_hata(503))
        self.assertEqual(YouTube("K", opener=op).ara("TR", "", "x"), [])
        self.assertEqual(len(op.urller), 2)

    def test_zaman_asimi_tekrar(self):
        op = SahteOpener(TimeoutError(), {"items": [{"id": {"videoId": "b"}}]})
        self.assertEqual(YouTube("K", opener=op).ara("TR", "", "x"), ["b"])

    def test_videolar_50lik_parca(self):
        op = SahteOpener()
        yt = YouTube("K", opener=op)
        yt.videolar([f"v{i}" for i in range(120)])
        self.assertEqual(len(op.urller), 3)
        self.assertEqual(yt.harcanan, 3)

    def test_son_yuklemeler(self):
        op = SahteOpener({"items": [{"contentDetails": {"videoId": "x"}}, {"contentDetails": {"videoId": "y"}}]})
        self.assertEqual(YouTube("K", opener=op).son_yuklemeler("UU1", 20), ["x", "y"])
        self.assertIn("maxResults=20", op.urller[0])

    def test_anahtar_hata_mesajinda_yok(self):
        op = SahteOpener(http_hata(403, b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}'))
        try:
            YouTube("GIZLI123", opener=op).ara("TR", "", "x")
        except KotaBitti as e:
            self.assertNotIn("GIZLI123", str(e))
            self.assertNotIn("GIZLI123", repr(e))


if __name__ == "__main__":
    unittest.main()

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
        self.assertIn("relevanceLanguage=tr", op.urller[0])
        op = SahteOpener()
        YouTube("K", opener=op).ara("US", "", "x")
        self.assertIn("relevanceLanguage=en", op.urller[0])

    def test_videolar_canli_bilgisi_ister(self):
        op = SahteOpener()
        YouTube("K", opener=op).videolar(["a"])
        self.assertIn("liveStreamingDetails", op.urller[0])

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

    def test_ara_konu_ile(self):
        op = SahteOpener({"items": [{"id": {"videoId": "x"}}]})
        self.assertEqual(YouTube("K", opener=op).ara("US", "", "2026-11-02T00:00:00Z", q="ai animation"), ["x"])
        self.assertIn("q=ai+animation", op.urller[0])
        self.assertNotIn("videoCategoryId", op.urller[0])

    def test_son_yuklemeler_tarih_sinirli_sayfali(self):
        def oge(i, t):
            return {"contentDetails": {"videoId": i, "videoPublishedAt": t}}
        op = SahteOpener(
            {"items": [oge("a", "2026-11-08T10:00:00Z"), oge("b", "2026-11-01T10:00:00Z")], "nextPageToken": "P2"},
            {"items": [oge("c", "2026-10-30T10:00:00Z"), oge("d", "2026-10-29T10:00:00Z")], "nextPageToken": "P3"},
        )
        yt = YouTube("K", opener=op)
        ids = yt.son_yuklemeler("UU1", 2, once="2026-11-05T00:00:00Z", sayfa=3)
        self.assertEqual(ids, ["b", "c"])
        self.assertEqual(len(op.urller), 2)
        self.assertIn("maxResults=50", op.urller[0])
        self.assertIn("pageToken=P2", op.urller[1])
        self.assertEqual(yt.harcanan, 2)

    def test_anahtar_hata_mesajinda_yok(self):
        op = SahteOpener(http_hata(403, b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}'))
        try:
            YouTube("GIZLI123", opener=op).ara("TR", "", "x")
        except KotaBitti as e:
            self.assertNotIn("GIZLI123", str(e))
            self.assertNotIn("GIZLI123", repr(e))


if __name__ == "__main__":
    unittest.main()

"""Kota sayaçlı, yalnızca standart kütüphane kullanan YouTube Data API v3 istemcisi."""
import json
import urllib.error
import urllib.parse
import urllib.request

from radar.parse import channel_from_api, video_from_api

TABAN = "https://www.googleapis.com/youtube/v3/"
PARCA = 50


class KotaBitti(Exception):
    pass


class YouTube:
    def __init__(self, key: str, butce: int = 9500, opener=urllib.request.urlopen):
        self._key = key
        self.butce = butce
        self.harcanan = 0
        self._opener = opener

    def _get(self, uc: str, params: dict, maliyet: int) -> dict | None:
        if self.harcanan + maliyet > self.butce:
            raise KotaBitti("günlük bütçe doldu")
        self.harcanan += maliyet
        url = TABAN + uc + "?" + urllib.parse.urlencode({**params, "key": self._key})
        for _ in range(2):
            try:
                with self._opener(url, timeout=30) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                govde = e.read() or b""
                if e.code == 403 and b"quotaExceeded" in govde:
                    raise KotaBitti("YouTube kotası doldu") from None
                if e.code < 500:
                    return None
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                pass
        return None

    def ara(self, region: str, kategori: str, after_iso: str) -> list[str]:
        p = {"part": "id", "type": "video", "order": "viewCount", "maxResults": 50,
             "publishedAfter": after_iso, "regionCode": region}
        if kategori:
            p["videoCategoryId"] = kategori
        d = self._get("search", p, 100) or {}
        return [i["id"]["videoId"] for i in d.get("items", []) if i.get("id", {}).get("videoId")]

    def trend(self, region: str) -> list[dict]:
        d = self._get("videos", {"part": "snippet,statistics,contentDetails", "chart": "mostPopular",
                                 "regionCode": region, "maxResults": 50}, 1) or {}
        return [v for v in map(video_from_api, d.get("items", [])) if v]

    def videolar(self, ids: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(ids), PARCA):
            d = self._get("videos", {"part": "snippet,statistics,contentDetails",
                                     "id": ",".join(ids[i:i + PARCA])}, 1) or {}
            out += [v for v in map(video_from_api, d.get("items", [])) if v]
        return out

    def kanallar(self, ids: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(ids), PARCA):
            d = self._get("channels", {"part": "snippet,statistics,contentDetails",
                                       "id": ",".join(ids[i:i + PARCA])}, 1) or {}
            out += [channel_from_api(c) for c in d.get("items", [])]
        return out

    def son_yuklemeler(self, uploads_id: str, adet: int = 20) -> list[str]:
        d = self._get("playlistItems", {"part": "contentDetails", "playlistId": uploads_id,
                                        "maxResults": adet}, 1) or {}
        return [i["contentDetails"]["videoId"] for i in d.get("items", [])
                if i.get("contentDetails", {}).get("videoId")]

"""Testler için ağsız sahte YouTube istemcisi (radar.api.YouTube ile aynı metotlar)."""
from radar.api import KotaBitti


class FakeYT:
    def __init__(self, videos=None, channels=None, uploads=None, search=None, trends=None, patla=None):
        self.videos = videos or {}        # id -> video dict
        self.channels = channels or {}    # id -> channel dict
        self.uploads = uploads or {}      # playlist id -> [video id, en yeniden]
        self.search = search or {}        # region -> [video id]
        self.trends = trends or {}        # region -> [video id]
        self.patla = patla                # bu numaralı çağrıda KotaBitti
        self.cagri = 0
        self.harcanan = 0
        self.istenen_kanallar = []

    def _say(self, m):
        self.cagri += 1
        if self.patla is not None and self.cagri >= self.patla:
            raise KotaBitti("sahte kota")
        self.harcanan += m

    def ara(self, region, kategori, after_iso):
        self._say(100)
        return list(self.search.get(region, []))

    def trend(self, region):
        self._say(1)
        return [dict(self.videos[i]) for i in self.trends.get(region, [])]

    def videolar(self, ids):
        if ids:
            self._say(1)
        return [dict(self.videos[i]) for i in ids if i in self.videos]

    def kanallar(self, ids):
        if ids:
            self._say(1)
        self.istenen_kanallar += ids
        return [dict(self.channels[i]) for i in ids if i in self.channels]

    def son_yuklemeler(self, uploads_id, adet=20, once=None, sayfa=1):
        tum = list(self.uploads.get(uploads_id, []))
        if once is None:
            self._say(1)
            return tum[:adet]
        ids = []
        for n in range(max(1, sayfa)):
            parca = tum[n * 50:(n + 1) * 50]
            self._say(1)
            ids += [i for i in parca if self.videos.get(i, {}).get("published", "") < once]
            if len(ids) >= adet or (n + 1) * 50 >= len(tum):
                break
        return ids[:adet]

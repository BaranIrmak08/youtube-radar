import unittest

from radar.parse import channel_from_api, iso_duration_to_seconds, video_from_api


def video_item(**over):
    item = {
        "id": "v1",
        "snippet": {
            "channelId": "c1",
            "channelTitle": "Kanal",
            "title": "Başlık",
            "publishedAt": "2026-11-07T10:00:00Z",
            "categoryId": "27",
            "thumbnails": {"medium": {"url": "http://m"}, "default": {"url": "http://d"}},
        },
        "statistics": {"viewCount": "12345"},
        "contentDetails": {"duration": "PT59S"},
    }
    for k, v in over.items():
        item[k] = v
    return item


class ParseTest(unittest.TestCase):
    def test_sure(self):
        self.assertEqual(iso_duration_to_seconds("PT1M5S"), 65)
        self.assertEqual(iso_duration_to_seconds("PT2H"), 7200)
        self.assertEqual(iso_duration_to_seconds("P0D"), 0)
        self.assertEqual(iso_duration_to_seconds("P1DT1S"), 86401)

    def test_short_siniri(self):
        v = video_from_api(video_item(contentDetails={"duration": "PT3M"}))
        self.assertTrue(v["is_short"])
        v = video_from_api(video_item(contentDetails={"duration": "PT3M1S"}))
        self.assertFalse(v["is_short"])

    def test_alanlar(self):
        v = video_from_api(video_item())
        self.assertEqual(v["id"], "v1")
        self.assertEqual(v["channel_id"], "c1")
        self.assertEqual(v["views"], 12345)
        self.assertEqual(v["thumb"], "http://m")
        self.assertEqual(v["category_id"], "27")

    def test_viewcount_yoksa_none(self):
        self.assertIsNone(video_from_api(video_item(statistics={})))
        self.assertIsNone(video_from_api(video_item(statistics=None)))

    def test_lang(self):
        item = video_item()
        item["snippet"]["defaultAudioLanguage"] = "tr-TR"
        self.assertEqual(video_from_api(item)["lang"], "tr")
        self.assertIsNone(video_from_api(video_item())["lang"])

    def test_begeni_ve_canli(self):
        v = video_from_api(video_item(statistics={"viewCount": "1000", "likeCount": "40"}))
        self.assertEqual(v["likes"], 40)
        self.assertFalse(v["is_live"])
        self.assertIsNone(video_from_api(video_item())["likes"])
        self.assertTrue(video_from_api(video_item(liveStreamingDetails={"actualStartTime": "x"}))["is_live"])
        item = video_item()
        item["snippet"]["liveBroadcastContent"] = "live"
        self.assertTrue(video_from_api(item)["is_live"])

    def test_und_dil_none(self):
        item = video_item()
        item["snippet"]["defaultAudioLanguage"] = "und"
        self.assertIsNone(video_from_api(item)["lang"])

    def test_gizli_abone(self):
        ch = channel_from_api({
            "id": "c1",
            "snippet": {"title": "K", "publishedAt": "2020-01-01T00:00:00Z"},
            "statistics": {"hiddenSubscriberCount": True, "videoCount": "7"},
            "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}},
        })
        self.assertIsNone(ch["subs"])
        self.assertEqual(ch["video_count"], 7)
        self.assertEqual(ch["uploads"], "UU1")
        self.assertIsNone(ch["country"])


if __name__ == "__main__":
    unittest.main()

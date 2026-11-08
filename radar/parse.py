"""YouTube API yanıtlarını sade sözlüklere çevirir."""
import re

SHORT_MAX_SN = 180

_SURE = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def iso_duration_to_seconds(s: str) -> int:
    m = _SURE.match(s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def video_from_api(item: dict) -> dict | None:
    stats = item.get("statistics") or {}
    views = _int(stats.get("viewCount"))
    if views is None:
        return None
    sn = item.get("snippet") or {}
    thumbs = sn.get("thumbnails") or {}
    thumb = (thumbs.get("medium") or thumbs.get("default") or {}).get("url")
    sure = iso_duration_to_seconds((item.get("contentDetails") or {}).get("duration", ""))
    lang = sn.get("defaultAudioLanguage") or sn.get("defaultLanguage")
    return {
        "id": item.get("id"),
        "channel_id": sn.get("channelId"),
        "channel_title": sn.get("channelTitle", ""),
        "title": sn.get("title", ""),
        "published": sn.get("publishedAt"),
        "views": views,
        "duration_s": sure,
        "is_short": 0 < sure <= SHORT_MAX_SN,
        "thumb": thumb,
        "category_id": sn.get("categoryId"),
        "lang": lang.split("-")[0].lower() if lang else None,
    }


def channel_from_api(item: dict) -> dict:
    sn = item.get("snippet") or {}
    st = item.get("statistics") or {}
    rel = (item.get("contentDetails") or {}).get("relatedPlaylists") or {}
    return {
        "id": item.get("id"),
        "title": sn.get("title", ""),
        "country": sn.get("country"),
        "published": sn.get("publishedAt"),
        "video_count": _int(st.get("videoCount")) or 0,
        "subs": None if st.get("hiddenSubscriberCount") else _int(st.get("subscriberCount")),
        "uploads": rel.get("uploads"),
    }

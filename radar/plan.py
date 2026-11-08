"""Her gün hangi ülke + kategori çiftlerinin aranacağı. Şimdilik yalnızca Türkçe ve İngilizce."""

# ülke -> arama dili (search.list relevanceLanguage)
DIL = {"TR": "tr", "US": "en", "GB": "en", "CA": "en", "AU": "en"}
SABIT = list(DIL)
KATEGORILER = ["", "1", "2", "10", "15", "17", "19", "20", "22", "23",
               "24", "25", "26", "27", "28"]


def _kategoriler(gun_no: int, adet: int) -> list[str]:
    bas = (gun_no * adet) % len(KATEGORILER)
    return [KATEGORILER[(bas + j) % len(KATEGORILER)] for j in range(adet)]


def gunun_ulkeleri(gun_no: int) -> list[str]:
    return list(SABIT)


def gunun_aramalari(gun_no: int, adet: int = 60) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i, r in enumerate(SABIT):
        n = adet // len(SABIT) + (1 if i < adet % len(SABIT) else 0)
        out += [(r, k) for k in _kategoriler(gun_no, n)]
    return out

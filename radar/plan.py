"""Her gün hangi ülke + kategori çiftlerinin aranacağı."""

SABIT = ["TR", "US", "GB", "IN"]
DONUSUMLU = ["DE", "BR", "ES", "MX", "FR", "JP", "KR", "RU", "ID", "IT",
             "PH", "VN", "SA", "EG", "AR", "PL", "NL", "CA", "AU", "PK"]
KATEGORILER = ["", "1", "2", "10", "15", "17", "19", "20", "22", "23",
               "24", "25", "26", "27", "28"]
GUNLUK_DONUSUMLU = 3


def _kategoriler(gun_no: int, adet: int) -> list[str]:
    bas = (gun_no * adet) % len(KATEGORILER)
    return [KATEGORILER[(bas + j) % len(KATEGORILER)] for j in range(adet)]


def gunun_ulkeleri(gun_no: int) -> list[str]:
    don = [DONUSUMLU[(gun_no * GUNLUK_DONUSUMLU + i) % len(DONUSUMLU)]
           for i in range(GUNLUK_DONUSUMLU)]
    return SABIT + don


def gunun_aramalari(gun_no: int, adet: int = 60) -> list[tuple[str, str]]:
    yarim = adet // 2
    out: list[tuple[str, str]] = []
    # sabit yarı: 30 arama 4 ülkeye 8,8,7,7 dağılır
    for i, r in enumerate(SABIT):
        n = yarim // len(SABIT) + (1 if i < yarim % len(SABIT) else 0)
        out += [(r, k) for k in _kategoriler(gun_no, n)]
    # dönüşümlü yarı: günün 3 ülkesine 10'ar arama
    don = gunun_ulkeleri(gun_no)[len(SABIT):]
    kalan = adet - len(out)
    for i, r in enumerate(don):
        n = kalan // len(don) + (1 if i < kalan % len(don) else 0)
        out += [(r, k) for k in _kategoriler(gun_no, n)]
    return out

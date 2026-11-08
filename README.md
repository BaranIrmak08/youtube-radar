# YouTube Radar

Son günlerde kendi kanalının normalinin çok üstünde izlenen YouTube videolarını ve patlayan yeni kanalları her gün bulan kişisel araç. GitHub Actions her sabah 06:00'da (TSİ) tarar, sonuçlar GitHub Pages'teki sitede görünür. Tasarım: `docs/2026-11-08-youtube-radar-tasarim.md`.

Testler: `python -m unittest discover -s tests -v`
Yerel tarama: `YT_API_KEY` ortam değişkeni ayarlıyken `python -m radar.main`

# YouTube Radar — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Her gün YouTube'u örnekleyip kanal normalinin çok üstünde izlenen videoları ve patlayan yeni kanalları bulan, GitHub Pages'te yayınlanan bedava kişisel araç.

**Architecture:** Python tarayıcı (`radar/`) GitHub Actions'ta günde bir kez çalışır. YouTube Data API v3'ten veri çeker, `data/*.json` dosyalarını günceller ve `site/liste.json` dosyasını üretir. Statik site (`site/`) bu dosyayı okur. Actions, veriyi depoya commit eder ve `site/` klasörünü Pages'e yayınlar.

**Tech Stack:** Python 3.12 (Actions) / 3.14 (yerel), yalnızca standart kütüphane (`urllib`, `json`, `statistics`, `unittest`). Site: düz HTML, CSS ve JS. Paket kurulumu yok.

**Spec:** `docs/2026-11-08-youtube-radar-tasarim.md`

## Global Constraints

- Ücretsiz: yalnızca YouTube Data API ücretsiz kotası, GitHub Actions ve Pages kullanılır.
- Günlük kota tavanı **9.500 birim** (10.000 sınırının altında güvenlik payı). Arama bütçesi **6.000 birim** (60 arama).
- Maliyetler: `search.list` = 100, `videos.list`, `channels.list`, `playlistItems.list` = 1.
- Short tanımı: süre **≤ 180 sn**.
- Listeleme alt sınırı: **5.000 izlenme**.
- Normal = kanalın son **20** videosunun izlenme **ortancası** (videonun kendisi hariç).
- Yeni kanal: kanal yaşı **< 30 gün** ya da **< 5 video**.
- Listede kalma süresi **7 gün**. Arama penceresi **son 48 saat**.
- Tarama saati: cron `0 3 * * *` (TR 06:00).
- Sabit ülkeler: `TR, US, GB, IN`. Dönüşümlü ülkeler: `DE, BR, ES, MX, FR, JP, KR, RU, ID, IT, PH, VN, SA, EG, AR, PL, NL, CA, AU, PK`.
- Kategoriler: `"" (hepsi), 1, 2, 10, 15, 17, 19, 20, 22, 23, 24, 25, 26, 27, 28`.
- API anahtarı yalnızca `YT_API_KEY` ortam değişkeninden okunur. Depoya, loga ya da sohbete hiçbir zaman yazılmaz.
- Arayüz metinleri Türkçe.
- Site, başlık ve kanal adlarını **yalnızca `textContent` ile** yazar. `innerHTML` içine veri konmaz.

## Review Focus

1. **Kota tarama ortasında biterse** (403 `quotaExceeded` ya da bütçe sayacı dolarsa) o ana kadar toplanan veri yine kaydedilir ve `liste.json` yine üretilir. → Görev 4, `test_kota_bitince_kismi_kayit`.
2. **İzlenme sayısı gizli ya da eksik videolar** (`statistics.viewCount` yok, canlı yayın veya prömiyer, `duration` "P0D") çökme yerine atlanır. → Görev 1, `test_viewcount_yoksa_none`.
3. **Normali 0 olan ya da 5'ten az videosu olan kanal** sıfıra bölme hatasına yol açmaz, "yeni kanal" sayılır. → Görev 2, `test_normal_sifir_ise_none`.
4. **Geçici API hatası (5xx, zaman aşımı)** tüm taramayı düşürmez. O çağrı bir kez tekrar denenir, yine olmazsa atlanır. → Görev 3, `test_5xx_tekrar_sonra_atla`.
5. **Emoji, Arapça ya da `<script>` içeren başlıklar** sayfada düz metin olarak görünür. → Görev 5, örnek veride `<img src=x onerror=alert(1)>` başlığıyla elle doğrulama.

---

### Task 1: Depo iskeleti ve API verisini çözümleme

**Files:**
- Create: `radar/__init__.py`, `radar/parse.py`, `tests/test_parse.py`, `.gitignore`, `README.md`

**Interfaces:**
- Produces:
  - `iso_duration_to_seconds(s: str) -> int`
  - `video_from_api(item: dict) -> dict | None`: anahtarlar `id, channel_id, channel_title, title, published (ISO str), views (int), duration_s, is_short (bool), thumb (url), category_id, lang (str|None)`. `viewCount` yoksa `None` döner.
  - `channel_from_api(item: dict) -> dict`: anahtarlar `id, title, country (str|None), published, video_count (int), subs (int|None, gizliyse None), uploads (playlist id)`.

- [ ] **Step 1:** `git init`. `.gitignore` içine `__pycache__/`, `.superpowers/` ve `.env` yaz. README'ye tek paragraf ekle: ne olduğu, `python -m unittest discover -s tests -v`.
- [ ] **Step 2: Failing testleri yaz** (`tests/test_parse.py`)
  - `test_sure`: `"PT1M5S"` → 65, `"PT2H"` → 7200, `"P0D"` → 0, `"P1DT1S"` → 86401
  - `test_short_siniri`: 180 sn → `is_short True`, 181 sn → `False`
  - `test_viewcount_yoksa_none`: `statistics` içinde `viewCount` yoksa `video_from_api` → `None`
  - `test_lang`: `defaultAudioLanguage="tr-TR"` → `lang == "tr"`. Alan yoksa → `None`
  - `test_gizli_abone`: `hiddenSubscriberCount=True` → `subs is None`
- [ ] **Step 3:** `python -m unittest tests.test_parse -v` → FAIL (import hatası)
- [ ] **Step 4:** `radar/parse.py` dosyasını yaz. Küçük resim: `thumbnails.medium.url`, yoksa `default`.
- [ ] **Step 5:** Test → PASS
- [ ] **Step 6:** Commit: `feat: depo iskeleti ve API çözümleme`

### Task 2: Skor ve arama planı

**Files:**
- Create: `radar/score.py`, `radar/plan.py`, `tests/test_score.py`, `tests/test_plan.py`

**Interfaces:**
- Produces (`score.py`):
  - `normal(views: list[int]) -> float | None`: 5'ten az değer varsa ya da ortanca 0 ise `None`, aksi hâlde son 20 değerin ortancası.
  - `yeni_kanal_mi(channel: dict, now: datetime) -> bool`
  - `yas_carpani(age_days: float) -> float` = `min(1.0, sqrt(max(age_days, 0.25) / 7))`. Sabit `YAS_REFERANS_GUN = 7` olarak tanımlanır, ilk verilerle ayarlanacak.
  - `skorla(video: dict, normal_deger: float, now: datetime) -> dict`: `{"kat": views/normal, "duzeltilmis": kat / yas_carpani(yaş)}`
- Produces (`plan.py`):
  - `SABIT, DONUSUMLU, KATEGORILER` sabitleri (Global Constraints'teki değerler)
  - `gunun_ulkeleri(gun_no: int) -> list[str]`: `SABIT` + o günün 3 dönüşümlü ülkesi `DONUSUMLU[(gun_no*3 + i) % len(DONUSUMLU)]`, i = 0, 1, 2 (trend listesi de bunları kullanır)
  - `gunun_aramalari(gun_no: int, adet: int = 60) -> list[tuple[str, str]]`: ilk yarı (30) için 4 sabit ülkenin her biri 7-8 kategori alır. İkinci yarı (30) için o günün 3 dönüşümlü ülkesinin her biri 10 kategori alır. Kategori seçimi `gun_no` ile kayar, böylece her ülke birkaç günde tüm kategorileri görür. Aynı gün aynı çift iki kez çıkmaz.

- [ ] **Step 1: Failing testleri yaz**
  - `test_normal_ortanca`: `[1000]*19 + [1_000_000]` → 1000
  - `test_normal_sifir_ise_none`: `[0]*10` → None. `[5000]*4` → None
  - `test_yeni_kanal`: 10 günlük kanal → True. 200 günlük ve 3 videolu kanal → True. 200 günlük ve 50 videolu kanal → False
  - `test_yas_carpani`: 7 gün → 1.0, 30 gün → 1.0, 0 gün → `sqrt(0.25/7)`
  - `test_skor_ornek`: 350_000 izlenme, normal 10_000, 7 günlük → kat 35.0
  - `test_plan_adet_ve_tekrarsiz`: `len == 60` ve `len(set) == 60`
  - `test_plan_yarisi_sabit`: tam 30 çiftin ülkesi `SABIT` içinde ve 4 sabit ülkenin her biri en az 7 kez geçiyor
  - `test_plan_doner`: `gun_no=0` ile `gun_no=1` dönüşümlü kısmı farklı
- [ ] **Step 2:** Testler → FAIL
- [ ] **Step 3:** İki modülü yaz.
- [ ] **Step 4:** Testler → PASS
- [ ] **Step 5:** Commit: `feat: kat skoru ve günlük arama planı`

### Task 3: Kota sayaçlı YouTube istemcisi

**Files:**
- Create: `radar/api.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: `video_from_api`, `channel_from_api` (Task 1)
- Produces:
  - `class KotaBitti(Exception)`
  - `class YouTube(key: str, butce: int = 9500, opener=urllib.request.urlopen)`, `.harcanan: int`
    - `ara(region: str, kategori: str, after_iso: str) -> list[str]`: video id'leri döner. `type=video, order=viewCount, maxResults=50, publishedAfter, regionCode`, kategori boş değilse `videoCategoryId`. Maliyet 100.
    - `trend(region: str) -> list[dict]`: `videos.list chart=mostPopular maxResults=50`, sonuçlar çözümlenmiş. Maliyet 1.
    - `videolar(ids: list[str]) -> list[dict]`: 50'lik parçalara bölünür, `part=snippet,statistics,contentDetails`, her parça 1 birim.
    - `kanallar(ids: list[str]) -> list[dict]`: 50'lik parçalar, `part=snippet,statistics,contentDetails`.
    - `son_yuklemeler(uploads_id: str, adet: int = 20) -> list[str]`: `playlistItems.list`, 1 birim.
  - Çağrıdan **önce** `harcanan + maliyet > butce` ise `KotaBitti` fırlatılır. HTTP 403 ve gövdede `quotaExceeded` varsa yine `KotaBitti` fırlatılır. 5xx ya da zaman aşımında bir kez tekrar denenir, yine olmazsa o çağrı boş sonuç döner. Hata mesajlarında anahtar asla görünmez (URL loglanmaz).

- [ ] **Step 1: Failing testleri yaz** (sahte `opener` ile, ağ yok)
  - `test_butce_asilinca_kotabitti`: `butce=150` iken iki `ara` çağrısı → ikincisi `KotaBitti`, `harcanan == 100`
  - `test_403_quota`: sahte 403 ve `quotaExceeded` gövdesi → `KotaBitti`
  - `test_5xx_tekrar_sonra_atla`: iki kez 500 → `ara` boş liste döner, opener 2 kez çağrılmış olur
  - `test_videolar_50lik_parca`: 120 id → 3 istek, `harcanan == 3`
  - `test_anahtar_hata_mesajinda_yok`: hata metninde `"GIZLI123"` geçmez
- [ ] **Step 2:** FAIL → **Step 3:** `api.py` yaz → **Step 4:** PASS
- [ ] **Step 5:** Commit: `feat: kota sayaçlı YouTube istemcisi`

### Task 4: Veri deposu ve günlük tarama akışı

**Files:**
- Create: `radar/store.py`, `radar/main.py`, `tests/test_main.py`, `tests/fake_yt.py`

**Interfaces:**
- Consumes: Task 1–3'ün tümü
- Produces:
  - `data/videolar.json`: `{video_id: {...video_from_api alanları, "bulundu": region, "gecmis": [[iso_zaman, views], ...]}}`. Yalnızca 7 günden yeni videolar tutulur.
  - `data/kanallar.json`: `{channel_id: {...channel_from_api alanları, "normal_views": {video_id: views}, "normal_tarih": iso, "kontrol": iso}}`
  - `site/liste.json`: `{"guncellendi": iso, "harcanan": int, "videolar": [...], "yeni_kanallar": [...]}`
    - Video satırı: `id, title, channel_id, channel_title, views, normal, kat, duzeltilmis, published, is_short, thumb, category_id, ulke`
    - Yeni kanal satırı: `channel_id, channel_title, kanal_yasi_gun, video_sayisi, subs, en_iyi` (en çok izlenen video satırı, `kat` yok)
    - `ulke` = `lang`, yoksa kanalın `country`, o da yoksa `bulundu`
  - `store.yukle(path) -> dict`, `store.kaydet(path, obj)`: UTF-8, `ensure_ascii=False`, atomik yazım (geçici dosya + `os.replace`)
  - `main.calistir(yt, veri_dir: Path, site_dir: Path, now: datetime) -> dict`: `liste.json` içeriğini döner
  - `python -m radar.main`: `YT_API_KEY` yoksa açık bir Türkçe hata verip kod 1 ile çıkar

**Akış (`calistir`)**, `KotaBitti` herhangi bir adımda yakalanır, kalan adımlar atlanır, **kayıt ve liste her durumda yapılır**:
1. `gunun_ulkeleri` için `trend`, `gunun_aramalari` için `ara` (yalnızca `after = now - 48 saat`). `gun_no = now.toordinal()`
2. Havuzdan, `kontrol` tarihi en eski olan en fazla 300 kanal için `son_yuklemeler(adet=5)` çağrılır ve yeni id'ler toplanır.
3. Yeni id'ler ve hâlâ 7 günden yeni kayıtlı videolar için `videolar(...)` çağrılır. Her videonun `gecmis` listesine `[now, views]` eklenir.
4. 7 günden eski videolar `videolar.json` dosyasından silinir.
5. Videoları olan kanallardan havuzda olmayanlar ya da `normal_tarih` değeri 3 günden eski olanlar için önce `kanallar`, sonra `son_yuklemeler(20)` ve `videolar` çağrılır, `normal_views` güncellenir.
6. Liste kurulur: video için `normal(views_listesi_kendisi_haric)` hesaplanır. `None` ya da `yeni_kanal_mi` ise video yeni kanallar sekmesine gider, değilse `skorla` ile değerlendirilir. 5.000 izlenmenin altındakiler listelenmez. Videolar `duzeltilmis` değerine göre azalan, yeni kanallar `en_iyi.views` değerine göre azalan sırada dizilir.

- [ ] **Step 1:** `tests/fake_yt.py`: `YouTube` ile aynı metotlara sahip, sabit veri döndüren ve isteğe bağlı olarak N. çağrıda `KotaBitti` fırlatan sahte istemci.
- [ ] **Step 2: Failing testleri yaz**
  - `test_patlayan_video_ust_sirada`: normali 10k olan kanalın 350k videosu, 3x'lik bir videonun üstünde. `kat == 35.0`
  - `test_yeni_kanal_sekmesi`: 2 günlük, 1 videolu ve 1M izlenmeli kanal `yeni_kanallar` listesinde, `videolar` listesinde değil
  - `test_alt_sinir`: 4.999 izlenmeli video hiçbir listede yok
  - `test_yedi_gun_temizlik`: 8 günlük video `videolar.json` dosyasından silinmiş
  - `test_gecmis_birikir`: iki çalıştırmadan sonra `gecmis` uzunluğu 2
  - `test_kota_bitince_kismi_kayit`: 3. çağrıda `KotaBitti` → `liste.json` ve `videolar.json` yine yazılmış, hata dışarı sızmamış
  - `test_anahtar_yoksa_cikis`: ortamda `YT_API_KEY` yoksa çıkış kodu 1
- [ ] **Step 3:** FAIL → **Step 4:** `store.py` ve `main.py` yaz → **Step 5:** PASS
- [ ] **Step 6:** Commit: `feat: günlük tarama akışı ve veri dosyaları`

### Task 5: Site

**Files:**
- Create: `site/index.html`, `site/app.js`, `site/style.css`, `site/ornek-liste.json`

**Interfaces:**
- Consumes: `site/liste.json` şeması (Task 4). Dosya yoksa `ornek-liste.json` yüklenir ve sayfada "örnek veri" uyarısı gösterilir.

**Davranış:**
- Sekmeler: "Patlayan videolar" / "Yeni kanallar".
- Görünüm düğmesi: Tablo / Kart. Seçim `localStorage` anahtarı `radar.gorunum` ile hatırlanır (try/catch içinde, kayıt yoksa varsayılan Tablo).
- Filtreler:
  - Zaman: 24 saat / **3 gün (varsayılan)** / 7 gün
  - Tür: Hepsi / Short / Uzun
  - Ülke-dil ve kategori açılır listeleri, veriden doldurulur
- Tablo sütunları: Kat · Video · Kanal · İzlenme · Normali · Yaş · Tür
- Kart: küçük resim, kat, "izlenme (normali X)", başlık, kanal · yaş · tür
- Sayılar `1,1M` / `350k` biçiminde, kat `35x` biçiminde gösterilir.
- Satıra ya da karta tıklayınca `https://www.youtube.com/watch?v=<id>` yeni sekmede açılır.
- Üstte "Son güncelleme: …" yazısı ve harcanan kota gösterilir.
- 375 px genişlikte yatay kaydırma olmaz. Tablo dar ekranda kendi kutusunda kaydırılır. Açık ve koyu tema desteklenir.

- [ ] **Step 1:** `ornek-liste.json` dosyasını Task 4 şemasıyla yaz: 8 video, 3 yeni kanal. İçinde biri `<img src=x onerror=alert(1)>`, biri Arapça, biri emoji başlıklı video bulunsun.
- [ ] **Step 2:** Sayfayı yaz.
- [ ] **Step 3: Doğrula:** `python -m http.server 8765 --directory site` ile yerel sunucuyu aç, tarayıcı panelinde incele:
  - Varsayılan görünüm tablo, filtre 3 gün
  - Kart düğmesine basıldıktan sonra sayfa yenilenince yine kart görünümü
  - Zararlı başlık düz metin olarak görünüyor, uyarı penceresi çıkmıyor
  - 375 px genişlikte yatay sayfa kaydırması yok
- [ ] **Step 4:** Commit: `feat: radar sitesi (tablo/kart, filtreler)`

### Task 6: GitHub'a yayın, otomatik tarama ve ilk gerçek çalıştırma

**Files:**
- Create: `.github/workflows/tara.yml`

**Workflow:**
- Tetikleyiciler: `schedule: cron "0 3 * * *"` ve `workflow_dispatch`.
- İzinler: `contents: write, pages: write, id-token: write`.
- Adımlar:
  1. Checkout
  2. `actions/setup-python` (3.12)
  3. `python -m unittest discover -s tests`
  4. `python -m radar.main` (`env: YT_API_KEY: ${{ secrets.YT_API_KEY }}`)
  5. `data/` ve `site/liste.json` değiştiyse commit atılır, mesaj `veri: <tarih>`, kullanıcı `github-actions[bot]`. Ardından push.
  6. `actions/upload-pages-artifact` (`path: site`) ve `actions/deploy-pages`.
- `concurrency: tara` kullanılır, iki çalıştırma üst üste binmez.

- [ ] **Step 1:** Workflow dosyasını yaz ve commit et.
- [ ] **Step 2 (kullanıcı onayıyla):** `gh repo create BaranIrmak08/youtube-radar --public --source . --push`. Depo herkese açık olarak oluşturulur, onay alınmadan çalıştırılmaz.
- [ ] **Step 3 (kullanıcı onayıyla):** Pages kaynağını "GitHub Actions" olarak ayarla: `gh api -X POST repos/BaranIrmak08/youtube-radar/pages -f build_type=workflow`.
- [ ] **Step 4 (kullanıcı yapar, ekran ekran rehberlik edilir):** Google Cloud'da proje aç, YouTube Data API v3'ü etkinleştir, API anahtarı oluştur. Anahtarı yalnızca YouTube Data API ile sınırla. Ardından GitHub'da depo → Settings → Secrets and variables → Actions → `YT_API_KEY` alanına yapıştır.
- [ ] **Step 5:** `gh workflow run tara.yml`, ardından `gh run watch`. Beklenen sonuç: testler geçer, tarama biter, `liste.json` commit edilir, Pages yayınlanır.
- [ ] **Step 6: Doğrula:** `https://baranirmak08.github.io/youtube-radar/` adresi açılıyor, gerçek veri görünüyor, "Son güncelleme" bugünü gösteriyor, harcanan kota ≤ 9.500.
- [ ] **Step 7: Ayar turu:** İlk 15 sonucu kullanıcıyla birlikte incele. Liste gerekirse `yas_carpani` ya da alt sınır değiştirilir (değişiklik test güncellemesiyle birlikte commit edilir). Kullanıcı onay verince proje bitmiş sayılır.

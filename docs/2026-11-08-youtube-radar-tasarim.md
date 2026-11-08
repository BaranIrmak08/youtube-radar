# YouTube Radar — Tasarım

Tarih: 8 Kasım 2026 · Durum: onay bekliyor

## 1. Amaç ve neden

Son birkaç günde **kendi kanalının normalinin çok üstünde** izlenen YouTube videolarını ve hızla patlayan yeni kanalları her gün otomatik bulan, kişisel bir araç.

- Örnek: ortalaması 10k olan bir kanalın bir videosu 350k izlenirse bu 35x demektir. Ya da dün açılan bir kanalın ilk videosu 1 milyonu geçebilir.
- Neden: vidIQ'nun benzer özelliği ücretli. Kullanıcı kendi ücretsiz versiyonunu istiyor.
- Birincil kullanım: kullanıcının kendi kanalları (Erirken vb.) için içerik fikri toplamak.
- İleride: araç iyi çıkarsa halka açılabilir. İlk sürüm buna engel olmayacak şekilde kurulur, ama halka açma işi bu sürümde yapılmaz.

## 2. Hedefler, kapsam dışı olanlar, başarısızlık sayılacaklar

**Hedefler**
- Her dilden ve her türden video. Ayıklama ekrandaki filtrelerle yapılır.
- Bilgisayar kapalıyken de her gün çalışması.
- Telefondan da açılabilmesi.
- Tamamen ücretsiz olması.

**Kapsam dışı (ilk sürüm)**
- Kullanıcı hesabı, giriş, ödeme, kişisel listeler.
- Bildirim ve e-posta.
- "Tüm YouTube"u eksiksiz taramak. Bu teknik olarak mümkün değil (bkz. 3).

**Başarısızlık sayılacak durumlar (çalışsa bile)**
- Listenin müzik klibi, maç özeti gibi zaten büyük kanalların sıradan videolarıyla dolması.
- Listenin 300 izlenmeli gürültüyle dolması.
- Kotanın her gün yarıda tükenip taramanın eksik kalması.
- Para gerektirmesi.

## 3. Kısıtlar

- **YouTube Data API v3**, ücretsiz kotası günde 10.000 birim. Birim maliyetleri: `search.list` 100, `videos.list`, `channels.list` ve `playlistItems.list` 1 (en fazla 50 kayıt). Yani günde yaklaşık 60-80 arama yapılabilir. Gerisi ucuz detay çağrılarıdır.
- YouTube'da "yeni açılan kanallar" diye bir liste yok. Yeni kanallar yalnızca aramada patlayan videoları üzerinden bulunur. Bazıları kaçabilir, bu kabul edildi.
- Araç bir videoyu kendi taramasında görmeden bilemez. Dönüşümlü taranan ülkelerde patlamalar 1-2 gün geç yakalanabilir.
- API, bir videonun Short olup olmadığını söylemez. Süreye bakılır: 180 saniye ve altı Short sayılır.
- Abone sayısı gizli olabilir. Skor ona dayanmaz.
- Ücretsiz GitHub Pages için depo **herkese açık** olur. Bulunan veriler zaten herkese açık bilgiler. API anahtarı ise GitHub'ın gizli kasasında (Secrets) durur, depoda görünmez.
- Halka açma aşamasında YouTube API kullanım şartlarına (veri saklama süresi, denetim) uyum ayrıca ele alınacak.

## 4. Değerlendirilen yollar

| Yol | Ne | Artı | Eksi |
|---|---|---|---|
| **A (seçilen)** | GitHub Actions her gün tarar, sonucu veri dosyası olarak depoya yazar. GitHub Pages'teki statik site bu dosyayı okur. | Bedava, sunucu yok, bakımı az, kurulumu en kısa yol. | Depo herkese açık. Hesap ve giriş gibi özellikler için sonradan arka uç gerekir. |
| B | Cloudflare Workers, veritabanı ve zamanlanmış görev | Halka açmaya en hazır yapı | İlk sürüm için gereksiz karmaşık, ücretsiz çalışma süresi sınırları var |
| C | Ücretsiz sanal sunucu (Render, Oracle) | Esnek | Uyuyor, veriyi siliyor, kart istiyor |

**Seçim:** A. Kullanıcı bulutta ve bedava olmasını istedi, A ile başlamayı seçti. Halka açma aşamasında B'ye geçilir. Tarama ve skor mantığı aynı kalır, yalnızca veri katmanı değişir.

## 5. Kararlaştırılanlar

### Tarama düzeni
- Günde bir kez, Türkiye saatiyle 06:00'da çalışır (cron 03:00 UTC). *(Benim önerim, kabul edildi.)*
- Aramaların yarısı her gün sabit ülkelere gider: **Türkiye, ABD, İngiltere, Hindistan**. Diğer yarısı her gün sırayla değişen ülkelere gider (Almanya, Brezilya, İspanya, Meksika, Fransa, Japonya, Kore, Rusya, Endonezya vb.). Birkaç günde hepsi taranmış olur.
- Her arama bir "ülke + kategori" çiftidir: son 48 saatte yüklenmiş ve izlenmeye göre sıralanmış videolar istenir.
- Ek ve ucuz kaynak: ülke bazında "trend" listesi (`chart=mostPopular`).
- Bulunan her kanal **takip havuzuna** girer. Havuzdaki kanalların yeni videoları sonraki günlerde ucuza kontrol edilir, böylece araç günden güne güçlenir.

### Skor (kat)
- **Kanalın normali:** kanalın son 20 videosunun izlenmelerinin **ortanca** değeri (o video hariç). Ortanca, tek bir eski hit videonun normali şişirmesini önler.
- **Kat** = videonun izlenmesi ÷ kanalın normali.
- **Alt sınır:** 5.000 izlenmenin altındaki videolar listelenmez.
- **Yaş düzeltmesi:** 7 günlük bir video doğal olarak 1 günlükten fazla izlenmiştir. Bu yüzden sıralama, yaşa göre düzeltilmiş kata göre yapılır. Ekranda yine ham kat gösterilir.
- **Yeni kanal:** 30 günden yeni ya da 5'ten az videosu olan kanal. Bu kanalların normali olmadığı için "Yeni kanallar" sekmesinde **izlenmeye göre** sıralanır.

### Ekran
- İki sekme: **Patlayan videolar** ve **Yeni kanallar**.
- Varsayılan sıralama en yüksek kata göre (yeni kanallar sekmesinde izlenmeye göre).
- **İki görünüm** (Tablo / Kart), bir düğmeyle değiştirilir. Seçim tarayıcıda hatırlanır.
  - Tablo sütunları: kat, video başlığı, kanal, izlenme, kanalın normali, yaş, tür (Short/Uzun).
  - Kart: küçük resim, kat, izlenme (normali), başlık, kanal, yaş, tür.
- **Filtreler:** zaman (son 24 saat / **3 gün, varsayılan** / 7 gün), Short / Uzun / hepsi, ülke-dil, kategori.
- Ülke-dil filtresi şu sırayla belirlenir: videonun ses dili bilgisi varsa o, yoksa kanalın ülkesi, o da yoksa videonun bulunduğu arama ülkesi. *(Benim kararım.)*
- "Yeni kanallar" sekmesinde her satır bir kanaldır ve kanalın en çok izlenen videosunu gösterir. *(Benim kararım.)*
- Kanalın 20'den az ama en az 5 videosu varsa normal, mevcut videolardan hesaplanır. *(Benim kararım.)*
- Bir videoya tıklanınca YouTube'da açılır.
- Telefonda da düzgün görünür.

### Veri
- Videolar 7 gün listede kalır, sonra listeden düşer. Kanal normali için gereken özet veriler saklanmaya devam eder.
- Her taramada izlenme sayısı yeniden kaydedilir. Böylece ileride "son 24 saatteki artış" gibi hız ölçüleri eklenebilir.

### Teknoloji (benim kararım)
- Tarayıcı script: **Python**. Bilgisayarda zaten var, Actions'ta da hazır geliyor. Ek paket gerekmez ya da çok az gerekir.
- Site: **düz HTML, CSS ve JavaScript**. Derleme adımı yoktur.
- Veri: depoda JSON dosyaları. Site tek bir `liste.json` okur, havuz ve geçmiş ayrı dosyalarda tutulur.
- Depo: `BaranIrmak08/youtube-radar` (herkese açık).

### 9 Kasım ayarı (ilk gerçek taramadan sonra, kullanıcı kararı)
- **Yalnızca Türkçe ve İngilizce:** Taranan ülkeler TR, US, GB, CA ve AU. Aramalar `relevanceLanguage` ile yapılıyor, dönüşümlü ülkeler kaldırıldı. Dili Türkçe ya da İngilizce olmayan videolar kanal bilgisi çekilmeden elendiği için kota harcamıyor. Halka açılırsa başka diller eklenebilir.
- **Kat en az 5:** Daha düşük kattaki videolar listelenmiyor.
- **Ayıklamalar:** Beğeni/izlenme oranı binde 1'in altındaysa video muhtemel reklam sayılıp elenir. Canlı yayınlar ve "- Topic" müzik kanalları da elenir. Haber ve diziler elenmez, kategori filtresiyle gizlenebilir.

## 6. Kurulumda kullanıcıdan gerekecekler
1. **YouTube API anahtarı:** Google Cloud'da proje açılır, YouTube Data API v3 etkinleştirilir, anahtar oluşturulur. Ücretsizdir, kart istemez. Ekran ekran rehberlik edilecek.
2. Anahtarı GitHub deposunun Secrets bölümüne **kullanıcı kendisi** yapıştırır. Anahtar sohbete yazılmaz.
3. İlk taramadan sonra sonuçlara bakıp alt sınır ve yaş düzeltmesinin ayarını onaylamak.

## 7. Kurucuya bırakılanlar
- Yaş düzeltmesinin tam formülü. Bu formül ilk gerçek verilerle ayarlanacak, kullanıcıya örnek sonuçlarla gösterilecek.
- Arama ve takip arasındaki kesin kota paylaşımı. Kota bitmeden duran bir bütçe sayacı olacak.
- Kategori listesi ve dönüşümlü ülkelerin sırası.
- GitHub zamanlanmış görevleri depo 60 gün hareketsiz kalırsa durur. Bunu günlük veri commit'i önler, yine de kontrol edilecek.
- Kanal havuzunun büyüme sınırı (dosya boyutu ve kota).

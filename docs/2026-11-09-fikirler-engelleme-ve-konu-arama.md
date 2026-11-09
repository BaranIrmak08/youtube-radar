# Fikirler: kanal engelleme düğmesi ve konuya göre viral arama

9 Kasım 2026. **Kanal engelleme yapıldı (seçenek A), anahtar adımları için `kanal-engelleme-anahtari.md`. Konu arama henüz yapılmadı.**

## Temel sorun: site kendi başına bir şey kaydedemez

Site GitHub Pages'te duran düz bir sayfa. Sunucusu yok. Bu yüzden siteden basılan bir düğme ancak iki yere bir şey yazabilir:

1. **Senin tarayıcına** (localStorage). Anında çalışır ama yalnızca o tarayıcıda geçerli olur. Tarayıcı da bunu bilmez, kanalı taramaya devam eder.
2. **GitHub'daki depoya**, senin vereceğin bir erişim anahtarıyla (fine-grained personal access token). Anahtar yalnızca bu depoya ve yalnızca gerekli izinlerle sınırlı olur, yalnızca senin tarayıcında saklanır, depoya hiç girmez. Anahtar girilmemişse düğmeler hiç görünmez. Böylece siteye giren başka biri bir şey değiştiremez.

İki özellik de aynı anahtarı kullanabilir. Anahtarı bir kez "Ayarlar" bölümüne yapıştırırsın, bu kadar.

## 1. Kanal engelleme düğmesi

**Nasıl görünür:** Her satırın sonunda küçük bir "⋯" düğmesi olur. Tıklayınca açılan menüde "Kanalı engelle" seçeneği çıkar. Kartlarda da aynı düğme sağ üst köşede yer alır.

**Bastığında ne olur:**
1. O kanalın bütün videoları listeden hemen kalkar (sayfa yenilenmeden).
2. Site, depodaki `data/engel.txt` dosyasına `UC... # Kanal adı` satırını ekleyen bir commit atar. Kanal adı değişebileceği için kanal ID'siyle engellemek daha sağlam.
3. Sonraki taramalarda tarayıcı bu kanalı zaten atlıyor: havuz taramasına almıyor, normalini çekmiyor, videolarını listeye koymuyor. Bu kısım bugün yazdığımız kodda hazır.
4. Ekranın altında birkaç saniye "Kanal engellendi, Geri al" yazısı çıkar. "Geri al" satırı dosyadan siler. Yanlışlıkla basmaya karşı onay penceresinden daha az can sıkar.

**Ek olarak:** Ayarlar bölümünde "Engellenen kanallar" listesi olur, oradan istediğin kanalın engeli kaldırılabilir. Bu da `izin.txt` ile aynı işi görür.

**Bilinmesi gereken:** Commit atıldıktan sonra yayındaki `liste.json` dosyası ancak bir sonraki taramada yenilenir. Bu yüzden engellenen kanal o zamana kadar senin tarayıcında localStorage ile gizli tutulur. Başka cihazdan girersen tarama olana kadar görünmeye devam eder.

**Seçenekler:**
- **A (önerilen):** Anahtarla depoya yazma ve tarayıcıda anında gizleme birlikte. Tam istediğin şey bu: kalıcı, her cihazda geçerli, tarama da kanala bakmaz.
- **B (anahtarsız, basit):** Yalnızca tarayıcında gizleme. Ayrıca "Engelleme listesine ekle" düğmesi, GitHub'da `engel.txt` dosyasının düzenleme sayfasını açar ve sen "Commit" dersin. Anahtar gerekmez ama her seferinde bir adım fazla.

## 2. Konuya göre viral video arama

**Yapılabilir mi:** Evet. YouTube API'sinin arama uç noktası (`search.list`) bir kelimeyle, son 7 gün içinde, en çok izlenene göre arama yapabiliyor. Çıkan videolara bizim mevcut "kat" hesabımızı uygularız. Kanalının normalinin en az 5 katı izlenmeyen videolar elenir. Böylece o konudaki gerçekten patlayan videolar kalır. Kurum filtresi ve engel listesi de aynen uygulanır.

**Nasıl görünür:** Üstte yeni bir "Konu ara" sekmesi olur. Örneğin "AI animation shorts" yazıp "Ara" dersin. Birkaç dakika sonra sonuçlar aynı tabloda, aynı filtre ve sıralamayla gelir. Geçmiş aramalar sekmede saklanır, tekrar bakılabilir.

**Kota hesabı:** Arama YouTube API'sinin en pahalı işlemi, her arama 100 birim tutuyor (50 sonuç). Bir konu araması için yaklaşık şunlar gerekir:
- 4 arama (Türkçe ve İngilizce bölgeler, Short ve uzun video ayrı): 400 birim
- Video ayrıntıları ve kanalların normalleri: yaklaşık 200 ile 400 birim
- **Toplam: konu başına yaklaşık 600 ile 800 birim**

Günlük kotamız 10.000, günlük tarama yaklaşık 7.000 harcıyor. Yani günde **3 ya da 4 konu araması** sığar. Daha fazlası istenirse Google'dan ücretsiz kota artışı istenebilir (form doldurulur, inceleniyor), ya da günlük taramanın arama sayısı biraz azaltılır.

**Nerede çalışacak, iki seçenek:**
- **A (önerilen): GitHub Actions'ta.** Site, yazdığın konuyu GitHub'a gönderir (yukarıdaki anahtarla, `workflow_dispatch` olarak). Mevcut Python tarayıcı o konu için arama yapar, sonucu `site/konular/<konu>.json` olarak kaydedip siteyi yeniler. YouTube anahtarı GitHub Secrets'ta kalır, hiçbir zaman tarayıcıya gelmez. Sonuç yaklaşık 2 ile 4 dakikada gelir. Kat hesabı ve filtreler zaten yazılmış ve test edilmiş Python kodunu kullanır.
- **B: Doğrudan tarayıcıda.** YouTube anahtarını (ayrı, yalnızca bu siteye kısıtlanmış bir anahtar) tarayıcına girersin, arama sonuçları birkaç saniyede gelir. Ama kat hesabını ve filtreleri JavaScript'te yeniden yazmak gerekir. Site halka açılırsa ziyaretçilerin kendi anahtarlarını girmesi için de bu yol uygun. Önce A, halka açılınca B mantıklı.

**Sınırlar, dürüstçe:**
- YouTube araması kelimeye bakar, videonun içeriğini anlamaz. "AI animation" diye etiketlenmemiş bir yapay zekâ videosu bulunmaz. Etiketlenmiş ama alakasız bir video da gelebilir.
- Bunu azaltmak için tek kutuya virgülle birkaç ifade yazılabilir, her biri ayrı arar (örneğin `ai animation, ai shorts, #aianimation, yapay zeka animasyon`). Ama her ifade kotayı artırır.
- İstersen ileride arama ifadelerini yapay zekâya genişlettirmek de mümkün. Bunun için bir yapay zekâ API anahtarı gerekir, şimdilik gereksiz.

**Ek fikir, "takip edilen konular":** Sık bakacağın bir konuyu "takip et" dersin, günlük tarama o konuyu da her gün kendiliğinden arar. Konu başına günde yaklaşık 600 birim tutar, en fazla 2 ya da 3 konu takip edilebilir.

## Sıra önerisi

1. Önce anahtar ve "Ayarlar" bölümü (iki özelliğin ortak temeli).
2. Kanal engelleme düğmesi (küçük iş, anında fayda).
3. Konu arama, Actions üzerinden (orta büyüklükte iş).
4. Sonra gerekirse "takip edilen konular".

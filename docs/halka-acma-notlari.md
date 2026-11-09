# Halka açma notları

Bugün YouTube Radar tamamen GitHub üzerinde çalışıyor: tarama ve konu araması GitHub Actions'ta, site GitHub Pages'te, yazma işlemleri (kanal engelleme, konu araması isteme) kullanıcının kendi GitHub anahtarıyla yapılıyor. Kod, ileride kendi sunucumuza geçişi kolaylaştıracak şekilde katmanlara ayrıldı.

## GitHub'a bağlı olmayan parçalar (aynen kalır)

| Parça | Dosya | Ne yapar |
| --- | --- | --- |
| Tarama ve puanlama çekirdeği | `radar/main.py`, `radar/score.py`, `radar/plan.py` | Keşif, kanal normali, kat, kurum filtresi, liste üretimi |
| Konu araması çekirdeği | `radar/konu.py` (`konu_ara`, `calistir_konu`) | Bir istek alır, sonucu JSON olarak yazar |
| YouTube istemcisi | `radar/api.py` | Kota sayaçlı API istemcisi, yalnızca standart kütüphane |
| Kota defteri | `radar/kota.py` | Günlük harcamayı tutar, konu aramasını sınırlar |
| Site arayüzü | `site/app.js`, `site/index.html`, `site/style.css` | Yalnızca statik JSON okur, yazma işlerini `arkaUc` nesnesine bırakır |

Site yalnızca şu statik dosyaları okur. Bunlar her sunucuda aynı adreste durduğu sürece arayüz değişmez:
`liste.json`, `konular/index.json`, `konular/<id>.json`.

## GitHub'a bağlı parçalar (değişecek olanlar)

| Parça | Bugün | Halka açılınca |
| --- | --- | --- |
| Yazma işlemleri | `site/arkauc.js` içindeki `githubArkaUcu`: depoya commit atar | Aynı arayüzle bir `sunucuArkaUcu` yazılır, dosyanın son satırı değişir |
| İşlerin tetiklenmesi | `.github/workflows/tara.yml` (elle ya da zamanlanmış), `konu.yml` (`data/konu-istek.json` değişince) | Sunucuda bir zamanlayıcı (cron) `python -m radar.main` çalıştırır; konu isteği bir HTTP uç noktasından gelir ve `calistir_konu` çağrılır |
| Veri saklama | `data/*.json`, `data/engel.txt` depoda | Aynı dosyalar sunucunun diskinde ya da bir veritabanında; `radar/store.py` tek giriş noktası |
| Yayın | GitHub Pages | Herhangi bir statik dosya sunucusu |
| Kimlik | Kullanıcının GitHub anahtarı | Sitenin kendi giriş sistemi |

## `arkaUc` arayüzü

`site/arkauc.js` başında yazılı. Kısaca:

- `hazir()`: yazma işlemleri kullanılabilir mi (engelle ve Ara düğmeleri buna göre görünür)
- `dene()`: bağlantıyı ve izni sınar
- `engelListesi()`, `engelEkle(id, ad)`, `engelKaldir(id, ad)`
- `konuIste(id, konu)`: aramayı kuyruğa koyar; sonuç `konular/<id>.json` olarak gelir, site `konular/index.json` dosyasını yoklayarak bekler
- `isKaydi()`: arama gecikirse gösterilecek adres

## Halka açılınca düşünülecekler

- **Kişiye özel engel listesi:** Bugün tek bir `engel.txt` var, yani engel herkes için geçerli. Çok kullanıcılı yapıda engel listesi kullanıcı başına tutulmalı, ortak listeye yalnızca açık kurum kanalları girmeli.
- **Kota:** Ücretsiz YouTube kotası günde 10.000 birim. Çok kullanıcıda ya Google'dan kota artışı istenir ya da kullanıcılar kendi YouTube API anahtarlarını girer. İkinci yol için `arkaUc` yerine tarayıcıda çalışan bir arama da yazılabilir; bunun için kat hesabının JavaScript karşılığı gerekir.
- **Konu araması sonuçları:** Bugün son 10 arama herkese açık dosyalarda duruyor. Kullanıcı başına ayrılmalı.

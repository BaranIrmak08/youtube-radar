# Kanal engelleme için GitHub anahtarı

Sitedeki "Kanalı engelle" düğmeleri, `data/engel.txt` dosyasına senin adına satır ekler. Bunun için GitHub'ın verdiği, yalnızca bu depoya ve yalnızca dosya yazmaya izin veren bir anahtar gerekir. Anahtarı yalnızca sen oluşturur ve sitenin Ayarlar penceresine yalnızca sen yapıştırırsın. Anahtar depoya hiçbir zaman yazılmaz.

## Anahtarı oluşturma (bir kez)

1. github.com'da sağ üstteki profil resmine tıkla, **Settings**'i aç.
2. Sol menünün en altındaki **Developer settings**'e gir.
3. **Personal access tokens** başlığı altında **Fine-grained tokens**'ı seç, sonra **Generate new token**'a tıkla.
4. **Token name:** `youtube-radar engel` (istediğin bir ad).
5. **Expiration:** 1 yıl ya da istediğin bir süre. Süre dolunca site "anahtar geçersiz" der, yenisini oluşturursun.
6. **Repository access:** **Only select repositories** seçeneğini işaretle ve yalnızca `youtube-radar` deposunu seç.
7. **Permissions** bölümünde **Repository permissions** altındaki **Contents** iznini **Read and write** yap. Başka bir izne dokunma (Metadata kendiliğinden "Read-only" olur).
8. **Generate token**'a tıkla. Anahtar yalnızca bir kez gösterilir, kopyala.

## Siteye girme

1. Sitede sağ üstteki **Ayarlar**'a tıkla.
2. Anahtarı kutuya yapıştır ve **Kaydet ve dene**'ye bas.
3. "Anahtar çalışıyor" yazısı çıkınca her satırın sonunda engelle düğmesi görünür.

Her tarayıcıda ve her cihazda bir kez girmen gerekir. Telefonda da kullanacaksan oraya da yapıştırırsın.

## Bilinmesi gerekenler

- Anahtar yalnızca o tarayıcıda saklanır. Siteye giren başkası düğmeleri görmez, bir şey değiştiremez.
- `baranirmak08.github.io` altındaki bütün GitHub Pages sitelerin aynı tarayıcı alanını paylaşır. Anahtarın izni yalnızca bu deponun dosyalarıyla sınırlı olduğu için, olası bir sızıntıda en fazla bu deponun dosyaları değiştirilebilir.
- Anahtarı GitHub'da aynı sayfadan istediğin an iptal edebilirsin (**Revoke**). Sitede Ayarlar penceresindeki **Anahtarı sil** düğmesi de anahtarı yalnızca o tarayıcıdan siler.

## Engelleme nasıl işler

- Düğmeye basınca kanalın bütün videoları listeden hemen kalkar ve `data/engel.txt` dosyasına `UC... # Kanal adı` satırı eklenir. Birkaç saniye boyunca **Geri al** seçeneği görünür.
- Sonraki taramalar bu kanala hiç bakmaz: kanalın yüklemelerini taramaz, normalini hesaplamaz, videolarını listeye koymaz.
- Yayındaki liste bir sonraki taramaya kadar eski haliyle kalır. O zamana kadar engellenen kanal yalnızca senin tarayıcında gizlenir.
- Engeli kaldırmak için Ayarlar penceresindeki **Engellenen kanallar** listesini kullan.

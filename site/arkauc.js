// YouTube Radar: arka uç katmanı.
//
// Sitenin bir şey YAZDIĞI her işlem (kanal engelleme, konu araması isteme) yalnızca bu dosyadan geçer.
// Okumalar düz statik dosyalardır (liste.json, konular/*.json) ve her sunucuda aynen çalışır.
//
// Bugün: GitHub. Kullanıcının kendi "fine-grained" anahtarıyla (yalnızca bu depo, Contents izni)
// data/engel.txt ve data/konu-istek.json dosyalarına commit atılır; tarama ve konu araması GitHub Actions'ta çalışır.
//
// Halka açılınca: aynı arayüzü sağlayan bir nesneyi (ör. kendi sunucumuzun HTTP API'sine giden
// sunucuArkaUcu) yazıp en alttaki satırı değiştirmek yeterli. app.js'e dokunmak gerekmez.
// Arayüz:
//   hazir()                 -> bool    yazma işlemleri kullanılabilir mi (düğmeler buna göre görünür)
//   dene()                  -> Promise bağlantıyı/izni sınar
//   engelListesi()          -> Promise<[{id, ad}]>
//   engelEkle(id, ad)       -> Promise
//   engelKaldir(id, ad)     -> Promise
//   konuIste(id, konu)      -> Promise arama isteğini kuyruğa koyar; sonuç konular/<id>.json olarak gelir
//   isKaydi()               -> string  arama gecikirse kullanıcıya gösterilecek iş kaydı adresi
"use strict";

function engelSatirlari(metin) {
  return metin.split(/\r?\n/).map(s => s.trim()).filter(s => s && !s.startsWith("#"))
    .map(s => { const [id, ...ad] = s.split(" #"); return { id: id.trim(), ad: ad.join(" #").trim() || id.trim() }; });
}

function githubArkaUcu(depo, anahtarAl) {
  const ENGEL = "data/engel.txt", ISTEK = "data/konu-istek.json";

  async function github(yol, ayar) {
    const r = await fetch("https://api.github.com/repos/" + depo + yol, {
      ...ayar,
      headers: { Authorization: "Bearer " + anahtarAl(), Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", ...(ayar && ayar.body ? { "Content-Type": "application/json" } : {}) },
    });
    if (!r.ok) {
      const e = new Error(r.status === 401 ? "anahtar geçersiz ya da süresi dolmuş"
        : r.status === 403 || r.status === 404 ? "anahtarın bu depoya yazma izni yok"
        : "GitHub hatası " + r.status);
      e.durum = r.status;
      throw e;
    }
    return r.json();
  }

  function b64Coz(s) { return new TextDecoder().decode(Uint8Array.from(atob(s.replace(/\s/g, "")), c => c.charCodeAt(0))); }
  function b64Yap(s) { let b = ""; for (const x of new TextEncoder().encode(s)) b += String.fromCharCode(x); return btoa(b); }

  async function oku(yol) {
    try {
      const d = await github("/contents/" + yol + "?ref=main");
      return { metin: b64Coz(d.content), sha: d.sha };
    } catch (e) {
      if (e.durum === 404) return { metin: "", sha: null };  // dosya henüz yok
      throw e;
    }
  }

  // Okur, değiştirir, yazar; bu arada başkası yazdıysa (409) bir kez yeniden dener.
  async function degistir(yol, donustur, mesaj) {
    for (let deneme = 0; ; deneme++) {
      const { metin, sha } = await oku(yol);
      const yeni = donustur(metin);
      if (yeni === metin) return;
      try {
        await github("/contents/" + yol, { method: "PUT",
          body: JSON.stringify({ message: mesaj, content: b64Yap(yeni), branch: "main", ...(sha ? { sha } : {}) }) });
        return;
      } catch (e) {
        if (e.durum !== 409 || deneme > 0) throw e;
      }
    }
  }

  let kuyruk = Promise.resolve();  // yazma istekleri sırayla gitsin (engelle, hemen ardından geri al)
  function sirayaKoy(is) { kuyruk = kuyruk.then(is, is); return kuyruk; }

  return {
    ad: "github",
    hazir: () => !!anahtarAl(),
    dene: () => github("/contents/" + ENGEL + "?ref=main"),
    engelListesi: async () => engelSatirlari((await oku(ENGEL)).metin),
    engelEkle(id, ad) {
      const temiz = (ad || "").replace(/[\r\n#]+/g, " ").trim();
      return sirayaKoy(() => degistir(ENGEL, metin => {
        if (engelSatirlari(metin).some(s => s.id === id)) return metin;
        return metin.replace(/\s*$/, "\n") + id + " # " + temiz + "\n";
      }, "engel: " + temiz));
    },
    engelKaldir(id, ad) {
      return sirayaKoy(() => degistir(ENGEL, metin =>
        metin.split(/\r?\n/).filter(s => s.split(" #")[0].trim() !== id).join("\n"),
        "engel kaldırıldı: " + (ad || id)));
    },
    konuIste(id, konu) {
      return sirayaKoy(() => degistir(ISTEK,
        () => JSON.stringify({ id, konu, istendi: new Date().toISOString() }, null, 2) + "\n",
        "konu isteği: " + konu.slice(0, 60)));
    },
    isKaydi: () => "https://github.com/" + depo + "/actions/workflows/konu.yml",
  };
}

window.arkaUc = githubArkaUcu("BaranIrmak08/youtube-radar",
  () => { try { return localStorage.getItem("radar.anahtar") || ""; } catch (e) { return ""; } });

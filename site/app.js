// YouTube Radar arayüzü. Veriler yalnızca textContent ile yazılır (innerHTML'e veri konmaz).
"use strict";

const KATEGORI = {
  "1": "Film ve Animasyon", "2": "Otomobil", "10": "Müzik", "15": "Hayvanlar", "17": "Spor",
  "19": "Seyahat", "20": "Oyun", "22": "Kişiler ve Bloglar", "23": "Komedi", "24": "Eğlence",
  "25": "Haber ve Politika", "26": "Nasıl Yapılır", "27": "Eğitim", "28": "Bilim ve Teknoloji",
};

const durum = { veri: null, sekme: "videolar", gorunum: "tablo" };

function hafizaOku(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function hafizaYaz(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* yok say */ } }

function el(etiket, ozellik, ...cocuklar) {
  const e = document.createElement(etiket);
  if (ozellik) for (const [k, v] of Object.entries(ozellik)) {
    if (k === "class") e.className = v; else if (v != null) e.setAttribute(k, v);
  }
  for (const c of cocuklar) if (c != null) e.append(c instanceof Node ? c : String(c));
  return e;
}

function kisa(n) {
  if (n == null) return "–";
  if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1).replace(".", ",") + "M";
  if (n >= 1e3) return Math.round(n / 1e3) + "k";
  return String(Math.round(n));
}
function katYaz(k) {
  return (k >= 10 ? Math.round(k).toLocaleString("tr-TR") : k.toFixed(1).replace(".", ",")) + "x";
}

function yasGun(iso) {
  const ref = new Date(durum.veri.guncellendi).getTime();
  return (ref - new Date(iso).getTime()) / 86400000;
}
function yasYaz(iso) {
  const g = yasGun(iso);
  return g < 1 ? Math.max(1, Math.round(g * 24)) + " saat" : Math.floor(g) + " gün";
}
function tur(v) { return v.is_short ? "Short" : "Uzun"; }
function ytLink(id) { return "https://www.youtube.com/watch?v=" + encodeURIComponent(id); }
function ac(id) { window.open(ytLink(id), "_blank", "noopener"); }
function guvenliResim(u) { return u && /^https:\/\//.test(u) ? u : null; }

function filtrele(v) {
  const zaman = +document.getElementById("f-zaman").value;
  const t = document.getElementById("f-tur").value;
  const u = document.getElementById("f-ulke").value;
  const k = document.getElementById("f-kategori").value;
  if (yasGun(v.published) > zaman) return false;
  if (t === "short" && !v.is_short) return false;
  if (t === "uzun" && v.is_short) return false;
  if (u && (v.ulke || "").toUpperCase() !== u) return false;
  if (k && v.category_id !== k) return false;
  return true;
}

function secenekDoldur() {
  const hepsi = [...durum.veri.videolar, ...durum.veri.yeni_kanallar.map(k => k.en_iyi)];
  const ulkeler = [...new Set(hepsi.map(v => (v.ulke || "").toUpperCase()).filter(Boolean))].sort();
  const kategoriler = [...new Set(hepsi.map(v => v.category_id).filter(Boolean))]
    .sort((a, b) => (KATEGORI[a] || a).localeCompare(KATEGORI[b] || b, "tr"));
  const su = document.getElementById("f-ulke"), sk = document.getElementById("f-kategori");
  for (const u of ulkeler) su.append(el("option", { value: u }, u));
  for (const k of kategoriler) sk.append(el("option", { value: k }, KATEGORI[k] || ("Kategori " + k)));
}

// Hücreler ---------------------------------------------------------------

function videoHucre(v, kanalAdi) {
  const resim = guvenliResim(v.thumb);
  const baslik = el("a", { class: "video__baslik", href: ytLink(v.id), target: "_blank", rel: "noopener" }, v.title);
  baslik.addEventListener("click", e => e.stopPropagation());
  return el("td", { class: "hucre-video" }, el("div", { class: "video" },
    resim ? el("img", { class: "video__resim", src: resim, alt: "", loading: "lazy", width: "96", height: "54" })
          : el("div", { class: "video__resim" }),
    el("div", { class: "video__metin" }, baslik, el("span", { class: "video__kanal" }, kanalAdi))));
}

function okuma(v) {
  return el("div", { class: "okuma" },
    el("span", { class: "okuma__kat" }, katYaz(v.kat)),
    el("span", { class: "okuma__toplam" }, kisa(v.views) + " / " + kisa(v.normal)));
}

function hucre(etiket, icerik, sinif) {
  return el("td", { class: sinif || null, "data-etiket": etiket }, icerik);
}

function tablo(basliklar, tbody) {
  return el("table", null,
    el("thead", null, el("tr", null, ...basliklar.map(([b, s]) => el("th", { class: s || null, scope: "col" }, b)))),
    tbody);
}

// Tablolar ---------------------------------------------------------------

function videoTablo(liste) {
  const tbody = el("tbody");
  for (const v of liste) {
    const tr = el("tr", null,
      el("td", { class: "hucre-okuma" }, okuma(v)),
      videoHucre(v, v.channel_title),
      hucre("İzlenme", kisa(v.views), "olcum sag"),
      hucre("Normali", kisa(v.normal), "olcum sag"),
      hucre("Yaş", yasYaz(v.published), "olcum"),
      hucre("Tür", el("span", { class: "etiket" }, tur(v))));
    tr.addEventListener("click", () => ac(v.id));
    tbody.append(tr);
  }
  return tablo([["Kat"], ["Video"], ["İzlenme", "sag"], ["Normali", "sag"], ["Yaş"], ["Tür"]], tbody);
}

function yeniTablo(liste) {
  const tbody = el("tbody");
  for (const k of liste) {
    const v = k.en_iyi;
    const tr = el("tr", null,
      el("td", { class: "hucre-okuma" }, el("div", { class: "okuma" },
        el("span", { class: "okuma__kat" }, kisa(v.views)),
        el("span", { class: "okuma__toplam" }, "izlenme"))),
      videoHucre(v, k.channel_title),
      hucre("Kanal yaşı", k.kanal_yasi_gun == null ? "–" : Math.floor(k.kanal_yasi_gun) + " gün", "olcum sag"),
      hucre("Video", k.video_sayisi ?? "–", "olcum sag"),
      hucre("Yaş", yasYaz(v.published), "olcum"),
      hucre("Tür", el("span", { class: "etiket" }, tur(v))));
    tr.addEventListener("click", () => ac(v.id));
    tbody.append(tr);
  }
  return tablo([["İzlenme"], ["En iyi video"], ["Kanal yaşı", "sag"], ["Video", "sag"], ["Yaş"], ["Tür"]], tbody);
}

// Kartlar ----------------------------------------------------------------

function bilgi(ciftler) {
  return el("dl", { class: "kart__bilgi" },
    ...ciftler.map(([d, t]) => el("div", null, el("dt", null, d), el("dd", { class: "olcum" }, t))));
}

function kart(v, ust, ciftler) {
  const a = el("a", { class: "kart", href: ytLink(v.id), target: "_blank", rel: "noopener" });
  const resim = guvenliResim(v.thumb);
  a.append(resim ? el("img", { class: "kart__resim", src: resim, alt: "", loading: "lazy", width: "320", height: "180" })
                 : el("div", { class: "kart__resim" }));
  a.append(el("div", { class: "kart__govde" }, ust, el("span", { class: "kart__baslik" }, v.title), bilgi(ciftler)));
  return a;
}

function videoKartlar(liste) {
  return el("div", { class: "kartlar" }, ...liste.map(v => kart(v, okuma(v), [
    ["Kanal", v.channel_title], ["Yaş", yasYaz(v.published)], ["Tür", tur(v)]])));
}

function yeniKartlar(liste) {
  return el("div", { class: "kartlar" }, ...liste.map(k => kart(k.en_iyi,
    el("div", { class: "okuma" }, el("span", { class: "okuma__kat" }, kisa(k.en_iyi.views)),
      el("span", { class: "okuma__toplam" }, "izlenme")), [
      ["Kanal", k.channel_title],
      ["Kanal yaşı", k.kanal_yasi_gun == null ? "?" : Math.floor(k.kanal_yasi_gun) + " gün"],
      ["Video", k.video_sayisi ?? "?"], ["Tür", tur(k.en_iyi)]])));
}

// CSV --------------------------------------------------------------------

// Türkçe Excel noktalı virgülü ayırıcı, virgülü ondalık sayar.
function csvHucre(d) {
  let s = d == null ? "" : String(d);
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;  // Excel'de formül olarak çalışmasın
  return /[";\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
function csvSayi(n, basamak) {
  return n == null ? "" : (basamak ? n.toFixed(basamak) : String(Math.round(n))).replace(".", ",");
}
function csvTarih(iso) { return iso ? iso.replace("T", " ").replace("Z", "") : ""; }
function kategoriAdi(id) { return id ? (KATEGORI[id] || id) : ""; }

function csvSatirlar(liste) {
  if (durum.sekme === "videolar") {
    return [["Kat", "Başlık", "Kanal", "İzlenme", "Kanal normali", "Yayın (UTC)", "Tür", "Dil", "Kategori", "Link"],
      ...liste.map(v => [csvSayi(v.kat, 2), v.title, v.channel_title, csvSayi(v.views), csvSayi(v.normal),
        csvTarih(v.published), tur(v), v.ulke, kategoriAdi(v.category_id), ytLink(v.id)])];
  }
  return [["Kanal", "En iyi video", "İzlenme", "Kanal yaşı (gün)", "Video sayısı", "Abone", "Yayın (UTC)", "Tür", "Dil", "Kategori", "Link"],
    ...liste.map(k => {
      const v = k.en_iyi;
      return [k.channel_title, v.title, csvSayi(v.views), csvSayi(k.kanal_yasi_gun, 1), csvSayi(k.video_sayisi),
        csvSayi(k.subs), csvTarih(v.published), tur(v), v.ulke, kategoriAdi(v.category_id), ytLink(v.id)];
    })];
}

function csvIndir() {
  const liste = guncelListe();
  if (!liste.length) return;
  const metin = "﻿" + csvSatirlar(liste).map(r => r.map(csvHucre).join(";")).join("\r\n") + "\r\n";
  const tarih = (durum.veri.guncellendi || new Date().toISOString()).slice(0, 10);
  const ad = "youtube-radar-" + (durum.sekme === "videolar" ? "videolar" : "yeni-kanallar") + "-" + tarih + ".csv";
  const url = URL.createObjectURL(new Blob([metin], { type: "text/csv;charset=utf-8" }));
  const a = el("a", { href: url, download: ad });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Çizim ------------------------------------------------------------------

function guncelListe() {
  return durum.sekme === "videolar"
    ? durum.veri.videolar.filter(filtrele)
    : durum.veri.yeni_kanallar.filter(k => filtrele(k.en_iyi));
}

function filtreleriSifirla() {
  document.getElementById("f-zaman").value = "7";
  for (const id of ["f-tur", "f-ulke", "f-kategori"]) document.getElementById(id).value = "";
  ciz();
}

function bosDurum() {
  const dar = document.getElementById("f-zaman").value !== "7" ||
    ["f-tur", "f-ulke", "f-kategori"].some(id => document.getElementById(id).value);
  const kutu = el("div", { class: "bos" },
    el("p", { class: "bos__ana" }, durum.sekme === "videolar" ? "Bu filtrelerle patlayan video yok." : "Bu filtrelerle yeni kanal yok."),
    el("p", null, dar ? "Filtreler listeyi daraltıyor. Son 7 güne ve tüm türlere bakabilirsin."
                      : "Bu taramada uygun video çıkmadı. Bir sonraki tarama listeyi yeniler."));
  if (dar) {
    const b = el("button", { type: "button", class: "btn" }, "Filtreleri sıfırla");
    b.addEventListener("click", filtreleriSifirla);
    kutu.append(b);
  }
  return kutu;
}

function ciz() {
  for (const b of document.querySelectorAll("[data-sekme]")) {
    b.classList.toggle("aktif", b.dataset.sekme === durum.sekme);
    b.setAttribute("aria-selected", String(b.dataset.sekme === durum.sekme));
  }
  for (const b of document.querySelectorAll("[data-gorunum]")) {
    b.classList.toggle("aktif", b.dataset.gorunum === durum.gorunum);
    b.setAttribute("aria-pressed", String(b.dataset.gorunum === durum.gorunum));
  }
  const kutu = document.getElementById("icerik");
  kutu.replaceChildren();
  const liste = guncelListe();
  const cizici = durum.sekme === "videolar"
    ? (durum.gorunum === "tablo" ? videoTablo : videoKartlar)
    : (durum.gorunum === "tablo" ? yeniTablo : yeniKartlar);
  document.getElementById("sayac").textContent = liste.length.toLocaleString("tr-TR") + " sonuç";
  const csv = document.getElementById("csv-indir");
  csv.disabled = !liste.length;
  csv.title = liste.length ? "Ekrandaki listeyi indir" : "İndirilecek sonuç yok";
  kutu.append(liste.length ? cizici(liste) : bosDurum());
}

function durumYaz(veri) {
  const t = new Date(veri.guncellendi);
  const p = document.getElementById("durum");
  p.replaceChildren(
    el("span", null, "Son tarama ", el("span", { class: "olcum" },
      t.toLocaleString("tr-TR", { dateStyle: "long", timeStyle: "short" }))),
    el("span", null, el("span", { class: "olcum" }, (veri.harcanan ?? 0).toLocaleString("tr-TR")), " birim kota"));
  if (veri.kota_bitti) p.append(el("span", { class: "kotu" }, "Kota bitti, tarama eksik"));
}

async function yukle() {
  let ornek = false, veri;
  try {
    const r = await fetch("liste.json", { cache: "no-store" });
    if (!r.ok) throw new Error();
    veri = await r.json();
  } catch (e) {
    const r = await fetch("ornek-liste.json");
    veri = await r.json();
    ornek = true;
  }
  durum.veri = veri;
  document.getElementById("ornek-uyari").hidden = !ornek;
  durumYaz(veri);
  secenekDoldur();
  ciz();
}

durum.gorunum = hafizaOku("radar.gorunum") === "kart" ? "kart" : "tablo";
for (const b of document.querySelectorAll("[data-sekme]")) b.addEventListener("click", () => { durum.sekme = b.dataset.sekme; ciz(); });
for (const b of document.querySelectorAll("[data-gorunum]")) b.addEventListener("click", () => {
  durum.gorunum = b.dataset.gorunum; hafizaYaz("radar.gorunum", durum.gorunum); ciz();
});
for (const s of document.querySelectorAll(".filtreler select")) s.addEventListener("change", () => durum.veri && ciz());
document.getElementById("csv-indir").addEventListener("click", () => durum.veri && csvIndir());
yukle().catch(() => {
  document.getElementById("durum").textContent = "Veri yüklenemedi.";
  document.getElementById("icerik").replaceChildren(el("div", { class: "bos" },
    el("p", { class: "bos__ana" }, "Liste yüklenemedi."),
    el("p", null, "Bağlantını kontrol edip sayfayı yenile. Sorun sürerse liste dosyası henüz yayınlanmamış olabilir.")));
});

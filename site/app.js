// YouTube Radar arayüzü. Veriler yalnızca textContent ile yazılır (innerHTML'e veri konmaz).
"use strict";

const KATEGORI = {
  "1": "Film ve Animasyon", "2": "Otomobil", "10": "Müzik", "15": "Hayvanlar", "17": "Spor",
  "19": "Seyahat", "20": "Oyun", "22": "Kişiler ve Bloglar", "23": "Komedi", "24": "Eğlence",
  "25": "Haber ve Politika", "26": "Nasıl Yapılır", "27": "Eğitim", "28": "Bilim ve Teknoloji",
};

const durum = { veri: null, sekme: "videolar", gorunum: "tablo", sira: { alan: "onerilen", yon: -1 } };

// Sıralama alanları: [etiket, değer okuyucu, varsayılan yön (-1 azalan, 1 artan)]
const SIRALAR = {
  videolar: {
    onerilen: ["Önerilen sıra", null, -1],
    kat: ["Kat", v => v.kat, -1],
    izlenme: ["İzlenme", v => v.views, -1],
    normal: ["Kanal normali", v => v.normal, -1],
    yas: ["En yeni", v => v.published, -1],
  },
  yeni: {
    onerilen: ["Önerilen sıra", null, -1],
    izlenme: ["İzlenme", k => k.en_iyi.views, -1],
    kanal_yasi: ["Kanal yaşı (gençten)", k => k.kanal_yasi_gun, 1],
    video: ["Video sayısı", k => k.video_sayisi, -1],
    yas: ["En yeni", k => k.en_iyi.published, -1],
  },
};

function hafizaOku(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function hafizaYaz(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* yok say */ } }
function hafizaSil(k) { try { localStorage.removeItem(k); } catch (e) { /* yok say */ } }

// Kanal engelleme ---------------------------------------------------------
// Engel listesi depodaki data/engel.txt dosyasıdır; tarayıcı bir sonraki taramada bu kanallara hiç bakmaz.
// Site, kullanıcının kendi GitHub anahtarıyla bu dosyaya commit atar. Anahtar yalnızca bu tarayıcıda durur.
const DEPO = "BaranIrmak08/youtube-radar";
const ENGEL_YOLU = "data/engel.txt";

function anahtar() { return hafizaOku("radar.anahtar") || ""; }

// Engellenen kanallar, liste.json bir sonraki taramada yenilenene kadar bu tarayıcıda gizli tutulur.
function gizlilerOku() { try { return JSON.parse(hafizaOku("radar.gizli") || "{}"); } catch (e) { return {}; } }
const gizliler = gizlilerOku();
function gizlileriYaz() { hafizaYaz("radar.gizli", JSON.stringify(gizliler)); }

async function github(yol, ayar) {
  const r = await fetch("https://api.github.com/repos/" + DEPO + yol, {
    ...ayar,
    headers: { Authorization: "Bearer " + anahtar(), Accept: "application/vnd.github+json",
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

async function engelDosyasiOku() {
  const d = await github("/contents/" + ENGEL_YOLU + "?ref=main");
  return { metin: b64Coz(d.content), sha: d.sha };
}

// Dosyayı okur, değiştirir, yazar; bu arada başkası yazdıysa (409) bir kez yeniden dener.
async function engelDosyasiDegistir(degistir, mesaj) {
  for (let deneme = 0; ; deneme++) {
    const { metin, sha } = await engelDosyasiOku();
    const yeni = degistir(metin);
    if (yeni === metin) return;
    try {
      await github("/contents/" + ENGEL_YOLU, { method: "PUT",
        body: JSON.stringify({ message: mesaj, content: b64Yap(yeni), sha, branch: "main" }) });
      return;
    } catch (e) {
      if (e.durum !== 409 || deneme > 0) throw e;
    }
  }
}

function engelSatirlari(metin) {
  return metin.split(/\r?\n/).map(s => s.trim()).filter(s => s && !s.startsWith("#"))
    .map(s => { const [id, ...ad] = s.split(" #"); return { id: id.trim(), ad: ad.join(" #").trim() || id.trim() }; });
}

let kuyruk = Promise.resolve();  // engelle / geri al istekleri sırayla gitsin
function sirayaKoy(is) { kuyruk = kuyruk.then(is, is); return kuyruk; }

function engelEkle(id, ad) {
  const temizAd = (ad || "").replace(/[\r\n#]+/g, " ").trim();
  return sirayaKoy(() => engelDosyasiDegistir(metin => {
    if (engelSatirlari(metin).some(s => s.id === id)) return metin;
    return metin.replace(/\s*$/, "\n") + id + " # " + temizAd + "\n";
  }, "engel: " + temizAd));
}

function engelKaldir(id, ad) {
  return sirayaKoy(() => engelDosyasiDegistir(metin =>
    metin.split(/\r?\n/).filter(s => s.split(" #")[0].trim() !== id).join("\n"),
    "engel kaldırıldı: " + (ad || id)));
}

let bildirimZamani = null;
function bildir(metin, geriAl) {
  const kutu = document.getElementById("bildirim"), geri = document.getElementById("bildirim-geri");
  document.getElementById("bildirim-metin").textContent = metin;
  geri.hidden = !geriAl;
  geri.onclick = geriAl ? () => { kutu.hidden = true; geriAl(); } : null;
  kutu.hidden = false;
  clearTimeout(bildirimZamani);
  bildirimZamani = setTimeout(() => { kutu.hidden = true; }, geriAl ? 8000 : 5000);
}

function kanaliEngelle(id, ad) {
  gizliler[id] = ad;
  gizlileriYaz();
  ciz();
  const hata = e => { delete gizliler[id]; gizlileriYaz(); ciz(); bildir("Engellenemedi: " + e.message); };
  engelEkle(id, ad).catch(hata);
  bildir(ad + " engellendi.", () => {
    delete gizliler[id];
    gizlileriYaz();
    ciz();
    engelKaldir(id, ad).catch(e => bildir("Geri alınamadı: " + e.message));
  });
}

function engelDugmesi(id, ad) {
  if (!anahtar()) return null;
  const b = el("button", { type: "button", class: "engel-btn", title: "Kanalı engelle", "aria-label": "Kanalı engelle: " + ad });
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("aria-hidden", "true");
  for (const [etiket, nit] of [["circle", { cx: "8", cy: "8", r: "6" }], ["line", { x1: "3.8", y1: "12.2", x2: "12.2", y2: "3.8" }]]) {
    const p = document.createElementNS("http://www.w3.org/2000/svg", etiket);
    for (const [k, v] of Object.entries(nit)) p.setAttribute(k, v);
    svg.append(p);
  }
  b.append(svg);
  b.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); kanaliEngelle(id, ad); });
  return b;
}

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
  if (gizliler[v.channel_id] !== undefined) return false;
  const ara = document.getElementById("f-ara").value.trim().toLocaleLowerCase("tr");
  if (ara && !((v.title || "") + " " + (v.channel_title || "")).toLocaleLowerCase("tr").includes(ara)) return false;
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

function baslikHucre([b, s, alan]) {
  if (!alan) return el("th", { class: s || null, scope: "col" }, b);
  const secili = durum.sira.alan === alan;
  const th = el("th", { class: s || null, scope: "col",
    "aria-sort": secili ? (durum.sira.yon < 0 ? "descending" : "ascending") : null });
  const btn = el("button", { type: "button", class: "sirala" }, b);
  btn.addEventListener("click", () => {
    durum.sira = secili ? { alan, yon: -durum.sira.yon } : { alan, yon: SIRALAR[durum.sekme][alan][2] };
    document.getElementById("f-sira").value = alan;
    ciz();
  });
  th.append(btn);
  return th;
}

function tablo(basliklar, tbody) {
  if (anahtar()) basliklar = [...basliklar, [el("span", { class: "visually-hidden" }, "İşlem"), "islem"]];
  return el("table", null,
    el("thead", null, el("tr", null, ...basliklar.map(baslikHucre))),
    tbody);
}

function islemHucre(id, ad) {
  const b = engelDugmesi(id, ad);
  return b ? el("td", { class: "hucre-islem" }, b) : null;
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
      hucre("Tür", el("span", { class: "etiket" }, tur(v))),
      islemHucre(v.channel_id, v.channel_title));
    tr.addEventListener("click", () => ac(v.id));
    tbody.append(tr);
  }
  return tablo([["Kat", null, "kat"], ["Video"], ["İzlenme", "sag", "izlenme"], ["Normali", "sag", "normal"],
    ["Yaş", null, "yas"], ["Tür"]], tbody);
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
      hucre("Tür", el("span", { class: "etiket" }, tur(v))),
      islemHucre(k.channel_id, k.channel_title));
    tr.addEventListener("click", () => ac(v.id));
    tbody.append(tr);
  }
  return tablo([["İzlenme", null, "izlenme"], ["En iyi video"], ["Kanal yaşı", "sag", "kanal_yasi"],
    ["Video", "sag", "video"], ["Yaş", null, "yas"], ["Tür"]], tbody);
}

// Kartlar ----------------------------------------------------------------

function bilgi(ciftler) {
  return el("dl", { class: "kart__bilgi" },
    ...ciftler.map(([d, t]) => el("div", null, el("dt", null, d), el("dd", { class: "olcum" }, t))));
}

function kart(v, ust, ciftler, kanalId, kanalAdi) {
  const a = el("a", { class: "kart__link", href: ytLink(v.id), target: "_blank", rel: "noopener" });
  const resim = guvenliResim(v.thumb);
  a.append(resim ? el("img", { class: "kart__resim", src: resim, alt: "", loading: "lazy", width: "320", height: "180" })
                 : el("div", { class: "kart__resim" }));
  a.append(el("div", { class: "kart__govde" }, ust, el("span", { class: "kart__baslik" }, v.title), bilgi(ciftler)));
  return el("article", { class: "kart" }, a, engelDugmesi(kanalId, kanalAdi));
}

function videoKartlar(liste) {
  return el("div", { class: "kartlar" }, ...liste.map(v => kart(v, okuma(v), [
    ["Kanal", v.channel_title], ["Yaş", yasYaz(v.published)], ["Tür", tur(v)]], v.channel_id, v.channel_title)));
}

function yeniKartlar(liste) {
  return el("div", { class: "kartlar" }, ...liste.map(k => kart(k.en_iyi,
    el("div", { class: "okuma" }, el("span", { class: "okuma__kat" }, kisa(k.en_iyi.views)),
      el("span", { class: "okuma__toplam" }, "izlenme")), [
      ["Kanal", k.channel_title],
      ["Kanal yaşı", k.kanal_yasi_gun == null ? "?" : Math.floor(k.kanal_yasi_gun) + " gün"],
      ["Video", k.video_sayisi ?? "?"], ["Tür", tur(k.en_iyi)]], k.channel_id, k.channel_title)));
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
  const liste = durum.sekme === "videolar"
    ? durum.veri.videolar.filter(filtrele)
    : durum.veri.yeni_kanallar.filter(k => filtrele(k.en_iyi));
  const tanim = SIRALAR[durum.sekme][durum.sira.alan];
  if (!tanim || !tanim[1]) return liste;  // önerilen sıra: taramanın verdiği sıra
  const oku = tanim[1], yon = durum.sira.yon;
  return liste.slice().sort((a, b) => {
    const x = oku(a), y = oku(b);
    if (x == null) return 1;
    if (y == null) return -1;
    return (x < y ? -1 : x > y ? 1 : 0) * yon;
  });
}

function siraSecenekleri() {
  const s = document.getElementById("f-sira");
  s.replaceChildren(...Object.entries(SIRALAR[durum.sekme]).map(([alan, [ad]]) => el("option", { value: alan }, ad)));
  s.value = durum.sira.alan;
}

function filtreleriSifirla() {
  document.getElementById("f-zaman").value = "7";
  for (const id of ["f-tur", "f-ulke", "f-kategori", "f-ara"]) document.getElementById(id).value = "";
  ciz();
}

function bosDurum() {
  const dar = document.getElementById("f-zaman").value !== "7" ||
    ["f-tur", "f-ulke", "f-kategori", "f-ara"].some(id => document.getElementById(id).value.trim());
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
  siraSecenekleri();
  ciz();
}

// Ayarlar ----------------------------------------------------------------

function ayarDurumu(metin, kotu) {
  const p = document.getElementById("anahtar-durum");
  p.textContent = metin;
  p.classList.toggle("kotu", !!kotu);
}

async function engelListesiCiz() {
  const ul = document.getElementById("engel-listesi");
  if (!anahtar()) { ul.replaceChildren(el("li", { class: "soluk" }, "Liste anahtar girilince görünür.")); return; }
  ul.replaceChildren(el("li", { class: "soluk" }, "Yükleniyor…"));
  try {
    const satirlar = engelSatirlari((await engelDosyasiOku()).metin);
    if (!satirlar.length) { ul.replaceChildren(el("li", { class: "soluk" }, "Henüz engellenen kanal yok.")); return; }
    ul.replaceChildren(...satirlar.map(s => {
      const b = el("button", { type: "button", class: "btn btn--kucuk" }, "Engeli kaldır");
      b.addEventListener("click", async () => {
        b.disabled = true;
        try {
          await engelKaldir(s.id, s.ad);
          delete gizliler[s.id];
          gizlileriYaz();
          if (durum.veri) ciz();
          engelListesiCiz();
        } catch (e) { b.disabled = false; ayarDurumu("Kaldırılamadı: " + e.message, true); }
      });
      return el("li", null, el("span", null, s.ad), b);
    }));
  } catch (e) {
    ul.replaceChildren(el("li", { class: "kotu" }, "Liste okunamadı: " + e.message));
  }
}

function ayarlariAc() {
  const kayitli = !!anahtar();
  const g = document.getElementById("anahtar");
  g.value = "";
  g.placeholder = kayitli ? "Kayıtlı anahtar var, değiştirmek için yenisini yapıştır" : "github_pat_…";
  document.getElementById("anahtar-sil").disabled = !kayitli;
  ayarDurumu(kayitli ? "Anahtar kayıtlı. Engelle düğmeleri açık." : "");
  document.getElementById("ayarlar").showModal();
  engelListesiCiz();
}

async function anahtarKaydet() {
  const deger = document.getElementById("anahtar").value.trim();
  if (!deger) { ayarDurumu("Önce anahtarı yapıştır.", true); return; }
  const eski = anahtar();
  hafizaYaz("radar.anahtar", deger);
  ayarDurumu("Deneniyor…");
  try {
    await engelDosyasiOku();
    document.getElementById("anahtar").value = "";
    document.getElementById("anahtar-sil").disabled = false;
    ayarDurumu("Anahtar çalışıyor. Engelle düğmeleri açıldı.");
    if (durum.veri) ciz();
    engelListesiCiz();
  } catch (e) {
    if (eski) hafizaYaz("radar.anahtar", eski); else hafizaSil("radar.anahtar");
    ayarDurumu("Olmadı: " + e.message + ".", true);
  }
}

document.getElementById("ayarlar-ac").addEventListener("click", ayarlariAc);
document.getElementById("anahtar-kaydet").addEventListener("click", anahtarKaydet);
document.getElementById("anahtar-sil").addEventListener("click", () => {
  hafizaSil("radar.anahtar");
  document.getElementById("anahtar-sil").disabled = true;
  ayarDurumu("Anahtar bu tarayıcıdan silindi.");
  if (durum.veri) ciz();
  engelListesiCiz();
});

durum.gorunum = hafizaOku("radar.gorunum") === "kart" ? "kart" : "tablo";
for (const b of document.querySelectorAll("[data-sekme]")) b.addEventListener("click", () => {
  if (durum.sekme !== b.dataset.sekme) {
    durum.sekme = b.dataset.sekme;
    durum.sira = { alan: "onerilen", yon: -1 };
    siraSecenekleri();
  }
  ciz();
});
// Sıralama seçimi durumu günceller; çizimi aşağıdaki ortak filtre dinleyicisi yapar.
document.getElementById("f-sira").addEventListener("change", e => {
  const alan = e.target.value;
  durum.sira = { alan, yon: SIRALAR[durum.sekme][alan][2] };
});
document.getElementById("f-ara").addEventListener("input", () => durum.veri && ciz());
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

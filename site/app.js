// YouTube Radar arayüzü. Veriler yalnızca textContent ile yazılır (innerHTML'e veri konmaz).
// Yazma işlemleri (engelleme, konu araması) arkauc.js içindeki window.arkaUc üzerinden gider.
"use strict";

const KATEGORI = {
  "1": "Film ve Animasyon", "2": "Otomobil", "10": "Müzik", "15": "Hayvanlar", "17": "Spor",
  "19": "Seyahat", "20": "Oyun", "22": "Kişiler ve Bloglar", "23": "Komedi", "24": "Eğlence",
  "25": "Haber ve Politika", "26": "Nasıl Yapılır", "27": "Eğitim", "28": "Bilim ve Teknoloji",
};

const arkaUc = window.arkaUc;
const durum = { veri: null, konular: [], konu: null, sekme: "videolar", gorunum: "tablo", sira: { alan: "onerilen", yon: -1 } };

// Sıralama alanları: [etiket, değer okuyucu, varsayılan yön (-1 azalan, 1 artan)]
const VIDEO_SIRALARI = {
  onerilen: ["Önerilen sıra", null, -1],
  kat: ["Kat", v => v.kat, -1],
  izlenme: ["İzlenme", v => v.views, -1],
  normal: ["Kanal normali", v => v.normal, -1],
  yas: ["En yeni", v => v.published, -1],
};
const SIRALAR = {
  videolar: VIDEO_SIRALARI,
  konu: VIDEO_SIRALARI,
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
function $(id) { return document.getElementById(id); }

function el(etiket, ozellik, ...cocuklar) {
  const e = document.createElement(etiket);
  if (ozellik) for (const [k, v] of Object.entries(ozellik)) {
    if (k === "class") e.className = v; else if (v != null) e.setAttribute(k, v);
  }
  for (const c of cocuklar) if (c != null) e.append(c instanceof Node ? c : String(c));
  return e;
}

// Biçim ------------------------------------------------------------------

function kisa(n) {
  if (n == null) return "–";
  if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1).replace(".", ",") + "M";
  if (n >= 1e3) return Math.round(n / 1e3) + "k";
  return String(Math.round(n));
}
function katYaz(k) {
  return (k >= 10 ? Math.round(k).toLocaleString("tr-TR") : k.toFixed(1).replace(".", ",")) + "x";
}
function referansZaman() {
  return durum.sekme === "konu" && durum.konu ? durum.konu.tarih : durum.veri.guncellendi;
}
function yasGun(iso) { return (new Date(referansZaman()).getTime() - new Date(iso).getTime()) / 86400000; }
function yasYaz(iso) {
  const g = yasGun(iso);
  return g < 1 ? Math.max(1, Math.round(g * 24)) + " saat" : Math.floor(g) + " gün";
}
function tur(v) { return v.is_short ? "Short" : "Uzun"; }
function ytLink(id) { return "https://www.youtube.com/watch?v=" + encodeURIComponent(id); }
function ac(id) { window.open(ytLink(id), "_blank", "noopener"); }
function guvenliResim(u) { return u && /^https:\/\//.test(u) ? u : null; }

// "Yeni": ilk kez son taramada görülen video. Artış: bir önceki taramadan bu yana kazandığı izlenme.
function yeniMi(v) { return durum.sekme !== "konu" && !!v.ilk && v.ilk === durum.veri.guncellendi; }
function artis(v) { return durum.sekme !== "konu" && v.onceki ? v.views - v.onceki[1] : null; }

function rozetler(v) {
  const a = artis(v);
  const parcalar = [];
  if (yeniMi(v)) parcalar.push(el("span", { class: "rozet" }, "Yeni"));
  if (a > 0) parcalar.push(el("span", { class: "artis" }, "+" + kisa(a) + " son taramadan beri"));
  if (v.yeniKanal) parcalar.push(el("span", { class: "rozet" }, "Yeni kanal"));
  return parcalar.length ? el("span", { class: "rozetler" }, ...parcalar) : null;
}

// Kanal engelleme ---------------------------------------------------------
// Engellenen kanal, liste bir sonraki taramada yenilenene kadar bu tarayıcıda gizli tutulur.

function gizlilerOku() { try { return JSON.parse(hafizaOku("radar.gizli") || "{}"); } catch (e) { return {}; } }
const gizliler = gizlilerOku();
function gizlileriYaz() { hafizaYaz("radar.gizli", JSON.stringify(gizliler)); }

let bildirimZamani = null;
function bildir(metin, geriAl) {
  const kutu = $("bildirim"), geri = $("bildirim-geri");
  $("bildirim-metin").textContent = metin;
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
  arkaUc.engelEkle(id, ad).catch(e => { delete gizliler[id]; gizlileriYaz(); ciz(); bildir("Engellenemedi: " + e.message); });
  bildir(ad + " engellendi.", () => {
    delete gizliler[id];
    gizlileriYaz();
    ciz();
    arkaUc.engelKaldir(id, ad).catch(e => bildir("Geri alınamadı: " + e.message));
  });
}

function engelDugmesi(id, ad) {
  if (!arkaUc.hazir()) return null;
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

// Filtreler --------------------------------------------------------------

function filtrele(v) {
  if (gizliler[v.channel_id] !== undefined) return false;
  const ara = $("f-ara").value.trim().toLocaleLowerCase("tr");
  if (ara && !((v.title || "") + " " + (v.channel_title || "")).toLocaleLowerCase("tr").includes(ara)) return false;
  if (yasGun(v.published) > +$("f-zaman").value) return false;
  const t = $("f-tur").value, u = $("f-ulke").value, k = $("f-kategori").value;
  if (t === "short" && !v.is_short) return false;
  if (t === "uzun" && v.is_short) return false;
  if (u && (v.ulke || "").toUpperCase() !== u) return false;
  if (k && v.category_id !== k) return false;
  if ($("f-yeni").value === "yeni" && durum.sekme !== "konu" && !yeniMi(v)) return false;
  return true;
}

function secenekDoldur() {
  const hepsi = [...durum.veri.videolar, ...durum.veri.yeni_kanallar.map(k => k.en_iyi)];
  const ulkeler = [...new Set(hepsi.map(v => (v.ulke || "").toUpperCase()).filter(Boolean))].sort();
  const kategoriler = [...new Set(hepsi.map(v => v.category_id).filter(Boolean))]
    .sort((a, b) => (KATEGORI[a] || a).localeCompare(KATEGORI[b] || b, "tr"));
  for (const u of ulkeler) $("f-ulke").append(el("option", { value: u }, u));
  for (const k of kategoriler) $("f-kategori").append(el("option", { value: k }, KATEGORI[k] || ("Kategori " + k)));
}

// Hücreler ---------------------------------------------------------------

function videoHucre(v, kanalAdi) {
  const resim = guvenliResim(v.thumb);
  const baslik = el("a", { class: "video__baslik", href: ytLink(v.id), target: "_blank", rel: "noopener" }, v.title);
  baslik.addEventListener("click", e => e.stopPropagation());
  return el("td", { class: "hucre-video" }, el("div", { class: "video" },
    resim ? el("img", { class: "video__resim", src: resim, alt: "", loading: "lazy", width: "96", height: "54" })
          : el("div", { class: "video__resim" }),
    el("div", { class: "video__metin" }, baslik, el("span", { class: "video__kanal" }, kanalAdi), rozetler(v))));
}

function okuma(v) {
  if (v.kat == null) {  // konu aramasında yeni kanal: normali yok, izlenme gösterilir
    return el("div", { class: "okuma" },
      el("span", { class: "okuma__kat" }, kisa(v.views)), el("span", { class: "okuma__toplam" }, "izlenme"));
  }
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
    $("f-sira").value = alan;
    ciz();
  });
  th.append(btn);
  return th;
}

function tablo(basliklar, tbody) {
  if (arkaUc.hazir()) basliklar = [...basliklar, [el("span", { class: "visually-hidden" }, "İşlem"), "islem"]];
  return el("table", null, el("thead", null, el("tr", null, ...basliklar.map(baslikHucre))), tbody);
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
        el("span", { class: "okuma__kat" }, kisa(v.views)), el("span", { class: "okuma__toplam" }, "izlenme"))),
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
  a.append(el("div", { class: "kart__govde" }, ust, el("span", { class: "kart__baslik" }, v.title), rozetler(v), bilgi(ciftler)));
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
  if (durum.sekme !== "yeni") {
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

function csvAdi() {
  const tarih = referansZaman().slice(0, 10);
  if (durum.sekme === "konu") {
    const parca = durum.konu.konu.toLocaleLowerCase("tr").replace(/[^a-z0-9çğıöşü]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);
    return "youtube-radar-konu-" + (parca || "arama") + "-" + tarih + ".csv";
  }
  return "youtube-radar-" + (durum.sekme === "videolar" ? "videolar" : "yeni-kanallar") + "-" + tarih + ".csv";
}

function csvIndir() {
  const liste = guncelListe();
  if (!liste.length) return;
  const metin = "﻿" + csvSatirlar(liste).map(r => r.map(csvHucre).join(";")).join("\r\n") + "\r\n";
  const url = URL.createObjectURL(new Blob([metin], { type: "text/csv;charset=utf-8" }));
  const a = el("a", { href: url, download: csvAdi() });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Konu araması -----------------------------------------------------------
// İstek arkaUc.konuIste ile gider; sonuç birkaç dakika sonra konular/<id>.json olarak yayınlanır.

const BEKLEME_SINIRI_DK = 12;
let izleyici = null;

function konuSatirlari() {
  if (!durum.konu) return [];
  return [...durum.konu.videolar,
    ...durum.konu.yeni_kanallar.map(k => ({ ...k.en_iyi, channel_title: k.channel_title, kat: null, normal: null, yeniKanal: true }))];
}

async function konulariYukle() {
  try {
    const r = await fetch("konular/index.json?t=" + Date.now(), { cache: "no-store" });
    durum.konular = r.ok ? await r.json() : [];
  } catch (e) { durum.konular = []; }
  const s = $("konu-gecmis");
  s.replaceChildren(...(durum.konular.length
    ? durum.konular.map(k => el("option", { value: k.id },
        k.konu + " (" + new Date(k.tarih).toLocaleDateString("tr-TR", { day: "numeric", month: "short" }) + ")"))
    : [el("option", { value: "" }, "Henüz arama yok")]));
  s.disabled = !durum.konular.length;
  if (durum.konu) s.value = durum.konu.id;
}

async function konuSec(id) {
  if (!id) { durum.konu = null; ciz(); return; }
  try {
    const r = await fetch("konular/" + encodeURIComponent(id) + ".json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error();
    durum.konu = await r.json();
    $("konu-gecmis").value = id;
    konuDurumu(durum.konu.hata || "", !!durum.konu.hata);
  } catch (e) {
    durum.konu = null;
    konuDurumu("Bu arama yüklenemedi.", true);
  }
  ciz();
}

function konuDurumu(metin, kotu) {
  $("konu-durum").textContent = metin;
  $("konu-durum").classList.toggle("kotu", !!kotu);
}

function konuPaneliniHazirla() {
  const hazir = arkaUc.hazir();
  $("konu-metin").disabled = !hazir;
  $("konu-ara").disabled = !hazir || !!izleyici;
  $("konu-anahtar-notu").hidden = hazir;
}

async function konuAra() {
  const konu = $("konu-metin").value.trim();
  if (!konu) { konuDurumu("Önce bir konu yaz.", true); $("konu-metin").focus(); return; }
  const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
  $("konu-ara").disabled = true;
  konuDurumu("İstek gönderiliyor…");
  try {
    await arkaUc.konuIste(id, konu);
  } catch (e) {
    konuDurumu("Gönderilemedi: " + e.message + ".", true);
    $("konu-ara").disabled = false;
    return;
  }
  hafizaYaz("radar.bekleyen", JSON.stringify({ id, konu, zaman: Date.now() }));
  bekleyeniIzle();
}

function bekleyeniIzle() {
  let bekleyen;
  try { bekleyen = JSON.parse(hafizaOku("radar.bekleyen") || "null"); } catch (e) { bekleyen = null; }
  if (!bekleyen) return;
  const kontrol = async () => {
    const dk = (Date.now() - bekleyen.zaman) / 60000;
    if (dk > BEKLEME_SINIRI_DK) {
      clearInterval(izleyici); izleyici = null;
      hafizaSil("radar.bekleyen");
      konuPaneliniHazirla();
      konuDurumu("“" + bekleyen.konu + "” için sonuç gelmedi. İş kaydına bak: " + arkaUc.isKaydi(), true);
      return;
    }
    konuDurumu("“" + bekleyen.konu + "” aranıyor, " + Math.max(1, Math.round(dk)) + ". dakika. Sonuç genelde 2-4 dakikada gelir.");
    await konulariYukle();
    if (durum.konular.some(k => k.id === bekleyen.id)) {
      clearInterval(izleyici); izleyici = null;
      hafizaSil("radar.bekleyen");
      konuPaneliniHazirla();
      $("konu-metin").value = "";
      await konuSec(bekleyen.id);
      if (!durum.konu || !durum.konu.hata) konuDurumu("“" + bekleyen.konu + "” araması hazır.");
      bildir("“" + bekleyen.konu + "” araması hazır.");
    }
  };
  clearInterval(izleyici);
  izleyici = setInterval(kontrol, 15000);
  konuPaneliniHazirla();
  kontrol();
}

// Çizim ------------------------------------------------------------------

function guncelListe() {
  const liste = durum.sekme === "videolar" ? durum.veri.videolar.filter(filtrele)
    : durum.sekme === "konu" ? konuSatirlari().filter(filtrele)
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
  $("f-sira").replaceChildren(...Object.entries(SIRALAR[durum.sekme]).map(([alan, [ad]]) => el("option", { value: alan }, ad)));
  $("f-sira").value = durum.sira.alan;
}

const FILTRE_KUTULARI = ["f-tur", "f-ulke", "f-kategori", "f-ara", "f-yeni"];

function filtreleriSifirla() {
  $("f-zaman").value = "7";
  for (const id of FILTRE_KUTULARI) $(id).value = "";
  ciz();
}

function bosDurum() {
  if (durum.sekme === "konu" && !durum.konu) {
    return el("div", { class: "bos" },
      el("p", { class: "bos__ana" }, durum.konular.length ? "Bir arama seç." : "Henüz konu araması yok."),
      el("p", null, arkaUc.hazir() ? "Yukarıdaki kutuya bir konu yazıp Ara’ya bas. Örnek: ai animation, ai shorts"
                                  : "Arama için Ayarlar’dan GitHub anahtarını gir."));
  }
  if (durum.sekme === "konu" && durum.konu.hata) {
    return el("div", { class: "bos" }, el("p", { class: "bos__ana" }, "Bu arama yapılamadı."), el("p", null, durum.konu.hata));
  }
  const dar = $("f-zaman").value !== "7" || FILTRE_KUTULARI.some(id => $(id).value.trim());
  const ad = { videolar: "patlayan video", yeni: "yeni kanal", konu: "bu konuda patlayan video" }[durum.sekme];
  const kutu = el("div", { class: "bos" },
    el("p", { class: "bos__ana" }, "Bu filtrelerle " + ad + " yok."),
    el("p", null, dar ? "Filtreler listeyi daraltıyor. Son 7 güne ve tüm türlere bakabilirsin."
      : durum.sekme === "konu" ? "Bu konuda kanalının normalinin 3 katını geçen video çıkmadı. Farklı ifadeler dene."
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
  $("konu-panel").hidden = durum.sekme !== "konu";
  $("f-yeni").disabled = durum.sekme === "konu";
  const kutu = $("icerik");
  kutu.replaceChildren();
  const liste = guncelListe();
  const cizici = durum.sekme === "yeni"
    ? (durum.gorunum === "tablo" ? yeniTablo : yeniKartlar)
    : (durum.gorunum === "tablo" ? videoTablo : videoKartlar);
  $("sayac").textContent = liste.length.toLocaleString("tr-TR") + " sonuç";
  $("csv-indir").disabled = !liste.length;
  $("csv-indir").title = liste.length ? "Ekrandaki listeyi indir" : "İndirilecek sonuç yok";
  kutu.append(liste.length ? cizici(liste) : bosDurum());
}

function durumYaz(veri) {
  const t = new Date(veri.guncellendi);
  $("durum").replaceChildren(
    el("span", null, "Son tarama ", el("span", { class: "olcum" },
      t.toLocaleString("tr-TR", { dateStyle: "long", timeStyle: "short" }))),
    el("span", null, el("span", { class: "olcum" }, (veri.harcanan ?? 0).toLocaleString("tr-TR")), " birim kota"));
  if (veri.kota_bitti) $("durum").append(el("span", { class: "kotu" }, "Kota bitti, tarama eksik"));
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
  $("ornek-uyari").hidden = !ornek;
  durumYaz(veri);
  secenekDoldur();
  siraSecenekleri();
  await konulariYukle();
  if (durum.konular.length) await konuSec(durum.konular[0].id);
  konuPaneliniHazirla();
  ciz();
  bekleyeniIzle();
}

// Ayarlar ----------------------------------------------------------------

function ayarDurumu(metin, kotu) {
  $("anahtar-durum").textContent = metin;
  $("anahtar-durum").classList.toggle("kotu", !!kotu);
}

async function engelListesiCiz() {
  const ul = $("engel-listesi");
  if (!arkaUc.hazir()) { ul.replaceChildren(el("li", { class: "soluk" }, "Liste anahtar girilince görünür.")); return; }
  ul.replaceChildren(el("li", { class: "soluk" }, "Yükleniyor…"));
  try {
    const satirlar = await arkaUc.engelListesi();
    if (!satirlar.length) { ul.replaceChildren(el("li", { class: "soluk" }, "Henüz engellenen kanal yok.")); return; }
    ul.replaceChildren(...satirlar.map(s => {
      const b = el("button", { type: "button", class: "btn btn--kucuk" }, "Engeli kaldır");
      b.addEventListener("click", async () => {
        b.disabled = true;
        try {
          await arkaUc.engelKaldir(s.id, s.ad);
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

function anahtarDegisti() {
  konuPaneliniHazirla();
  if (durum.veri) ciz();
  engelListesiCiz();
}

function ayarlariAc() {
  const kayitli = arkaUc.hazir();
  $("anahtar").value = "";
  $("anahtar").placeholder = kayitli ? "Kayıtlı anahtar var, değiştirmek için yenisini yapıştır" : "github_pat_…";
  $("anahtar-sil").disabled = !kayitli;
  ayarDurumu(kayitli ? "Anahtar kayıtlı. Engelleme ve konu araması açık." : "");
  $("ayarlar").showModal();
  engelListesiCiz();
}

async function anahtarKaydet() {
  const deger = $("anahtar").value.trim();
  if (!deger) { ayarDurumu("Önce anahtarı yapıştır.", true); return; }
  const eski = hafizaOku("radar.anahtar");
  hafizaYaz("radar.anahtar", deger);
  ayarDurumu("Deneniyor…");
  try {
    await arkaUc.dene();
    $("anahtar").value = "";
    $("anahtar-sil").disabled = false;
    ayarDurumu("Anahtar çalışıyor. Engelleme ve konu araması açıldı.");
    anahtarDegisti();
  } catch (e) {
    if (eski) hafizaYaz("radar.anahtar", eski); else hafizaSil("radar.anahtar");
    ayarDurumu("Olmadı: " + e.message + ".", true);
  }
}

// Olaylar ----------------------------------------------------------------

$("ayarlar-ac").addEventListener("click", ayarlariAc);
$("anahtar-kaydet").addEventListener("click", anahtarKaydet);
$("anahtar-sil").addEventListener("click", () => {
  hafizaSil("radar.anahtar");
  $("anahtar-sil").disabled = true;
  ayarDurumu("Anahtar bu tarayıcıdan silindi.");
  anahtarDegisti();
});
$("konu-form").addEventListener("submit", e => { e.preventDefault(); konuAra(); });
$("konu-gecmis").addEventListener("change", e => konuSec(e.target.value));

durum.gorunum = hafizaOku("radar.gorunum") === "kart" ? "kart" : "tablo";
for (const b of document.querySelectorAll("[data-sekme]")) b.addEventListener("click", () => {
  if (durum.sekme !== b.dataset.sekme) {
    durum.sekme = b.dataset.sekme;
    durum.sira = { alan: "onerilen", yon: -1 };
    if (durum.sekme === "konu") $("f-zaman").value = "7";  // konu araması son 7 günü kapsar
    siraSecenekleri();
  }
  if (durum.veri) ciz();
});
// Sıralama seçimi durumu günceller; çizimi aşağıdaki ortak filtre dinleyicisi yapar.
$("f-sira").addEventListener("change", e => {
  const alan = e.target.value;
  durum.sira = { alan, yon: SIRALAR[durum.sekme][alan][2] };
});
$("f-ara").addEventListener("input", () => durum.veri && ciz());
for (const b of document.querySelectorAll("[data-gorunum]")) b.addEventListener("click", () => {
  durum.gorunum = b.dataset.gorunum; hafizaYaz("radar.gorunum", durum.gorunum); if (durum.veri) ciz();
});
for (const s of document.querySelectorAll(".filtreler select")) s.addEventListener("change", () => durum.veri && ciz());
$("csv-indir").addEventListener("click", () => durum.veri && csvIndir());
yukle().catch(() => {
  $("durum").textContent = "Veri yüklenemedi.";
  $("icerik").replaceChildren(el("div", { class: "bos" },
    el("p", { class: "bos__ana" }, "Liste yüklenemedi."),
    el("p", null, "Bağlantını kontrol edip sayfayı yenile. Sorun sürerse liste dosyası henüz yayınlanmamış olabilir.")));
});

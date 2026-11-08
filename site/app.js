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
  return String(n);
}
function katYaz(k) { return (k >= 10 ? Math.round(k) : k.toFixed(1).replace(".", ",")) + "x"; }

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

function videoTablo(liste) {
  const tbody = el("tbody");
  for (const v of liste) {
    const tr = el("tr", null,
      el("td", { class: "kat" }, katYaz(v.kat)),
      el("td", { class: "baslik" }, v.title),
      el("td", null, v.channel_title),
      el("td", { class: "sayi" }, kisa(v.views)),
      el("td", { class: "sayi" }, kisa(v.normal)),
      el("td", null, yasYaz(v.published)),
      el("td", null, tur(v)));
    tr.addEventListener("click", () => ac(v.id));
    tbody.append(tr);
  }
  return el("div", { class: "tablo-kutu" }, el("table", null,
    el("thead", null, el("tr", null, ...["Kat", "Video", "Kanal", "İzlenme", "Normali", "Yaş", "Tür"].map(b => el("th", null, b)))),
    tbody));
}

function yeniTablo(liste) {
  const tbody = el("tbody");
  for (const k of liste) {
    const v = k.en_iyi;
    const tr = el("tr", null,
      el("td", null, k.channel_title),
      el("td", { class: "baslik" }, v.title),
      el("td", { class: "sayi kat" }, kisa(v.views)),
      el("td", null, k.kanal_yasi_gun == null ? "–" : Math.floor(k.kanal_yasi_gun) + " gün"),
      el("td", { class: "sayi" }, k.video_sayisi ?? "–"),
      el("td", null, yasYaz(v.published)),
      el("td", null, tur(v)));
    tr.addEventListener("click", () => ac(v.id));
    tbody.append(tr);
  }
  return el("div", { class: "tablo-kutu" }, el("table", null,
    el("thead", null, el("tr", null, ...["Kanal", "En iyi video", "İzlenme", "Kanal yaşı", "Video", "Yaş", "Tür"].map(b => el("th", null, b)))),
    tbody));
}

function kart(v, ust, alt) {
  const a = el("a", { class: "kart", href: ytLink(v.id), target: "_blank", rel: "noopener" });
  if (v.thumb && /^https:\/\//.test(v.thumb)) a.append(el("img", { src: v.thumb, alt: "", loading: "lazy" }));
  else a.append(el("div", { class: "resimsiz" }));
  a.append(el("div", { class: "govde" }, ust, el("div", { class: "baslik" }, v.title), el("div", { class: "alt" }, alt)));
  return a;
}

function videoKartlar(liste) {
  return el("div", { class: "kartlar" }, ...liste.map(v => kart(v,
    el("div", { class: "ust-satir" }, el("span", { class: "kat" }, katYaz(v.kat)), " · " + kisa(v.views) + " izlenme (normali " + kisa(v.normal) + ")"),
    v.channel_title + " · " + yasYaz(v.published) + " · " + tur(v))));
}

function yeniKartlar(liste) {
  return el("div", { class: "kartlar" }, ...liste.map(k => kart(k.en_iyi,
    el("div", { class: "ust-satir" }, el("span", { class: "kat" }, kisa(k.en_iyi.views)), " izlenme · kanal " +
      (k.kanal_yasi_gun == null ? "?" : Math.floor(k.kanal_yasi_gun)) + " günlük"),
    k.channel_title + " · " + (k.video_sayisi ?? "?") + " video · " + tur(k.en_iyi))));
}

function ciz() {
  for (const b of document.querySelectorAll("[data-sekme]")) b.classList.toggle("aktif", b.dataset.sekme === durum.sekme);
  for (const b of document.querySelectorAll("[data-gorunum]")) b.classList.toggle("aktif", b.dataset.gorunum === durum.gorunum);
  const kutu = document.getElementById("icerik");
  kutu.replaceChildren();
  let liste, cizici;
  if (durum.sekme === "videolar") {
    liste = durum.veri.videolar.filter(filtrele);
    cizici = durum.gorunum === "tablo" ? videoTablo : videoKartlar;
  } else {
    liste = durum.veri.yeni_kanallar.filter(k => filtrele(k.en_iyi));
    cizici = durum.gorunum === "tablo" ? yeniTablo : yeniKartlar;
  }
  document.getElementById("sayac").textContent = liste.length + " sonuç";
  kutu.append(liste.length ? cizici(liste) : el("div", { class: "bos" }, "Bu filtrelerle sonuç yok."));
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
  const t = new Date(veri.guncellendi);
  document.getElementById("durum").textContent = "Son güncelleme: " +
    t.toLocaleString("tr-TR", { dateStyle: "long", timeStyle: "short" }) +
    " · " + (veri.harcanan ?? 0).toLocaleString("tr-TR") + " birim kota" +
    (veri.kota_bitti ? " · kota bitti, tarama eksik" : "");
  secenekDoldur();
  ciz();
}

durum.gorunum = hafizaOku("radar.gorunum") === "kart" ? "kart" : "tablo";
for (const b of document.querySelectorAll("[data-sekme]")) b.addEventListener("click", () => { durum.sekme = b.dataset.sekme; ciz(); });
for (const b of document.querySelectorAll("[data-gorunum]")) b.addEventListener("click", () => {
  durum.gorunum = b.dataset.gorunum; hafizaYaz("radar.gorunum", durum.gorunum); ciz();
});
for (const s of document.querySelectorAll(".filtreler select")) s.addEventListener("change", () => durum.veri && ciz());
yukle().catch(() => { document.getElementById("durum").textContent = "Veri yüklenemedi."; });

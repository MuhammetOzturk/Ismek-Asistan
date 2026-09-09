"""İSMEK sorgu API'sinin tek sayfa web arayüzü — eğitim Gün 3.

Sayfa JSON uç noktalarını (GET /kurslar, GET /ozet) fetch ile çağırır;
filtre → tablo render'ı tamamen istemci tarafında. API'den ayrı süreç
çalışmaz: api.py bu sabiti GET / rotasına bağlar — tek sunucu, tek port.

Uygulama kuralı (rag-web-panel-hibrit): HTML gövde .format()'lanmaz;
süslü parantezler CSS/JS'ten gelir. Sayfa içinde harici kaynak (CDN)
yok — headless doğrulama ve Docker'da offline açılır.
"""

SAYFA = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>İSMEK Kurs Arama</title>
<style>
  :root { --yesil: #0a7d55; --acik-ar: #e6f4ee; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         background: #f5f6f8; color: #1c2733; }
  header { background: var(--yesil); color: #fff; padding: 18px 28px; }
  header h1 { margin: 0; font-size: 1.45rem; letter-spacing: .3px; }
  header p { margin: 4px 0 0; opacity: .85; font-size: .92rem; }
  main { max-width: 1100px; margin: 0 auto; padding: 22px 20px 40px; }

  #ozet { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
  .kutu { background: #fff; border: 1px solid #dfe5ea; border-radius: 10px;
          padding: 8px 14px; font-size: .85rem; }
  .kutu b { display: block; font-size: 1.25rem; color: var(--yesil); }

  form { display: flex; gap: 10px; flex-wrap: wrap; background: #fff;
         border: 1px solid #dfe5ea; border-radius: 12px; padding: 14px; }
  form input, form select { flex: 1 1 150px; padding: 9px 11px; font-size: .95rem;
         border: 1px solid #c8d1d8; border-radius: 8px; }
  #btn { flex: 0 0 auto; padding: 9px 26px; border: 0; border-radius: 8px;
         background: var(--yesil); color: #fff; font-size: .95rem; cursor: pointer; }
  #btn:disabled { opacity: .6; cursor: wait; }

  #ornekler { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 2px 4px; }
  #ornekler button { padding: 6px 13px; font-size: .85rem; border-radius: 999px;
         border: 1px solid #bcd8cb; background: var(--acik-ar); color: #0a5c40;
         cursor: pointer; }
  #ornekler button:hover { background: #d3ecdf; }

  #sonuc { margin-top: 20px; }
  #sonuc h2 { font-size: 1.05rem; margin: 0 0 10px; }
  table { width: 100%; border-collapse: collapse; background: #fff;
          border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(16,42,67,.08); }
  th { background: #eef2f5; text-align: left; font-size: .8rem; text-transform: uppercase;
       letter-spacing: .4px; color: #51606e; }
  th, td { padding: 10px 12px; border-bottom: 1px solid #e8edf1; font-size: .92rem; }
  tr:last-child td { border-bottom: 0; }
  td .prog { font-weight: 600; }
  td .kod { color: #6b7a87; font-size: .8rem; }
  .pil { display: inline-block; padding: 2px 10px; border-radius: 999px;
         font-size: .8rem; white-space: nowrap; }
  .pil.acik { background: var(--acik-ar); color: #0a5c40; border: 1px solid #a9d6c0; }
  .pil.kapali { background: #f2f2f2; color: #7a8692; border: 1px solid #d9dee3; }

  #hata { margin-top: 18px; padding: 12px 16px; border-radius: 10px;
          background: #fdecec; border: 1px solid #f0b7b7; color: #9b2626; }
  #bos { margin-top: 18px; padding: 12px 16px; border-radius: 10px;
         background: #fff; border: 1px dashed #c8d1d8; color: #51606e; }
  footer { max-width: 1100px; margin: 0 auto; padding: 0 20px 30px;
           color: #7a8692; font-size: .82rem; }
  #nlbtn { padding: 9px 26px; border: 0; border-radius: 8px; background: #0f5132;
          color: #fff; font-size: .95rem; cursor: pointer; }
  #nlbtn:disabled { opacity: .6; cursor: wait; }
  #nlcips { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 2px 0; }
  #nlcips button { padding: 6px 13px; font-size: .85rem; border-radius: 999px;
          border: 1px solid #bcd8cb; background: #fff; color: #0a5c40; cursor: pointer; }
  #nlcips button:hover { background: var(--acik-ar); }
  #nlsonuc { margin-top: 14px; display: grid; gap: 12px; }
  .nl-panel { background: #fff; border: 1px solid #dfe5ea; border-radius: 12px;
          padding: 14px 16px; }
  .nl-panel h3 { margin: 0 0 8px; font-size: .8rem; text-transform: uppercase;
          letter-spacing: .4px; color: #51606e; }
  #nlcevap { white-space: pre-wrap; font-size: .98rem; line-height: 1.55; }
  .nl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  #nlkanit { margin: 0; padding-left: 16px; font-size: .88rem; }
  #nlkanit li { margin: 5px 0; }
  .skor { display: inline-block; height: 6px; border-radius: 3px; background: var(--yesil);
          vertical-align: middle; margin-right: 6px; }
  #nlperf { margin: 0; white-space: pre-wrap; font-size: .82rem; color: #51606e; }
  #nlhata { margin-top: 12px; padding: 12px 16px; border-radius: 10px;
          background: #fdecec; border: 1px solid #f0b7b7; color: #9b2626; }


</style>
</head>
<body>
<header>
  <h1>İSMEK Kurs Arama</h1>
  <p>İstanbul'daki İSMEK kursları — RAG asistan: doğal dil sorusu + yapısal sorgu</p>
</header>
<main>
  <section id="ozet" aria-label="Veri özeti"></section>

  <section id="sohbet">
    <form id="nlform">
      <input id="nlsoru" type="text"
             placeholder="Doğal dilde sor: Kayda açık pastacılık kursu hangi merkezde?">
      <button id="nlbtn" type="submit">Sor</button>
    </form>
    <div id="nlcips">
      <button type="button" data-soru="Butik Çikolata Hazırlama programının amacı nedir, ön koşulu var mı?">Butik Çikolata — amaç</button>
      <button type="button" data-soru="Kayda açık pastacılık kursu hangi merkezde, ne zaman başlıyor?">Açık pastacılık kursu</button>
      <button type="button" data-soru="Uzaktan eğitimle verilen kurslar hangileri?">Uzaktan eğitim kursları</button>
      <button type="button" data-soru="Kahve Yapımı kursuna kayıt olabilir miyim?">Kahve kursu kayıt durumu</button>
    </div>
    <section id="nlhata" hidden></section>
    <section id="nlsonuc" hidden>
      <div class="nl-panel"><h3>Yanıt</h3><div id="nlcevap"></div></div>
      <div class="nl-grid">
        <div class="nl-panel"><h3>Vektör kanıtları (e5 kosinüs)</h3><ul id="nlkanit"></ul></div>
        <div class="nl-panel"><h3>Performans</h3><pre id="nlperf"></pre></div>
      </div>
    </section>
  </section>

  <form id="form">
    <input id="arama" type="text" placeholder="Program adı (ör. pasta)">
    <input id="ilce" type="text" placeholder="İlçe (ör. Bahçelievler)">
    <input id="bolum" type="text" placeholder="Bölüm (ör. Pastacılık)">
    <select id="kayit">
      <option value="">Kayıt: Hepsi</option>
      <option value="acik">Kayıt: Açık</option>
      <option value="kapali">Kayıt: Kapalı</option>
    </select>
    <button id="btn" type="submit">Ara</button>
  </form>

  <div id="ornekler">
    <button type="button" data-bolum="Pastacılık" data-kayit="acik">Pastacılık — kaydı açık</button>
    <button type="button" data-ilce="Şişli">Şişli kursları</button>
    <button type="button" data-kayit="acik">Kaydı açık tüm kurslar</button>
  </div>

  <section id="sonuc" hidden>
    <h2>Sonuçlar (<span id="sayi">0</span> kurs)</h2>
    <table>
      <thead>
        <tr><th>Program</th><th>Bölüm</th><th>Merkez</th><th>İlçe</th>
            <th>Veriliş</th><th>Başlangıç</th><th>Kontenjan</th><th>Kayıt</th></tr>
      </thead>
      <tbody id="govde"></tbody>
    </table>
  </section>

  <section id="bos" hidden>Uygun kurs bulunamadı — filtreleri gevşetip tekrar deneyin.</section>
  <section id="hata" hidden></section>
</main>
<footer>
  Veri kaynağı: veri/kayitlar/*.json (topla.py koşumu) · Uç noktalar:
  GET /health, GET /ozet, GET /kurslar, GET /programlar/&lt;brans_code&gt;, POST /api/soru
</footer>
<script>
"use strict";
const $ = (id) => document.getElementById(id);

function kacir(metin) {
  return String(metin).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function hataGoster(metin) {
  const h = $("hata");
  h.textContent = metin;
  h.hidden = false;
}

function tarih(k) {
  return String(k ?? "").slice(0, 10);
}

function tabloDoldur(satirlar) {
  $("hata").hidden = true;
  $("bos").hidden = satirlar.length > 0;
  $("sonuc").hidden = satirlar.length === 0;
  $("sayi").textContent = String(satirlar.length);
  const govde = $("govde");
  govde.textContent = "";
  for (const s of satirlar) {
    const tr = document.createElement("tr");
    const pil = s.kayit_acik
      ? '<span class="pil acik">Açık · ' + kacir(s.kayit_durumu) + "</span>"
      : '<span class="pil kapali">Kapalı · ' + kacir(s.kayit_durumu) + "</span>";
    tr.innerHTML =
      '<td><span class="prog">' + kacir(s.program) + '</span><br>' +
      '<span class="kod">BransCode ' + s.brans_code + "</span></td>" +
      "<td>" + kacir(s.bolum) + "</td>" +
      "<td>" + kacir(s.merkez) + "</td>" +
      "<td>" + kacir(s.ilce) + "</td>" +
      "<td>" + kacir(s.verilis) + "</td>" +
      "<td>" + tarih(s.baslangic) + "</td>" +
      "<td>" + (s.kontenjan ?? "—") + "</td>" +
      "<td>" + pil + "</td>";
    govde.appendChild(tr);
  }
}

async function sorgula() {
  const q = new URLSearchParams();
  for (const id of ["arama", "ilce", "bolum"]) {
    const v = $(id).value.trim();
    if (v) q.set(id, v);
  }
  const k = $("kayit").value;
  if (k) q.set("kayit", k);

  const btn = $("btn");
  btn.disabled = true;
  btn.textContent = "Aranıyor…";
  try {
    const r = await fetch("/kurslar?" + q.toString());
    if (!r.ok) {
      hataGoster("API hatası (" + r.status + "): " + (await r.text()));
      return;
    }
    tabloDoldur(await r.json());
  } catch (e) {
    hataGoster("Bağlantı hatası: " + e);
  } finally {
    btn.disabled = false;
    btn.textContent = "Ara";
  }
}

$("form").addEventListener("submit", (olay) => {
  olay.preventDefault();
  sorgula();
});

for (const cip of document.querySelectorAll("#ornekler button")) {
  cip.addEventListener("click", () => {
    $("arama").value = "";
    $("ilce").value = "";
    $("bolum").value = "";
    $("kayit").value = "";
    for (const [anahtar, deger] of Object.entries(cip.dataset)) {
      if (anahtar === "kayit") $("kayit").value = deger;
      else $(anahtar).value = deger;
    }
    sorgula();
  });
}

// ---- Gün 3: doğal dil sorusu → POST /api/soru (RAG hattı) ----
async function nlSor() {
  const soru = $("nlsoru").value.trim();
  if (!soru) return;
  const btn = $("nlbtn");
  btn.disabled = true;
  btn.textContent = "İşleniyor…";
  $("nlhata").hidden = true;
  $("nlsonuc").hidden = true;
  try {
    const r = await fetch("/api/soru", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ soru }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || r.status);
    nlGoster(d);
  } catch (e) {
    $("nlhata").textContent = "Hata: " + e.message;
    $("nlhata").hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Sor";
  }
}

function nlGoster(d) {
  $("nlsonuc").hidden = false;
  $("nlcevap").innerHTML = kacir(d.yanit).split("**")
    .map((p, i) => i % 2 ? "<b>" + p + "</b>" : p).join("");
  $("nlkanit").textContent = "";
  for (const k of d.vektor.kanitlar) {
    const li = document.createElement("li");
    li.innerHTML = '<span class="skor" style="width:' + Math.round(k.skor * 60) + 'px"></span>'
      + k.skor.toFixed(3) + " — " + kacir(k.program)
      + ' <span class="kod">BransCode ' + k.brans_code + "</span>";
    $("nlkanit").appendChild(li);
  }
  const m = d.maliyet;
  $("nlperf").textContent =
    "çözümleyici: " + d.filtre_sure.toFixed(2) + " sn (" + m.cozumleyici.giris + "+"
    + m.cozumleyici.cikis + " tok, $" + m.cozumleyici.usd.toFixed(6) + ")\\n"
    + "vektör: " + d.vektor.sure.toFixed(2) + " sn (" + d.vektor.kanitlar.length + " kanıt)\\n"
    + "sentez: " + d.sentez_sure.toFixed(2) + " sn (" + m.sentez.giris + "+"
    + m.sentez.cikis + " tok, $" + m.sentez.usd.toFixed(6) + ")\\n"
    + "yapısal: " + d.yapisal_sure.toFixed(3) + " sn (" + d.yapisal.sayi + " kurs)\\n"
    + "TOPLAM: " + d.toplam_sure.toFixed(2) + " sn · $" + m.toplam.usd.toFixed(6) + "\\n"
    + "filtre: " + JSON.stringify(d.filtre);
  // Çözümleyicinin çıkardığı filtre yapısal forma da yazılır: hat görünür olur.
  $("arama").value = d.filtre.arama_terimi || "";
  $("ilce").value = d.filtre.ilce || "";
  $("bolum").value = "";
  $("kayit").value = d.filtre.kayit_durumu || "";
  tabloDoldur(d.yapisal.satirlar);
}

$("nlform").addEventListener("submit", (olay) => {
  olay.preventDefault();
  nlSor();
});

for (const cip of document.querySelectorAll("#nlcips button")) {
  cip.addEventListener("click", () => {
    $("nlsoru").value = cip.dataset.soru;
    nlSor();
  });
}

(async () => {
  try {
    const o = await (await fetch("/ozet")).json();
    const kutular = [
      ["Program", o.program_sayisi], ["Kurs", o.kurs_sayisi],
      ["Kaydı açık", o.acik_kurs], ["Kaydı kapalı", o.kapali_kurs],
      ["İlçe", o.ilce_sayisi],
    ];
    $("ozet").textContent = "";
    for (const [ad, deger] of kutular) {
      const d = document.createElement("div");
      d.className = "kutu";
      d.innerHTML = "<b>" + kacir(deger) + "</b>" + kacir(ad);
      $("ozet").appendChild(d);
    }
  } catch (e) {
    hataGoster("Özet yüklenemedi: " + e);
  }
})();

(async () => {
  // Derin bağlantı: ?soru=.. (RAG) veya ?arama=..&ilce=..&bolum=..&kayit=acik — doldurup koştur.
  const p = new URLSearchParams(location.search);
  if (![...p.keys()].length) return;
  if (p.get("soru")) { $("nlsoru").value = p.get("soru"); nlSor(); return; }
  for (const id of ["arama", "ilce", "bolum"]) if (p.get(id)) $(id).value = p.get(id);
  if (p.get("kayit")) $("kayit").value = p.get("kayit");
  sorgula();
})();
</script>
</body>
</html>
"""
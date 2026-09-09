"""İSMEK sorgu API — eğitim Gün 1 Lab 2-3 İSMEK hedefi (eğitmen çözümü).

Çalıştırma (repo kökünden): uvicorn app.api:app --port 8000
Sağlık uç noktası: GET /health — docker-compose healthcheck ve CI bekliyor.
Veri: ISMEK_VERI_DIR env (default <repo>/veri; Docker/CI: veri/ornek fixture).

Gün 3: GET / web arayüzü + POST /api/soru RAG hattı (çözümleyici → yapısal
sorgu + e5 vektör araması → kanıtlı LLM sentezi) aynı süreçte.
"""
import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.sorgu import istatistik, sorgula, yukle
from app.web import SAYFA
from bot.istemci import TOKERLEK
from bot.rag import MODEL_ADI, ara, hazirla, sentezle
from bot.sorgu_cozumleyici import coz

app = FastAPI(title="İSMEK Sorgu API", version="0.1.0")

# Import anında bir kez yüklenir: fixture/durum sabit, testler deterministik.
KAYITLAR = yukle()
# e5 modeli + vektör indeksi başlangıçta yüklenir — ilk istek beklemesin.
hazirla()

@app.get("/", response_class=HTMLResponse)
def ana_sayfa() -> str:
    """Gün 3 web arayüzü — tek sayfa; sorguları /kurslar'a fetch'ler."""
    return SAYFA


@app.get("/health")
def health() -> dict:
    """Orkestrasyon ve CI'ın beklediği canlılık uç noktası."""
    return {"status": "ok", "program": len(KAYITLAR), "model": MODEL_ADI}


@app.get("/ozet")
def ozet() -> dict:
    """Koşum istatistiği — /health'in ötesinde veri tazeliği görünümü."""
    return istatistik(KAYITLAR)


@app.get("/kurslar")
def kurslari_listele(
    ilce: str | None = None,
    kayit: str | None = Query(default=None, pattern="^(acik|kapali)$"),
    bolum: str | None = None,
    verilis: str | None = None,
    arama: str | None = None,
    limit: int | None = Query(default=None, ge=1),
) -> list[dict]:
    """Yapısal sorgu — ilçe/tarih/kayıt-durumu filtreleri (H2)."""
    kayit_acik = {"acik": True, "kapali": False}.get(kayit)
    return sorgula(
        KAYITLAR, ilce=ilce, kayit_acik=kayit_acik, bolum=bolum,
        verilis=verilis, arama=arama, limit=limit,
    )


@app.get("/programlar/{brans_code}")
def program(brans_code: int) -> dict:
    """Tek programın tam kaydı (amaç, koşullar, kurslar — RAG kanıt kaynağı)."""
    for kayit in KAYITLAR:
        if kayit["brans_code"] == brans_code:
            return kayit
    raise HTTPException(status_code=404, detail=f"program yok: {brans_code}")


# ---- Gün 3 RAG: doğal dil sorusu → hibrit yanıt ----------------------------

YAPISAL_LIMIT = 30  # sayfada gösterilen satır sınırı; sayı tam sayılır
YAPISAL_ALANLAR = ("brans_code", "program", "bolum", "merkez", "ilce",
                   "baslangic", "bitis", "kayit_durumu", "kayit_acik",
                   "verilis", "kontenjan")


def _maliyet_delta(oncesi: dict) -> dict:
    """chat() sonrası TOKERLEK farkı — aşama başına token/maliyet muhasebesi."""
    return {
        "giris": TOKERLEK["giris"] - oncesi["giris"],
        "cikis": TOKERLEK["cikis"] - oncesi["cikis"],
        "usd": TOKERLEK["usd"] - oncesi["usd"],
    }


@app.post("/api/soru")
def soru_cevapla(govde: dict) -> dict:
    """Doğal dil sorusu → RAG hattı: çözümleyici → yapısal + vektör → sentez.

    Çözümleyici çıktısı (filtre) asla kullanıcıya içerik olarak gösterilmez;
    yalnız yapısal katmana beslenir (guardrail) ve şeffaflık için yanıtla döner.
    """
    soru = (govde or {}).get("soru", "").strip()
    if not soru:
        raise HTTPException(status_code=422, detail="'soru' alanı boş olamaz")

    basla = time.perf_counter()

    # 1) LLM sorgu çözümleyici → JSON filtre
    once = dict(TOKERLEK)
    try:
        filtre = coz(soru)
    except RuntimeError as hata:
        raise HTTPException(status_code=502, detail=f"çözümleyici: {hata}") from hata
    filtre_sure = time.perf_counter() - basla
    cozumleyici_maliyet = _maliyet_delta(once)

    # 2) yapısal sorgu — kayıt durumu/tarih/kontenjan tek doğruluk kaynağı
    yapi_basla = time.perf_counter()
    satirlar = sorgula(
        KAYITLAR,
        ilce=filtre["ilce"],
        kayit_acik={"acik": True, "kapali": False}.get(filtre["kayit_durumu"]),
        verilis=filtre["verilis"],
        arama=filtre["arama_terimi"] or None,
    )
    yapisal_sure = time.perf_counter() - yapi_basla

    # 3) vektör arama — yalnız statik içerik kanıtı
    kanitlar, vektor_sure = ara(soru, k=5)

    # 4) sentez — kanıt + güncel yapısal sonuç birlikte
    sen_basla = time.perf_counter()
    once = dict(TOKERLEK)
    try:
        yanit = sentezle(soru, kanitlar, satirlar)
    except RuntimeError as hata:
        raise HTTPException(status_code=502, detail=f"sentez: {hata}") from hata
    sentez_sure = time.perf_counter() - sen_basla
    sentez_maliyet = _maliyet_delta(once)

    toplam = {
        "giris": cozumleyici_maliyet["giris"] + sentez_maliyet["giris"],
        "cikis": cozumleyici_maliyet["cikis"] + sentez_maliyet["cikis"],
        "usd": cozumleyici_maliyet["usd"] + sentez_maliyet["usd"],
    }
    return {
        "soru": soru,
        "filtre": filtre,
        "filtre_sure": round(filtre_sure, 3),
        "yapisal": {
            "sayi": len(satirlar),
            "satirlar": [{a: s[a] for a in YAPISAL_ALANLAR}
                         for s in satirlar[:YAPISAL_LIMIT]],
        },
        "yapisal_sure": round(yapisal_sure, 3),
        "vektor": {
            "sure": round(vektor_sure, 3),
            "kanitlar": [{a: k[a] for a in ("skor", "program", "brans_code",
                                            "dosya", "kaynak_url")}
                         for k in kanitlar],
        },
        "yanit": yanit,
        "sentez_sure": round(sentez_sure, 3),
        "toplam_sure": round(time.perf_counter() - basla, 3),
        "maliyet": {"cozumleyici": cozumleyici_maliyet, "sentez": sentez_maliyet,
                    "toplam": toplam},
    }
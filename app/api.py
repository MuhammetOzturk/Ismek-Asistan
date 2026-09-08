"""İSMEK sorgu API — eğitim Gün 1 Lab 2-3 İSMEK hedefi (eğitmen çözümü).

Çalıştırma (repo kökünden): uvicorn app.api:app --port 8000
Sağlık uç noktası: GET /health — docker-compose healthcheck ve CI bekliyor.
Veri: ISMEK_VERI_DIR env (default <repo>/veri; Docker/CI: veri/ornek fixture).
"""
from fastapi import FastAPI, HTTPException, Query

from app.sorgu import istatistik, sorgula, yukle

app = FastAPI(title="İSMEK Sorgu API", version="0.1.0")

# Import anında bir kez yüklenir: fixture/durum sabit, testler deterministik.
KAYITLAR = yukle()


@app.get("/health")
def health() -> dict:
    """Orkestrasyon ve CI'ın beklediği canlılık uç noktası."""
    return {"status": "ok"}


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
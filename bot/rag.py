"""İSMEK RAG katmanı — e5 vektör araması (ChromaDB) + kanıtlı LLM sentezi (H3).

Kural (anlatim.md §9 / README mimari): kayıt durumu, tarih, kontenjan gibi
DİNAMİK alanlar vektör mağazasına konmaz — onlar app/sorgu.py yapısal
katmanından gelir; burada yalnız statik içerik (amaç, koşullar, sınav,
malzeme) aranır.

e5 prefix kuralı (alistirmalar.md Alıştırma 7): belgeye "passage: ", soruya
"query: " — prefix unutulursa kalite düşer.

İndeks: veri/markdown/*.md gövdeleri, tek vektör/belge (e5-small 512 token
penceresi, uzun gövde kırpılır). Vektörler ChromaDB kalıcı koleksiyonunda
(bot/cikti/chroma) tutulur; belge kümesi değişince yeniden kurulur.

Kullanım:
    python bot/rag.py --kur                    # indeksi kur/kontrol et
    python bot/rag.py --soru "Butik Çikolata Hazırlama amacı ne?"
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bot.istemci import chat  # noqa: E402

MODEL_ADI = "intfloat/multilingual-e5-small"
CHROMA_YOLU = REPO / "bot" / "cikti" / "chroma"
KOLEKSIYON_ADI = "ismek-markdown"
MARKDOWN_DIR = REPO / "veri" / "markdown"

KANIT_SINIRI = 1200  # sentez istemine giren belge başına karakter

SISTEM = """Sen İSMEK (İBB Enstitü) eğitim asistanısın. Yalnızca sana verilen kanıt \
belgelerinden yanıt ver.
Kurallar:
1. Kanıt soruyu tam karşılamıyorsa eldeki kanıtla yanıtla, karşılanmayan kısmı açıkça belirt; \
hiç kanıt yoksa "Bu konuda elimde yeterli kanıt yok" de — asla uydurma.
2. Kanıtlardaki kurs tabloları eski çekimdir; kayıt durumu, tarih ve kontenjan \
sorularında yalnız sana verilen güncel yapısal sorgu sonuçlarına dayan.
3. Adını andığın her programın yanına [BransCode N] referansı yaz.
4. Türkçe, kısa ve net yanıt ver."""

_model = None
_koleksiyon = None
_istemci = None


def _model_yukle():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_ADI)
    return _model


def _koleksiyon_kur(iz: str):
    global _istemci, _koleksiyon
    if _istemci is None:
        import chromadb
        from chromadb.config import Settings

        _istemci = chromadb.PersistentClient(
            path=str(CHROMA_YOLU), settings=Settings(anonymized_telemetry=False)
        )
    _koleksiyon = _istemci.get_or_create_collection(
        KOLEKSIYON_ADI,
        metadata={"hnsw:space": "cosine", "iz": iz, "model": MODEL_ADI},
    )
    return _koleksiyon


def belgeleri_yukle() -> list[dict]:
    """veri/markdown/*.md → {brans_code, program, kaynak_url, govde} (frontmatter ayrıştırılmış)."""
    belgeler = []
    for yol in sorted(MARKDOWN_DIR.glob("*.md")):
        metin = yol.read_text(encoding="utf-8")
        parcalar = metin.split("---\n", 2)
        front, govde = parcalar[1], parcalar[2] if len(parcalar) > 2 else ""
        alanlar = {}
        for satir in front.strip().splitlines():
            if ":" in satir:
                anahtar, _, deger = satir.partition(":")
                alanlar[anahtar.strip()] = deger.strip().strip('"')
        belgeler.append({
            "brans_code": int(alanlar["brans_code"]),
            "program": alanlar.get("program", ""),
            "kaynak_url": alanlar.get("kaynak_url", ""),
            "dosya": yol.name,
            "govde": govde.strip(),
        })
    return belgeler


def _karmas(belgeler: list[dict]) -> str:
    """Belge kümesi parmak izi — count değil, içerik değişimini de yakalar."""
    iz = "\n".join(f"{b['dosya']}:{b['govde'][:64]}" for b in belgeler)
    return hashlib.md5(iz.encode()).hexdigest()


def indeksi_kur(force: bool = False) -> tuple[list[dict], object]:
    """markdown gövdelerini 'passage: ' prefix'iyle embed edip Chroma'ya yazar."""
    belgeler = belgeleri_yukle()
    iz = _karmas(belgeler)
    if _koleksiyon is None:
        _koleksiyon_kur(iz)
    kol = _koleksiyon
    if (
        not force
        and kol.count() == len(belgeler)
        and kol.metadata.get("iz") == iz
        and kol.metadata.get("model") == MODEL_ADI
    ):
        return belgeler, kol
    _istemci.delete_collection(KOLEKSIYON_ADI)
    kol = _koleksiyon_kur(iz)
    model = _model_yukle()
    emb = model.encode(
        ["passage: " + b["govde"] for b in belgeler],
        normalize_embeddings=True, batch_size=64, show_progress_bar=False,
    ).astype(np.float32)
    kol.add(
        ids=[b["dosya"] for b in belgeler],
        documents=[b["govde"] for b in belgeler],
        metadatas=[
            {"brans_code": b["brans_code"], "program": b["program"],
             "kaynak_url": b["kaynak_url"], "dosya": b["dosya"]}
            for b in belgeler
        ],
        embeddings=emb,
    )
    return belgeler, kol


def hazirla() -> None:
    """İndeksi + modeli yükle — sunucu başlangıcında çağrılır; ilk istek beklemesin."""
    indeksi_kur()
    _model_yukle()


def ara(soru: str, k: int = 5) -> tuple[list[dict], float]:
    """Sorguyu 'query: ' prefix'iyle embed et; kosinüs benzerliğine göre top-k kanıt."""
    belgeler, kol = indeksi_kur()
    model = _model_yukle()
    basla = time.perf_counter()
    q = model.encode(["query: " + soru], normalize_embeddings=True,
                     show_progress_bar=False).astype(np.float32)[0]
    yanit = kol.query(
        query_embeddings=[q], n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    sure = time.perf_counter() - basla
    kanitlar = []
    for i, belge_id in enumerate(yanit["ids"][0]):
        meta = yanit["metadatas"][0][i]
        kanitlar.append({
            "brans_code": meta["brans_code"],
            "program": meta["program"],
            "kaynak_url": meta["kaynak_url"],
            "dosya": meta["dosya"],
            # chroma kosinüs UZAKLIK döner; benzerlik = 1 - uzaklık
            "skor": round(1.0 - float(yanit["distances"][0][i]), 4),
            "govde": yanit["documents"][0][i],
        })
    return kanitlar, sure


def sentezle(soru: str, kanitlar: list[dict], yapisal_satirlar: list[dict] | None = None,
             max_tokens: int = 3000) -> str:
    """Kanıt + yapısal sonuçları LLM'e verip kullanıcı yanıtını üret."""
    parcalar = []
    for s, k in enumerate(kanitlar, 1):
        parcalar.append(
            f"[{s}] {k['program']} (BransCode {k['brans_code']})\n"
            + k["govde"].replace("\n\n", "\n")[:KANIT_SINIRI]
        )
    kanit_metni = "\n\n".join(parcalar) or "(kanıt yok)"
    if yapisal_satirlar is None:
        guncel = ""
    else:
        satir_metni = "\n".join(
            f"- {s['program']} (BransCode {s['brans_code']}) | {s['merkez']}"
            f" | başlangıç {s['baslangic'] or '?'} | kayıt: {s['kayit_durumu']}"
            for s in yapisal_satirlar[:8]
        ) or "(filtreye uyan güncel kurs bulunamadı — kurs varsa kaydı kapalı ya da filtre uyuşmuyor demektir)"
        guncel = (f"\n\nGÜNCEL YAPISAL SORGU SONUCU (tek doğruluk kaynağı — kayıt "
                  f"durumu/tarih/kontenjan için):\n{satir_metni}")
    return chat(
        [{"role": "system", "content": SISTEM},
         {"role": "user", "content":
          f"Kanıt belgeler:\n\n{kanit_metni}{guncel}\n\nSoru: {soru}"}],
        etiket="rag-sentez", max_tokens=max_tokens,
    )


if __name__ == "__main__":
    ayristir = argparse.ArgumentParser(description="İSMEK RAG katmanı (e5 + ChromaDB + LLM sentez)")
    ayristir.add_argument("--kur", action="store_true", help="indeksi kur ve istatistik yaz")
    ayristir.add_argument("--soru", type=str, help="hızlı deneme sorusu")
    ayristir.add_argument("--k", type=int, default=5)
    args = ayristir.parse_args()

    if args.kur or args.soru:
        basla = time.perf_counter()
        belgeler, kol = indeksi_kur()
        print(f"[rag] indeks: {kol.count()} belge ({time.perf_counter() - basla:.1f} sn) → {CHROMA_YOLU}")
    if args.soru:
        kanitlar, sure = ara(args.soru, args.k)
        print(f"[rag] vektör arama {sure:.2f} sn:")
        for k in kanitlar:
            print(f"  {k['skor']:.3f}  {k['program']} (BransCode {k['brans_code']})")
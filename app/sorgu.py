"""İSMEK yapısal sorgu katmanı — eğitim Gün 1 İSMEK hedefi (H2), eğitmen çözümü.

Veri kaynağı: <veri_dir>/kayitlar/*.json (topla.py çıktısı; tek doğruluk kaynağı).
Kural (anlatim.md §9): kayıt durumu, tarih, kontenjan gibi DİNAMİK alanlar yalnız
burada yaşar; vektör mağazasına konmaz — chatbot bu soruları yapısal sorguyla
yanıtlar, statik içerik (amaç, koşullar) vektör aramasıyla.

Veri dizini seçimi: ISMEK_VERI_DIR env → yoksa <repo>/veri (tam koşum).
Lab/CI için sabit fixture: <repo>/veri/ornek (5 program, 6 kurs — topla.py
çıktısının 2026-09-04 koşumundan sabitlenmiş dilim).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_TR = str.maketrans({"İ": "i", "I": "ı"})


def _kucuk(metin: str) -> str:
    """Türkçe duyarsız küçük harf: İ→i, I→ı, sonra casefold.

    casefold tek başına yetmez: 'İ' → 'i̇' (birleşik nokta) olur, 'i' ile
    eşleşmez. Portal verisi Türkçe adlar taşır; filtreler bunu kullanır.
    """
    return metin.translate(_TR).casefold()


def veri_klasoru(veri_dir: str | None = None) -> Path:
    yol = veri_dir or os.environ.get("ISMEK_VERI_DIR") or REPO / "veri"
    return Path(yol).resolve()


def yukle(veri_dir: str | None = None) -> list[dict]:
    """kayitlar/*.json → brans_code sıralı program kayıtları."""
    klasor = veri_klasoru(veri_dir) / "kayitlar"
    if not klasor.is_dir():
        raise FileNotFoundError(
            f"kayıt dizini yok: {klasor} — önce `python3 topla.py` koştur ya da "
            "ISMEK_VERI_DIR=veri/ornek ile fixture kullan"
        )
    kayitlar = [json.loads(p.read_text(encoding="utf-8")) for p in klasor.glob("*.json")]
    return sorted(kayitlar, key=lambda k: k["brans_code"])


def kurs_satiri(kayit: dict, kurs: dict) -> dict:
    """Kursu program bilgisiyle düzleştir — sorgu çıktısı satır biçimi."""
    return {
        "brans_code": kayit["brans_code"],
        "program": kayit["program"]["ad"],
        "bolum": kayit["program"]["bolum"],
        "seviye": kayit["program"].get("seviye", ""),
        "sure_saat": kayit.get("sure_saat"),
        "kurs_id": kurs["kurs_id"],
        "merkez": kurs["merkez_adi"],
        "ilce": kurs["ilce"],
        "verilis": kurs["verilis_sekli"],
        "egitim_dili": kurs["egitim_dili"],
        "baslangic": kurs["baslangic"],
        "bitis": kurs["bitis"],
        "kontenjan": kurs["kontenjan"],
        "kayit_durumu": kurs["kayit_durumu"],
        "kayit_acik": bool(kurs["kayit_alma_durumu"]),
    }


def sorgula(
    kayitlar: list[dict],
    ilce: str | None = None,
    kayit_acik: bool | None = None,
    bolum: str | None = None,
    verilis: str | None = None,
    arama: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Yapısal filtre — alistirmalar.md Alıştırma 2'nin genelleştirilmiş hâli.

    ilce: önek eşleşmesi (kampüs adları ilçe adını taşıyabilir:
    "AVCILAR GÜMÜŞPALA" — bilinçli tercih, H3 taksonomisi bağlar).
    kayit_acik: True → kayıda açık, False → kapalı, None → fark etmez.
    """
    satirlar = [kurs_satiri(k, c) for k in kayitlar for c in k["kurslar"]]
    if ilce:
        onek = _kucuk(ilce)
        satirlar = [s for s in satirlar if _kucuk(s["ilce"]).startswith(onek)]
    if kayit_acik is not None:
        satirlar = [s for s in satirlar if s["kayit_acik"] == bool(kayit_acik)]
    if bolum:
        satirlar = [s for s in satirlar if _kucuk(s["bolum"]) == _kucuk(bolum)]
    if verilis:
        satirlar = [s for s in satirlar if _kucuk(verilis) in _kucuk(s["verilis"])]
    if arama:
        terim = _kucuk(arama)
        satirlar = [s for s in satirlar if terim in _kucuk(s["program"])]
    satirlar.sort(key=lambda s: (s["baslangic"], s["brans_code"]))
    return satirlar[:limit] if limit else satirlar


def istatistik(kayitlar: list[dict]) -> dict:
    """/ozet uç noktasının verdiği koşum istatistiği."""
    kurslar = [c for k in kayitlar for c in k["kurslar"]]
    return {
        "program_sayisi": len(kayitlar),
        "kurs_sayisi": len(kurslar),
        "acik_kurs": sum(1 for c in kurslar if c.get("kayit_alma_durumu")),
        "kapali_kurs": sum(1 for c in kurslar if not c.get("kayit_alma_durumu")),
        "bolum_sayisi": len({k["program"]["bolum"] for k in kayitlar}),
        "ilce_sayisi": len({c["ilce"] for c in kurslar}),
    }


def dogrulama_kapisi(veri_dir: str | None = None) -> dict:
    """ozet.json ↔ kayitlar tutarlılık kapısı — anti-uydurma kültürü.

    Sayılar uyuşmuyorsa koşuma güvenme: gecer=False + bulgular döner.
    alistirmalar.md Alıştırma 4'ün JSON tarafındaki kardeşi.
    """
    ozet = json.loads((veri_klasoru(veri_dir) / "ozet.json").read_text(encoding="utf-8"))
    kayitlar = yukle(veri_dir)
    kurslar = [c for k in kayitlar for c in k["kurslar"]]
    acik = sum(1 for c in kurslar if c.get("kayit_alma_durumu"))
    bulgular = []
    if ozet.get("program_sayisi") != len(kayitlar):
        bulgular.append(
            f"program_sayisi: ozet={ozet.get('program_sayisi')} kayitlar={len(kayitlar)}"
        )
    if ozet.get("kurs_sayisi") != len(kurslar):
        bulgular.append(f"kurs_sayisi: ozet={ozet.get('kurs_sayisi')} kayitlar={len(kurslar)}")
    if ozet.get("acik_kayit_kurs") != acik:
        bulgular.append(f"acik_kayit_kurs: ozet={ozet.get('acik_kayit_kurs')} kayitlar={acik}")
    return {"gecer": not bulgular, "bulgular": bulgular}
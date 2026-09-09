"""Sorgu çözümleyici — Türkçe soru → JSON filtre (H3, alıştırma 8 kalıbı).

LLM çıktısı asla doğrudan kullanıcıya gösterilmez; yalnız app/sorgu.py
yapısal katmanına beslenen filtre parametresidir (guardrail). Şema:
{"ilce": str|null, "verilis": str|null, "kayit_durumu": "acik"|"kapali"|null,
 "arama_terimi": str}

Kullanım:
    from bot.sorgu_cozumleyici import coz
    filtre = coz("Avcılar'da kayda açık pastacılık kursları?")
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bot.istemci import chat  # noqa: E402

VERILIS_DEGERLERI = [
    "Yüz Yüze Eğitim",
    "Video Tabanlı Uzaktan Eğitim",
    "Etkileşimli İçerik Tabanlı Uzaktan Eğitim",
    "Canlı Ders Tabanlı Uzaktan Eğitim",
    "Harmanlanmış(Yüz Yüze + Uzaktan) Eğitim",
]

PROMPT = """Aşağıdaki Türkçe soruyu İSMEK eğitim veritabanı filtresine çevir.
Yalnız JSON döndür. Bilinmeyen alan için null kullan.
arama_terimi: program adında aranacak KISA çekirdek terim (ör. "pasta", "ingilizce"); "kurs", "var mı" gibi genel kelimeleri ve ilçe adını koyma.
Geçerli verilis değerleri: "Yüz Yüze Eğitim", "Video Tabanlı Uzaktan Eğitim",
"Etkileşimli İçerik Tabanlı Uzaktan Eğitim", "Canlı Ders Tabanlı Uzaktan Eğitim",
"Harmanlanmış(Yüz Yüze + Uzaktan) Eğitim".
Şema: {"ilce": str|null, "verilis": str|null, "kayit_durumu": "acik"|"kapali"|null, "arama_terimi": str}

Soru: {soru}"""

SABIT = {"ilce": None, "verilis": None, "kayit_durumu": None, "arama_terimi": ""}


def coz(soru: str) -> dict:
    yanit = chat(
        [{"role": "user", "content": PROMPT.replace("{soru}", soru)}],
        etiket="sorgu-cozumleyici",
    )
    eslesme = re.search(r"\{[\s\S]*\}", yanit)
    if not eslesme:
        raise RuntimeError(f"çözümleyici JSON döndürmedi: {yanit[:200]}")
    filtre = dict(SABIT)
    ham = json.loads(eslesme.group(0))
    for anahtar in SABIT:
        deger = ham.get(anahtar)
        if deger in (None, "", "null"):
            continue
        if anahtar == "kayit_durumu":
            kucuk = str(deger).casefold()
            filtre[anahtar] = kucuk if kucuk in ("acik", "kapali") else None
        elif anahtar == "verilis":
            eslesme_v = next((v for v in VERILIS_DEGERLERI
                              if str(deger).casefold() in v.casefold()), None)
            filtre[anahtar] = eslesme_v
        else:
            filtre[anahtar] = str(deger)
    return filtre


if __name__ == "__main__":
    soru = " ".join(sys.argv[1:]) or "Avcılar'da kayda açık pastacılık kursları var mı?"
    print(json.dumps(coz(soru), ensure_ascii=False, indent=2))
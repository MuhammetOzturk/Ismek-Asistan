"""veri/kayitlar/*.json → veri/markdown/*.md üretici (RAG Gün 3 veri hazırlığı).

RAG vektör mağazası statik içerik (amaç, ön koşullar, sınav, malzeme) için
markdown belgeleri okur (bot/rag.py MARKDOWN_DIR). Dinamik alanlar (kayıt
durumu, tarih, kontenjan) bilinçli olarak BELGELENMEZ — onlar app/sorgu.py
yapısal katmanının tek doğruluk kaynağıdır.

Çıktı biçimi bot/rag.py belgeleri_yukle() ile uyumludur: `---\n` frontmatter
(brans_code, program, kaynak_url) + markdown gövde. Koşum deterministiktir;
aynı kayıtlar → aynı baytlar.

Kullanım (repo kökünden): python3 veri/markdown_uret.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KAYIT_DIR = REPO / "veri" / "kayitlar"
HEDEF_DIR = REPO / "veri" / "markdown"

BASLIKLAR = [
    ("amac", "Amaç"),
    ("on_kosullar", "Ön Koşullar"),
    ("sinav_bilgisi", "Sınav Bilgisi"),
    ("malzeme_ekipman", "Malzeme ve Ekipman"),
]


def belge_uret(kayit: dict) -> str:
    """Tek program kaydını frontmatter + gövde markdown'a çevir."""
    program = kayit["program"]
    icerik = kayit.get("icerik") or {}
    satirlar = [
        "---",
        f"brans_code: {kayit['brans_code']}",
        f'program: "{program["ad"]}"',
        f"kaynak_url: {kayit.get('meta', {}).get('kaynak_url', '')}",
        "---",
        "",
        f"# {program['ad']} (BransCode {kayit['brans_code']})",
        "",
        f"- Bölüm: {program['bolum']}",
    ]
    if program.get("seviye"):
        satirlar.append(f"- Seviye: {program['seviye']}")
    if kayit.get("sure_saat"):
        satirlar.append(f"- Süre: {kayit['sure_saat']} saat")
    if kayit.get("verilis_sekli"):
        satirlar.append(f"- Veriliş: {', '.join(kayit['verilis_sekli'])}")
    for anahtar, baslik in BASLIKLAR:
        metin = (icerik.get(anahtar) or "").strip()
        if metin:
            satirlar += ["", f"## {baslik}", "", metin]
    return "\n".join(satirlar) + "\n"


def main() -> int:
    if not KAYIT_DIR.is_dir():
        raise SystemExit(f"kayıt dizini yok: {KAYIT_DIR}")
    HEDEF_DIR.mkdir(parents=True, exist_ok=True)
    sayi = 0
    for yol in sorted(KAYIT_DIR.glob("*.json")):
        kayit = json.loads(yol.read_text(encoding="utf-8"))
        hedef = HEDEF_DIR / f"{kayit['brans_code']}.md"
        hedef.write_text(belge_uret(kayit), encoding="utf-8")
        sayi += 1
    print(f"[markdown_uret] {sayi} belge → {HEDEF_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Ortak LLM istemcisi — openai-uyumlu, çok sağlayıcı ücretsiz hat.

Sıra: Groq > Hugging Face > Gemini (hepsi ücretsiz katman).
402 (kota bitti) / 429 (hız limiti) durumunda sıradaki hata geçilir —
`ai-agent-otomasyon-egitimi/kurulum.md` §3 maliyet disiplini ve 402/429
playbook'u bu dosyanın kalıbıdır.

Kullanım:
    from istemci import chat, ozet
    cevap = chat([{"role": "user", "content": "..."}], etiket="lab5")
    ...
    print(ozet())   # koşumun toplam token + maliyet raporu
"""
import os
import time

from openai import APIError, OpenAI

HATLAR = [
    {
        "ad": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
        "anahtar_env": "GROQ_API_KEY",
    },
    {
        "ad": "hf",
        "base_url": "https://router.huggingface.co/v1",
        "model": "openai/gpt-oss-120b:cheapest",
        "anahtar_env": "HF_TOKEN",
    },
    {
        "ad": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash",
        "anahtar_env": "GEMINI_API_KEY",
    },
]

# USD / 1M token (yaklaşık). Eğitmen kurulum.md çeyreklik revizyon listesiyle günceller;
# HF hattı yanıtın usage alanında gerçek estimated_cost döndürürse o esas alınır.
FIYAT_1M = {
    "groq": (0.10, 0.50),
    "hf": (0.10, 0.50),
    "gemini": (0.30, 2.50),
}

# Koşum toplamı — rubrikteki "maliyet raporu" ölçütü buradan gelir
TOKERLEK = {"giris": 0, "cikis": 0, "usd": 0.0}

# gpt-oss akıl yürütme tokeni ayırdığı için kurulum.md kuralı: max_tokens >= 1200.
# Kod üretiminde reasoning + kod birlikte gider; 3000 güvenli bütçedir.
VARSAYILAN_MAX_TOKENS = 3000


def ozet() -> str:
    return (
        f"KOŞUM MALİYETİ: {TOKERLEK['giris']} giriş + {TOKERLEK['cikis']} çıkış tokeni"
        f" — yaklaşık ${TOKERLEK['usd']:.6f}"
    )


def _kullanım_yaz(hat: str, usage, etiket: str) -> None:
    giris = getattr(usage, "prompt_tokens", 0) or 0
    cikis = getattr(usage, "completion_tokens", 0) or 0
    gercek = getattr(usage, "estimated_cost", None)  # HF router gerçek maliyeti verir
    if gercek is not None:
        usd = float(gercek)
    else:
        giris_f, cikis_f = FIYAT_1M[hat]
        usd = (giris * giris_f + cikis * cikis_f) / 1_000_000
    TOKERLEK["giris"] += giris
    TOKERLEK["cikis"] += cikis
    TOKERLEK["usd"] += usd
    print(f"[maliyet] {hat:6} | {giris} giriş + {cikis} çıkış tok | ${usd:.6f} | {etiket}")


def chat(
    mesajlar: list[dict],
    *,
    etiket: str = "chat",
    max_tokens: int = VARSAYILAN_MAX_TOKENS,
    temperature: float = 0.2,
) -> str:
    """Tüm hatları sırayla dener; ilk başarılı cevabın metnini döndürür."""
    mevcut = [h for h in HATLAR if os.environ.get(h["anahtar_env"])]
    if not mevcut:
        raise RuntimeError(
            "Hiç anahtar yok. kurulum.md §2: GROQ_API_KEY (kart yok) > HF_TOKEN > GEMINI_API_KEY"
        )
    hatalar = []
    for hat in mevcut:
        istemci = OpenAI(
            api_key=os.environ[hat["anahtar_env"]],
            base_url=hat["base_url"],
            max_retries=2,
            timeout=90,
        )
        for deneme in range(2):
            try:
                yanit = istemci.chat.completions.create(
                    model=hat["model"],
                    messages=mesajlar,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                icerik = (yanit.choices[0].message.content or "").strip()
                if not icerik:
                    # gpt-oss: max_tokens'ın tamamı reasoning'e gitti — bütçeyi artır
                    raise RuntimeError(
                        "boş içerik: max_tokens bütçesi reasoning'de tükendi, artır"
                    )
                _kullanım_yaz(hat["ad"], yanit.usage, etiket)
                return icerik
            except APIError as e:
                durum = getattr(getattr(e, "response", None), "status_code", "?")
                hatalar.append(f"{hat['ad']}#{deneme + 1}: HTTP {durum} {e.__class__.__name__}")
                if durum == 429:  # hız limiti — Retry-After'a saygılı kısa bekleme
                    bekle = min(
                        float(e.response.headers.get("retry-after", 5) or 5), 20
                    )
                    print(f"[{hat['ad']}] 429 — {bekle:.0f} sn bekleniyor")
                    time.sleep(bekle)
                else:
                    break  # 402 vb. → bu hattı bırak, sıradakine geç
            except (RuntimeError, OSError) as e:
                hatalar.append(f"{hat['ad']}#{deneme + 1}: {e}")
                break
    raise RuntimeError(
        "Tüm hatlar başarısız. Denenenler:\n  " + "\n  ".join(hatalar)
    )
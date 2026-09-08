# Ismek Asistan

İSMEK kursları hakkında bilgi almak isteyen kişiler için geliştirilen asistan projesi.

İstanbul'da ücretsiz sanat ve meslek eğitimi veren İSMEK kurslarını aramak, karşılaştırmak ve kişiye uygun kursları önermek için kullanılır. Kullanıcı sorularını doğal dilde yanıtlar; kurs isimleri, dalları ve eğitim yerleri hakkında güncel bilgi sağlar.

## 2. Gün

Projenin iki bileşeni bu gün depoya eklendi:

- **`app/`** — FastAPI tabanlı sorgu API'si.
  - `app/sorgu.py`: `veri/kayitlar/*.json` kayıtlarını yükler; ilçe, kayıt durumu, bölüm, veriliş ve arama filtreleriyle yapısal sorgu (`sorgula`), koşum istatistiği (`istatistik`) ve `ozet.json` ↔ `kayitlar` tutarlılık kapısı (`dogrulama_kapisi`) sunar.
  - `app/api.py`: uç noktalar `GET /health`, `GET /ozet`, `GET /kurslar` ve `GET /programlar/{brans_code}`. Çalıştırma (repo kökünden): `uvicorn app.api:app --port 8000`
  - `requirements.txt`: fastapi, uvicorn, httpx, pytest.
  - `Dockerfile`: `docker build -f app/Dockerfile -t ismek-sunucu .` (repo kökünden koş; context repo kökü olmalı) → sonra `docker run -d -p 8000:8000 ismek-sunucu`. `ISMEK_VERI_DIR=/ismek/veri` image içinde sabitli.
- **`veri/`** — `topla.py` çıktısı veri katmanı: `kayitlar/*.json` (5 program kaydı, tek doğruluk kaynağı) ve koşum özeti `ozet.json`.


**Katki Saglayanlar:**
- Muhammet Ozturk
- Furkan Kurt
- Bekir Yildirim

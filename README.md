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


## 3. Gün

Sorgu API'sinin üzerine tek sayfa web arayüzü eklendi:

- **`app/web.py`** — arayüz sayfası (`SAYFA`): filtre formu (program adı, ilçe, bölüm, kayıt durumu), hazır örnek sorgu çipleri ve `/ozet`'ten beslenen istatistik şeridi. Sayfa JSON uç noktalarını `fetch` ile çağırır; harici/CDN bağımlılığı yok.
- **`app/api.py`** — yeni `GET /` rotası arayüzü sunar; API ile arayüz aynı süreçte: `uvicorn app.api:app --port 8000` → `http://127.0.0.1:8000` (Docker görüntüsü de aynı dosyayla ayağa kalkar).
- Derin bağlantı desteği: filtreler URL'den okunur — ör. `http://127.0.0.1:8000/?kayit=acik` açılır açılmaz kaydı açık kursları sorgulayıp tabloyu doldurur.

Örnek sorgu sonucu — "Kaydı açık tüm kurslar" çipi (`?kayit=acik`, 4 kurs):

![Web arayüzünde örnek sorgu sonucu — kaydı açık 4 kurs listeleniyor](docs/gun3-web-arayuz.png)

**Katki Saglayanlar:**
- Muhammet Ozturk
- Furkan Kurt
- Bekir Yildirim

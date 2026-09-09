FROM python:3.12-slim
WORKDIR /ismek

# torch'u CPU tekeriyle çek — CUDA varyantı (~2 GB) gereksiz: e5 çıkarımı CPU'da.
COPY app/requirements.txt app-gereksinimler.txt
COPY bot/requirements.txt bot-gereksinimler.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r app-gereksinimler.txt -r bot-gereksinimler.txt && \
    rm app-gereksinimler.txt bot-gereksinimler.txt

COPY app/__init__.py app/__init__.py
COPY app/api.py app/sorgu.py app/web.py app/
COPY bot/istemci.py bot/rag.py bot/sorgu_cozumleyici.py bot/
COPY veri/kayitlar veri/kayitlar
COPY veri/markdown veri/markdown

ENV ISMEK_VERI_DIR=/ismek/veri
EXPOSE 8000
# İlk açılışta vektör indeksi kurulur ve e5 modeli HF'den indirilir (~450 MB).
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
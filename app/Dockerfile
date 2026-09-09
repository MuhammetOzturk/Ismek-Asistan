FROM python:3.12-slim
WORKDIR /ismek

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/__init__.py app/__init__.py
COPY app/api.py app/api.py
COPY app/sorgu.py app/sorgu.py
COPY veri/kayitlar veri/kayitlar

ENV ISMEK_VERI_DIR=/ismek/veri
EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]

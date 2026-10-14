FROM python:3.11-slim@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr=5.5.0-1+b1 tesseract-ocr-eng=1:4.1.0-2 tesseract-ocr-spa=1:4.1.0-2 poppler-utils=25.03.0-5+deb13u4 && rm -rf /var/lib/apt/lists/*
COPY services/api/requirements.lock requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY kcee kcee
COPY examples examples
COPY docs/engineering/finer-mesh-exploration.json docs/engineering/root-refinement-exploration.json /app/evidence/
COPY services/api/app.py app.py
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce
WORKDIR /app
COPY services/api/requirements.lock requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY kcee kcee
COPY examples examples
COPY services/api/app.py app.py
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

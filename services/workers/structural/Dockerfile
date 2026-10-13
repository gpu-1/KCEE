FROM python:3.11-slim-bookworm@sha256:0a310eeecf4e1f5a0743f9a6520c90c88d089c903ca5fd283f501e3a805f5f89
RUN apt-get update && apt-get install -y --no-install-recommends calculix-ccx=2.20-1 python3-gmsh=4.8.4+ds2-3 && rm -rf /var/lib/apt/lists/*
ENV PYTHONPATH=/usr/lib/python3/dist-packages
WORKDIR /app
COPY kcee kcee
COPY services/workers/structural/server.py server.py
CMD ["python", "server.py"]

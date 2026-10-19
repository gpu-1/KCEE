FROM python:3.11-slim@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce AS native-build
RUN apt-get update && apt-get install -y --no-install-recommends g++ openfoam=1912.200626-3+b1 && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY services/workers/cfd/native/ /build/
RUN python /build/build.py

FROM python:3.11-slim@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce
RUN apt-get update && apt-get install -y --no-install-recommends openfoam=1912.200626-3+b1 && rm -rf /var/lib/apt/lists/*
ENV WM_PROJECT_DIR=/usr/share/openfoam
ENV FOAM_ETC=/usr/share/openfoam/etc
WORKDIR /app
COPY --from=native-build /opt/kcee/native /opt/kcee/native
COPY kcee kcee
COPY services/workers/cfd/server.py server.py
CMD ["python", "server.py"]

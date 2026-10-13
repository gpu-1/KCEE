FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html main.js client.js style.css vite.config.js ./
COPY tests tests
RUN npm test && npm run build
CMD ["npm", "run", "preview"]

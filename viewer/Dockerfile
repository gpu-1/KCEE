FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY index.html main.js ./
CMD ["npm", "run", "dev"]

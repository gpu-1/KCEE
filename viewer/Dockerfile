FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html main.js client.js thermal-chart.js cfd-chart.js vortex-view.js bracket-flow-view.js vortex-convergence.js cfd-comparison.js knowledge-ui.js pdf-source.js pdf-review.js page-notes.js note-export.js search-export.js compare-evidence.js compare-ui.js comparison-export.js verify-export.js verify-export-ui.js verification-report.js assistant-scope.js assistant-evidence.js engineering-report.js engineering-workflow.js document-workspace.js document-library.js backup-status-ui.js search-highlight.js saved-searches.js saved-searches-ui.js saved-search-transfer.js search-page-filter.js search-page-filter-ui.js style.css vite.config.js ./
COPY tests tests
RUN npm test && npm run build
CMD ["npm", "run", "preview"]

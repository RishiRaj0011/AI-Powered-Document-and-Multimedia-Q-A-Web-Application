FROM node:20-alpine AS builder

WORKDIR /app

# Copy manifests first for layer caching — only re-runs npm ci when
# package.json or package-lock.json changes
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

COPY . .
RUN npm run build


# ---------------------------------------------------------------------------
FROM nginx:alpine AS final

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy production nginx config (nginx.conf is in the frontend/ build context)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

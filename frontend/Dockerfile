FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

RUN mkdir -p public

# Build-time env vars baked into Next.js output
ARG NEXT_PUBLIC_WS_URL=
ENV NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}

# BACKEND_URL usado pelo next.config.js rewrites (compilado no build)
ENV BACKEND_URL=http://backend:8000

RUN npm run build

# Production stage
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/package.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/next.config.js ./

EXPOSE 3000

CMD ["npm", "run", "start"]

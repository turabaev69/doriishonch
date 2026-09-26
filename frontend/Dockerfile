FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit --no-fund
COPY . .
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL
ENV NEXT_STANDALONE=1
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]

FROM node:20-slim

WORKDIR /app

COPY package.json .
COPY node_modules ./node_modules

COPY . .

EXPOSE 9090

CMD ["node", "index.js"]

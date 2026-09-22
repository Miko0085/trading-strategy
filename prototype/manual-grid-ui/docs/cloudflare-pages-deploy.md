# Cloudflare Pages deployment

Статус: frontend-only production/staging deployment.

## Архитектура

Cloudflare Pages публикует только React/Vite frontend. FastAPI, PostgreSQL и Bybit credentials остаются вне Pages и должны работать на отдельном HTTPS backend.

Frontend:
- root: `prototype/manual-grid-ui/frontend`
- build command: `npm run build`
- output: `dist`
- production env: `VITE_API_URL=https://<backend-host>`

Backend:
- FastAPI на отдельном VPS/host
- HTTPS обязателен для browser calls from Pages
- `MANUAL_GRID_ALLOWED_ORIGINS` — comma-separated allowlist, например:
  `http://localhost:5173,https://crypto-grid.pages.dev`

## Cloudflare Pages

1. Workers & Pages → Create application → Pages → Connect to Git.
2. GitHub repository: `Miko0085/trading-strategy`.
3. Production branch: `feature/manual-grid-ui-mvp` для текущего pilot. После стабилизации переключить на `main`.
4. Root directory: `prototype/manual-grid-ui/frontend`.
5. Build command: `npm run build`.
6. Build output directory: `dist`.
7. Environment variable: `VITE_API_URL=https://<backend-host>`.
8. Deploy.

Production URL вида `https://<project-name>.pages.dev` остаётся постоянным. Новые production deploys обновляют содержимое по тому же адресу; hash URLs относятся к preview deployments.

## Security

Никогда не добавлять в Pages/Vite environment:
- `BYBIT_API_KEY`
- `BYBIT_API_SECRET`
- `DATABASE_URL`

Переменные `VITE_*` попадают в frontend bundle и считаются публичными.

Backend содержит private read-only account data endpoints. Стабильный frontend URL не означает, что backend API следует делать полностью публичным; для внешнего доступа нужен отдельный auth/Cloudflare Access layer либо другой подтверждённый access-control слой.

## Verification

После deploy:
- открыть `https://<project>.pages.dev`;
- browser DevTools → Network: `/api/health`, `/api/state/*`, `/api/market/klines/*` должны идти на `VITE_API_URL`;
- проверить CORS;
- убедиться, что frontend не содержит секретов;
- проверить Grid Preview и Bybit candle chart.

# Frontend Integration — Architecture Document

## Overview

Phase 5 introduces the first integrated frontend for quant-platform, converting the existing collection of backend services into a unified platform with a coherent user interface.

## Architecture

```
┌──────────────────────────────────────────┐
│          FRONTEND (React SPA)            │
│  Vite + React 19 + TypeScript + Tailwind │
│                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Dashboard │  │   Data   │  │ Strats │ │
│  └────┬─────┘  └────┬─────┘  └───┬────┘ │
│       │              │            │      │
│  ┌────┴──────────────┴────────────┴────┐ │
│  │          API Client Layer           │ │
│  │    TanStack Query + Typed Fetch     │ │
│  └─────────────────┬───────────────────┘ │
└────────────────────┼─────────────────────┘
                     │ HTTP/REST
                     ▼
┌──────────────────────────────────────────┐
│          API GATEWAY (FastAPI)           │
│  /health  /strategies  /backtests       │
│  /market-data  /portfolios  /risk       │
│  /data-quality                          │
└────────────┬─────────────────────────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
 Data    Quant     Execution
Services Services  (Future)
    │        │
    ▼        ▼
 Parquet  PostgreSQL
 Storage    (ORM)
```

## Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | Vite + React | SPA tool, no SSR needed. Vite for fast HMR. |
| Language | TypeScript (strict) | Type safety across frontend, mirrors Pydantic schemas |
| Styling | Tailwind CSS v4 | Utility-first, CSS-first config in v4, dark theme |
| Server State | TanStack Query v5 | Caching, dedup, background refetch, mutation handling |
| Routing | React Router v7 | Standard SPA routing with nested layouts |
| Charts (financial) | Lightweight Charts | TradingView-quality candlestick charts |
| Charts (analytics) | Recharts | Equity curves, drawdowns, area charts |
| Forms | React Hook Form + Zod | Performant forms with schema validation |
| Icons | Lucide React | Lightweight, consistent icon set |

## API Integration Strategy

```
Backend Pydantic Schemas (schemas.py)
         │
         ▼ (manual mirror, TODO: auto-generate)
Frontend TypeScript Types (api/types.ts)
         │
         ▼
API Client Modules (api/strategies.ts, etc.)
         │
         ▼
TanStack Query Hooks (hooks/use-strategies.ts, etc.)
         │
         ▼
React Components (pages/strategies/StrategyList.tsx, etc.)
```

### API Endpoints Used

| Endpoint | Method | Frontend Feature |
|---|---|---|
| `/health` | GET | System status indicator |
| `/strategies` | GET | Strategy list, dashboard |
| `/strategies/{name}/schema` | GET | Strategy detail, backtest form params |
| `/backtests` | GET, POST | Backtest list, run new backtest |
| `/backtests/{id}` | GET | Backtest results page |
| `/market-data/symbols` | GET | Data explorer, dashboard |
| `/market-data/prices/{symbol}` | GET | Data explorer chart + table |
| `/market-data/ingest` | POST | Data ingestion from explorer |
| `/portfolios` | GET | Portfolio list |
| `/portfolios/{id}` | GET | Portfolio detail |
| `/portfolios/{id}/positions` | GET | Portfolio positions |
| `/data-quality/validate/{symbol}` | POST | Data quality validation |

## State Management

### Server State (TanStack Query)
- Strategies, backtests, portfolios, market data, health
- Automatic caching with 30s stale time
- Background refetch on mutation success
- Health polling every 30 seconds

### UI State (React useState/useReducer)
- Sidebar collapsed state
- Form inputs
- Selected filters
- Dialog visibility

**No global state store** — this is intentional. All server data flows through TanStack Query; UI state is local to components.

## Security Considerations

- **No secrets in frontend**: No API keys, database credentials, or broker tokens
- **No direct DB access**: All data via REST API
- **CORS**: Backend allows `*` in development (restrict in production)
- **Auth placeholder**: Architecture supports adding auth headers to `apiClient`
- **No sensitive data in logs**: API client doesn't log request/response bodies

## Known Limitations & Technical Debt

| Item | Status | Notes |
|---|---|---|
| Authentication | Not implemented | Hook point exists in API client |
| Backtest persistence | In-memory only | ORM models exist; backend change needed |
| Strategy CRUD | Read-only | Backend has hardcoded registry |
| OpenAPI type generation | Manual mirror | Should auto-generate from `/docs` |
| WebSocket for job status | Not implemented | Polling via TanStack Query instead |
| E2E tests | Not included | Playwright setup planned for Phase 6 |

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| API unavailable during dev | Vite proxy + graceful error states |
| Type drift between FE/BE | Review types when backend schemas change |
| Large dataset performance | Pagination via `limit` param; virtual scrolling future |
| Mobile layout | Responsive grid; sidebar collapses |

## File Structure

```
frontend/
├── index.html              # Entry HTML
├── package.json            # Dependencies
├── tsconfig.json           # TypeScript strict config
├── vite.config.ts          # Vite + Tailwind + proxy
├── Dockerfile              # Multi-stage build for Docker
├── eslint.config.js        # ESLint flat config
├── .env                    # VITE_API_BASE_URL
└── src/
    ├── main.tsx            # React DOM entry
    ├── App.tsx             # Router + QueryClient
    ├── index.css           # Design system tokens
    ├── api/                # HTTP client + typed modules
    ├── hooks/              # TanStack Query hooks
    ├── components/
    │   ├── layout/         # Sidebar, Header, AppLayout
    │   ├── ui/             # Card, Button, Badge, DataTable, States
    │   └── charts/         # EquityCurve, Drawdown, Candlestick
    ├── pages/              # Route pages by feature
    └── lib/                # Utils, constants
```

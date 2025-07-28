# Eunice Frontend Development Setup

## Quick Start

To run the complete development environment (backend + frontend):

```bash
./start_dev.sh
```

This will start:

- **PostgreSQL** database (port 5433)
- **Redis** cache (port 6380)
- **MCP Server** (internal communication)
- **AI Service** (internal communication)
- **API Gateway** (port 8001)
- **React Frontend** (port 5173)

## Access Points

- 📱 **React Frontend**: <http://localhost:5173/>
- 🚪 **API Gateway**: <http://localhost:8001>
- 📊 **Health Check**: <http://localhost:8001/health>

## Development Commands

### Start Development Environment

```bash
./start_dev.sh
```

### Stop Development Environment

```bash
./stop_dev.sh
```

### Check Logs

```bash
# Frontend logs
tail -f logs/frontend.log

# Backend logs
docker compose logs -f

# Specific service logs
docker compose logs -f api-gateway
docker compose logs -f mcp-server
docker compose logs -f ai-service
```

### Frontend Only (if backend is already running)

```bash
cd frontend
npm run dev
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/          # Shared components
│   │   ├── layout/          # Layout components
│   │   ├── ui/              # shadcn/ui components
│   │   └── welcome/         # Welcome page
│   ├── utils/
│   │   ├── api.ts           # API client
│   │   └── routes.ts        # Route constants
│   ├── App.tsx              # Main app with routing
│   └── main.tsx             # Entry point
├── components.json          # shadcn/ui config
├── vite.config.ts          # Vite config with proxy
└── package.json
```

## Tech Stack

- **React 19** with TypeScript
- **Vite** for development and building
- **React Router DOM** for routing
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **Heroicons** for icons

## API Integration

The frontend uses a proxy configuration to communicate with the backend:

- Frontend requests to `/api/*` are proxied to `http://localhost:8001`
- API client utilities are available in `src/utils/api.ts`
- Connection status is displayed on the welcome page

## Adding New Routes

1. Add route constants to `src/utils/routes.ts`
2. Create page components in `src/components/`
3. Add routes to `src/App.tsx`

## Troubleshooting

### Frontend not connecting to backend

1. Ensure backend services are running: `docker compose ps`
2. Check API Gateway health: `curl http://localhost:8001/health`
3. Check frontend logs: `tail -f logs/frontend.log`

### Port conflicts

- Frontend: 5173
- API Gateway: 8001  
- PostgreSQL: 5433
- Redis: 6380

If ports are in use, stop other services or modify the configuration.

---

## Original Vite + React + TypeScript Template

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

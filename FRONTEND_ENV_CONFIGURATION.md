# Frontend Environment Configuration - GridLedger GL-1

## Development Setup (.env.local)

Create `frontend/.env.local` with:

```env
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_API_KEY=letmein123

# Frontend Port
VITE_PORT=5173

# Debug Mode
VITE_DEBUG=true
```

## Production Setup (.env.production)

Create `frontend/.env.production` with:

```env
# Production API Endpoint
VITE_API_URL=https://api.gridledger.production.example.com
VITE_API_KEY=${PROD_API_KEY}

# Production Frontend
VITE_PORT=443

# Debug Mode (disabled in production)
VITE_DEBUG=false
```

## Staging Setup (.env.staging)

```env
VITE_API_URL=https://staging-api.gridledger.example.com
VITE_API_KEY=${STAGING_API_KEY}
VITE_PORT=443
VITE_DEBUG=false
```

---

## How to Use Environment Variables

### In React Components:

```typescript
// Access via import.meta.env
const apiUrl = import.meta.env.VITE_API_URL;
const apiKey = import.meta.env.VITE_API_KEY;

// Fallback for missing env
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

### In Vite Config:

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: parseInt(import.meta.env.VITE_PORT || '5173'),
    proxy: {
      '/api': {
        target: import.meta.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
      }
    }
  }
});
```

---

## Quick Start

1. Copy environment file:
   ```bash
   cd frontend
   cp .env.example .env.local
   ```

2. Edit `.env.local` with your backend URL

3. Start frontend dev server:
   ```bash
   npm run dev
   ```

4. Frontend will connect to backend at `http://localhost:8000`

---

## API Key Management

### Development (Hardcoded):
- Key: `letmein123`
- Usage: In X-API-Key header

### Production (Environment Variable):
- Store in CI/CD secrets
- Load via `process.env.PROD_API_KEY`
- Never commit to repository

---

## CORS Configuration

If frontend and backend are on different origins, ensure backend has CORS enabled:

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
)
```

---

## Testing Configuration

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=test_key_12345
```

Run tests with:
```bash
npm run test
```

---

## Environment Variables Reference

| Variable | Type | Default | Purpose |
|----------|------|---------|---------|
| `VITE_API_URL` | string | http://localhost:8000 | Backend API endpoint |
| `VITE_API_KEY` | string | letmein123 | API authentication key |
| `VITE_PORT` | number | 5173 | Frontend dev server port |
| `VITE_DEBUG` | boolean | false | Enable debug logging |

---

## Status Check

After starting frontend, verify backend connection:

```bash
curl -X GET http://localhost:5173/api/institutional/audit-trail/full \
  -H "X-API-Key: letmein123"
```

Expected response: `200 OK` with audit trail JSON

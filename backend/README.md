# Assessment Engine — Backend

Node.js **Express** API with **Prisma** (default **SQLite** file `prisma/dev.db` via `DATABASE_URL=file:./dev.db`; Docker Compose still uses PostgreSQL), **JWT** access + refresh tokens, **Bull** queues (Redis), **Socket.io**, optional **S3/MinIO** uploads, and **Swagger UI** at `/api/docs`.

## Questions from resources (no AI)

There is **no machine-learning** pipeline. You can still attach questions to books / question papers in two ways:

1. **Structured import** — `POST /api/v1/resources/{book|question_paper}/:id/import-questions` with a JSON body `{ "questions": [ ... ] }` using the same shape as creating a question (type, text, options, etc.). Use this for exports from another LMS, your own scripts, or manual JSON.

2. **Heuristic document extraction** — `POST /api/v1/resources/{book|question_paper}/:id/extract` reads the stored file: **PDF** text is taken with `pdf-parse`; **`.txt`** is read as UTF-8. The service splits on numbered lines (e.g. `1.`, `2)`). Lines like `(a) ...` are treated as MCQ options (no correct answer is inferred — teachers must verify). For reliable reads, configure **S3/MinIO** so the object key is stored on upload; otherwise the `fileUrl` must be a fetchable `http(s)` URL.

Quality of (2) depends entirely on how consistent the source document’s numbering is.

## Quick start

### Option A — API + web UI together (recommended)

From the **repository root** (parent of `backend/` and `frontend/`):

```bash
npm install
npm run dev
```

The first run creates `backend/.env` from `backend/.env.example` if it is missing. Then open the URL Vite prints (usually `http://localhost:5173`). The UI talks to the API through the dev proxy (`/api` → port 3000).

Before the first login, ensure the database is ready (once):

```bash
cd backend
npx prisma migrate deploy
npx prisma db seed
```

### Share the app on the internet ([untun](https://www.npmjs.com/package/untun))

Use tunnel-friendly dev so Vite does not break over HTTPS (see below). From the **repository root**:

**Terminal 1 — API + UI (tunnel mode disables broken `ws://localhost` HMR):**

```bash
npm run dev:tunnel
```

**Terminal 2 — public URL:**

```bash
npm run tunnel
```

This runs `npx untun tunnel http://localhost:5173` and prints a **HTTPS** URL (Cloudflare Quick Tunnel). If you use plain `npm run dev` instead, the page can stay **blank** in the browser because an HTTPS tunnel cannot use Vite’s default hot-reload WebSocket to `localhost`.

The frontend loads `frontend/.env.tunnel` (`VITE_TUNNEL=1`, `vite --mode tunnel`) which turns **HMR off** for that session only — refresh the browser manually after code changes.

`vite.config.ts` sets `allowedHosts: true` and `host: true` so tunnel hostnames work.

- Tunnel **only the API** (Swagger, mobile clients hitting port 3000 directly): `npm run tunnel:api`
- First-time Cloudflare prompt: set `UNTUN_ACCEPT_CLOUDFLARE_NOTICE=true` in your environment if the CLI asks you to accept terms.

### Option B — Backend only

1. Copy `.env.example` to `.env` and set `JWT_SECRET`, `JWT_REFRESH_SECRET` (each ≥32 characters recommended). For local SQLite you can omit `DATABASE_URL`; in non‑production it defaults to `file:./dev.db` (database file under `prisma/`). **Production** must set `DATABASE_URL` explicitly.

2. Install and migrate:

```bash
npm install
npx prisma migrate deploy
npx prisma db seed
```

3. Run:

```bash
npm run dev
```

- Health: `GET http://localhost:3000/health`
- API base: `http://localhost:3000/api/v1`
- OpenAPI UI: `http://localhost:3000/api/docs`

## Docker

From this directory:

```bash
docker compose up --build
```

Apply migrations against the Compose database (one-off):

```bash
docker compose run --rm api npx prisma migrate deploy
```

## Tests

```bash
npm test
```

## Seed data

School code **TEST001** and users `admin@demo-school.test`, `teacher@demo-school.test`, `student@demo-school.test` with password **Password123!** (see `prisma/seed.js`).

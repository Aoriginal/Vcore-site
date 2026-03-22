# CLAUDE.md — Vcore Site

## Project Overview

**Vcore** is a marketing/agency website for a retention-focused copywriting service targeting e-commerce brands. It offers email flows, post-purchase sequences, and retention campaigns to increase repeat purchases and customer lifetime value (CLV).

- **Framework**: Next.js 13.5.4 (App Router)
- **Language**: TypeScript (TSX)
- **Styling**: Tailwind CSS 3.3.4
- **React**: 18.2.0
- **Package manager**: npm

---

## Repository Structure

```
/home/user/Vcore-site/
├── CLAUDE.md                        ← This file
├── package.json.txt                 ← package.json stored as .txt (see note below)
├── next.config.js.txt               ← next.config.js stored as .txt (see note below)
└── Vcore2/
    └── src/
        ├── app/
        │   ├── layout.tsx           ← Root layout (ACTUAL .tsx file)
        │   └── globals.css          ← Global styles (ACTUAL .css file)
        └── components/
            └── Header.tsx           ← Nav header (ACTUAL .tsx file)
```

### Critical: File Organization Issue

**Most source files are stored as `.txt` files inside oddly-named directories.** This is a known structural problem in the repo. The actual content lives in nested `.txt` files:

| Intended file path | Actual location |
|---|---|
| `src/app/page.tsx` | `src/app/srcapppage.tsx/srcapppage.tsx.txt` |
| `src/app/contact/page.tsx` | `src/app/srcappcontactpage.tsx/srcappcontactpage.tsx.txt` |
| `src/app/services/page.tsx` | `src/app/srcappservicespage.tsx/srcappservicespage.tsx.txt` |
| `src/app/about/page.tsx` | `src/app/srcappaboutpage.tsx/srccomponentsabout-section.tsx.txt` |
| `src/components/hero.tsx` | `src/components/srccomponentshero.tsx/srccomponentshero.tsx.txt` |
| `src/components/services-section.tsx` | `src/components/srccomponentsservices-section.tsx/srccomponentsservices-section.tsx.txt` |
| `src/components/about-section.tsx` | `src/components/srccomponentsabout-section.tsx/srcappaboutpage.tsx.txt` (incomplete) |
| `next.config.js` | `/next.config.js.txt` (root) |
| `package.json` | `/package.json.txt` (root) |

**Before editing or creating source files, always check both the real `.tsx` files AND the `.txt` files in the weird directories. The `.txt` files contain the intended source code that needs to be properly organized.**

---

## Pages and Routes

The intended app uses Next.js App Router page structure:

| Route | Component | Status |
|---|---|---|
| `/` | `src/app/page.tsx` — `HomePage` | Source in `.txt` file |
| `/services` | `src/app/services/page.tsx` — `ServicesPage` | Source in `.txt` file |
| `/contact` | `src/app/contact/page.tsx` — `ContactPage` | Source in `.txt` file |
| `/about` | `src/app/about/page.tsx` — `AboutPage` | Source in `.txt` file |

### Home page (`page.tsx`) composition:
```tsx
<Hero />
<ServicesSection />
<AboutSection />    // incomplete component
<ContactSection />  // component missing entirely
```

---

## Components

### Existing (actual `.tsx` files)
- **`src/components/Header.tsx`** — Top nav with logo ("Vcore") and links to `/services`, `/work`, `/contact`
- **`src/app/layout.tsx`** — Root layout; includes `<Header>`, `<main>`, and `<footer>`

### In `.txt` files (need to be converted to real files)
- **`hero.tsx`** — Hero section with image, headline, CTA button to `/contact`
- **`services-section.tsx`** — 3-column grid: Email Flows, Post-Purchase Sequences, Retention Campaigns
- **`about-section.tsx`** — Incomplete; body is empty
- **`contact-section.tsx`** — Missing entirely (not found anywhere in repo)

---

## Styling Conventions

- **Tailwind CSS** for all styling — inline utility classes only, no CSS modules
- **No styled-components** or CSS-in-JS
- Global styles in `src/app/globals.css`:
  - Font: `Inter, sans-serif`
  - Background: `#f9fafb` (light gray)
  - Text: `#18181b` (near black)
- CSS custom properties (set but not widely used yet):
  ```css
  --brand-primary: #23272f;
  --brand-accent: #3b82f6;
  --brand-bg: #f9fafb;
  ```
- Blue accent color `blue-600` / `#3b82f6` used for CTAs and buttons
- Layout max-widths: `max-w-7xl` (header), `max-w-4xl`/`max-w-5xl` (content), `max-w-2xl` (contact form)

---

## Architecture Patterns

- **Next.js App Router** — Server Components by default; use `"use client"` only when needed
- **Client components**: Only the contact form uses `"use client"` (for `useState`)
- **State management**: React `useState` hooks only — no Redux, Zustand, or Jotai
- **Data fetching**: Direct `fetch()` API — no SWR or React Query
- **Navigation**: `<Link>` from `next/link` for internal links; `<a href>` also used in some places
- **Path alias**: `@/` maps to `src/` (e.g., `import Header from "@/components/Header"`)

---

## External API

The contact form submits leads to an external service:

- **Endpoint**: `POST https://alluring-encouragement-production.up.railway.app/public/lead_v3`
- **Payload**:
  ```json
  {
    "email": "...",
    "name": "...",
    "details": "...",
    "knowledge_profile_id": "eff7ec88-5cc2-4c59-9b7f-1e872788e83d"
  }
  ```
- The `knowledge_profile_id` is hard-coded in the contact page component
- No environment variable abstraction exists yet — this is a known gap

---

## Development Setup

### Prerequisites
The project needs to be properly structured before it can run. The current repo has these **missing configuration files** (they exist as `.txt` files but are not in the right location/format):
- `Vcore2/package.json` (use content from `/package.json.txt`)
- `Vcore2/next.config.js` (use content from `/next.config.js.txt`)
- `Vcore2/tsconfig.json` (missing entirely)
- `Vcore2/tailwind.config.js` (missing entirely)
- `Vcore2/postcss.config.js` (missing entirely)

### Scripts (from package.json.txt)
```bash
npm run dev     # Start development server (next dev)
npm run build   # Production build (next build)
npm start       # Start production server (next start)
```

### No testing framework is set up. No lint/format tooling configured.

---

## Known Issues / Technical Debt

1. **File structure corruption** — Source files stored as `.txt` inside wrongly-named directories instead of proper `.tsx` files. The project cannot run in its current state without restructuring.
2. **Missing config files** — No `tsconfig.json`, `tailwind.config.js`, or `postcss.config.js` in `Vcore2/`
3. **Incomplete component** — `AboutSection` has no JSX body
4. **Missing component** — `ContactSection` (used in home page) doesn't exist anywhere
5. **Hard-coded API values** — `knowledge_profile_id` and the external API URL in the contact page should be in environment variables
6. **No tests** — Zero test coverage; no testing framework installed
7. **No linting/formatting** — No ESLint or Prettier configuration
8. **No `.env` files** — No environment variable management
9. **`/work` link in header** — Header links to `/work` but no work/portfolio page exists

---

## Git Information

- **Main development branch**: `claude/add-claude-documentation-v8B3L`
- **Stable branches**: `master`, `main`
- **Remote**: `origin` at `http://local_proxy@127.0.0.1:33573/git/Aoriginal/Vcore-site`
- **Commit history**: 2 commits (both from 2026-02-07)

---

## Content / Copy

Vcore's value proposition language (use consistently in copy):
- "Retention-focused copywriting for e-commerce brands"
- "Email flows, post-purchase sequences, and retention campaigns"
- "Increase repeat purchases and customer lifetime value"
- "Turn one-time buyers into loyal customers"
- Key metric: CLV (Customer Lifetime Value)

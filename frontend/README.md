# Candence — AI Content Generation Dashboard

A complete front-end (UI only, **mock data, no backend**) for a SaaS tool that generates and
schedules content across multiple client websites. Built with **plain HTML5, CSS3 and vanilla
JavaScript** — no frameworks, no build step. Just open the files in a browser.

## Getting started
Open **`index.html`** in any modern browser. It links every page. No `npm`, no bundler.

## Roles & theme (mock)
- **Role toggle** — top bar of every page (and on the index): switch between **Admin** and
  **Super Admin**. Super Admin unlocks the *Admins & Roles* and *All Websites* screens plus the
  *Billing* settings section. The choice persists in `localStorage`.
- **Theme toggle** — the sun/moon button in the top bar switches **light / dark**. Persists in
  `localStorage`.

## Pages / routes
| File | Description |
|---|---|
| `index.html` | Route directory + quick links |
| `login.html` · `signup.html` · `forgot-password.html` | Branded split-layout auth |
| `dashboard.html` | Stat cards, weekly schedule, activity feed, output chart |
| `add-website.html` | Form → live "crawling…" animation → crawl-results confirmation |
| `website-workspace.html?site=<id>` | **Core page**: Overview / Generate / Calendar / Published / Settings tabs, AI draft cards with Approve / Edit / Regenerate / Reject and platform-styled previews |
| `calendar.html` | Weekly Mon–Sun board, drag-to-reschedule, auto-schedule, filters |
| `approvals.html` | Cross-website draft queue, bulk approve/reject, inline edit |
| `analytics.html` | Volume, platform mix, approval & engagement charts |
| `settings.html` | Profile, notifications, scheduler, connections, billing |
| `admins.html` | *(Super Admin)* admin table + roles & permission matrix |
| `all-websites.html` | *(Super Admin)* every website with owner & stats |

## Shared files
- **`styles.css`** — the design system: tokens (CSS custom properties), light/dark themes, and all
  component styles (buttons, inputs, cards, tables, tabs, modals, toasts, badges, avatars, empty
  states, skeletons, etc.).
- **`app.js`** — injects the shared sidebar + top bar into every page and wires the theme toggle,
  role toggle, dropdowns, modals, tabs and toasts. Exposes `window.Candence`.
- **`mock-data.js`** — all sample data (`window.MOCK`): websites, content drafts, admins, activity,
  notifications and analytics series.
- **`workspace.css` / `workspace.js`** — styles and logic specific to the website workspace.

## Notes
- Charts use **Chart.js** (CDN); icons use **Lucide** (CDN); type is **Inter** (Google Fonts).
- Brand glyphs (LinkedIn/YouTube/Instagram) are inline SVGs since Lucide no longer ships them.
- States included throughout: empty states, loading skeletons, validation/error states, and
  success toasts on actions.

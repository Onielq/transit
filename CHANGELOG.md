# Plateau Transit — CHANGELOG

All notable changes to the app are documented here.
Format: `[vYYYY.MM.DD-N] YYYY-MM-DD`

Every release **must** update:
1. The version string in this file
2. `CACHE_VERSION` in `sw.js`
3. `APP_VERSION` in the PWA `<head>`

---

## [v2026.03.22-1] 2026-03-22

### Added
- **GTFS static feed** — `plateau-transit-GTFS.zip` (60 routes, 7,200 trips, fares in RWF)
- **Backend API** — Express + PostgreSQL + Socket.io (`plateau-transit-backend`)
- **DEMO MODE** — persistent amber banner + first-open modal; all simulated ETAs labelled `est.`
- **SQL Explorer** removed (analytics tab)
- **TEC-style Vehicle Detail** screen — matches Lines-path design; "Change destination" button
- **Service Worker** — versioned cache, offline fallback, background sync queue
- **Error monitor** — `window.onerror` → localStorage error log + PostHog integration
- **Weekly audit script** — `audit/weekly-route-audit.js`

### Changed
- `statusLive()` always returns `false` — no wifi icon shown until real GPS connected
- `statusLabel()` — "Arrival time is accurate" → "Estimated arrival (demo)"
- `fmtEta()` — removed stale "pm" suffix from time strings
- Info banner text — "GTFS-RT data" → "How our simulated timetables work"
- Analytics nav button removed from bottom nav

### Fixed
- Unescaped apostrophe in CASE concept string (`SQL's`) breaking JS parse
- `vehMap` height now 120px (was unconstrained causing layout shift)

### SW Cache
- `CACHE_VERSION = 'pt-v2026.03.22-1'`

---

## [v2026.03.18-1] 2026-03-18 (v20)

### Added
- Plateau Transit v20 — base version prior to SQL Explorer addition

### SW Cache
- `CACHE_VERSION = 'pt-v2026.03.18-1'`

---

<!-- ─────────────────────────────────────────
     HOW TO CUT A RELEASE
     ─────────────────────────────────────────
1.  Make your changes to the PWA HTML file
2.  Decide the new version:  vYYYY.MM.DD-N  (increment N if multiple releases same day)
3.  Add a new ## [vYYYY.MM.DD-N] section above with:
    - Added / Changed / Fixed / Removed bullets
    - The new CACHE_VERSION string at the bottom of the section
4.  Update CACHE_VERSION in sw.js to match
5.  Update APP_VERSION meta tag in the PWA <head> to match
6.  Deploy. The new SW will install, activate, and clear old caches automatically.
7.  Verify: open DevTools → Application → Cache Storage → confirm new cache name exists
    and old cache name is gone.
──────────────────────────────────────────── -->

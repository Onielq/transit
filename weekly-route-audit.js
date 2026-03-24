#!/usr/bin/env node
// audit/weekly-route-audit.js
// ─────────────────────────────────────────────────────────────────────
// Plateau Transit — Weekly Route Data Accuracy Check (Layer 3.1)
//
// Run every Monday morning before peak hours:
//   node audit/weekly-route-audit.js
//   node audit/weekly-route-audit.js --routes 101,202,305  (specific routes)
//   node audit/weekly-route-audit.js --sample 5            (5 random routes)
//   node audit/weekly-route-audit.js --all                 (all 60 routes)
//
// Output: terminal report + audit/audit-log.jsonl (append-only log)
// ─────────────────────────────────────────────────────────────────────

import { readFileSync, appendFileSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dir = dirname(fileURLToPath(import.meta.url));
const LOG   = join(__dir, 'audit-log.jsonl');

// ─── Source of truth: RURA official data ─────────────────────────────
// Update these when RURA announces changes.
// Format: { [routeNum]: { fare, from, to, stops: [stopName,...] } }
// This is the reference you check the app data against each Monday.

const RURA_REFERENCE = {
  // ── Corridor A ──
  '101': { fare: 307,  from: 'Remera',    to: 'Downtown',   corridor: 'A' },
  '102': { fare: 741,  from: 'Kabuga',    to: 'Nyabugogo',  corridor: 'A' },
  '103': { fare: 484,  from: 'Downtown',  to: 'Rubirizi',   corridor: 'A' },
  '105': { fare: 355,  from: 'Remera',    to: 'Nyabugogo',  corridor: 'A' },
  '108': { fare: 256,  from: 'Remera',    to: 'Nyanza',     corridor: 'A' },
  '109': { fare: 306,  from: 'Remera',    to: 'Bwerankori', corridor: 'A' },
  '112': { fare: 307,  from: 'Remera',    to: 'Nyabugogo',  corridor: 'A' },
  '120': { fare: 295,  from: 'Remera',    to: 'SEZ',        corridor: 'A' },
  '124': { fare: 741,  from: 'Downtown',  to: 'Kabuga',     corridor: 'A' },
  '125': { fare: 267,  from: 'Remera',    to: 'Busanza',    corridor: 'A' },
  // ── Corridor B ──
  '106': { fare: 269,  from: 'Remera',    to: 'Ndera',      corridor: 'B' },
  '107': { fare: 384,  from: 'Remera',    to: 'Masaka',     corridor: 'B' },
  '111': { fare: 420,  from: 'Remera',    to: 'Kabuga',     corridor: 'B' },
  '113': { fare: 227,  from: 'Remera',    to: 'Busanza',    corridor: 'B' },
  '114': { fare: 224,  from: 'Remera',    to: 'Kibaya',     corridor: 'B' },
  '115': { fare: 291,  from: 'Remera',    to: 'Busanza',    corridor: 'B' },
  '118': { fare: 565,  from: 'Nyabugogo', to: 'Kibaya',     corridor: 'B' },
  // ── Corridor C ──
  '202': { fare: 340,  from: 'Nyanza',    to: 'Downtown',   corridor: 'C' },
  '203': { fare: 390,  from: 'Nyanza',    to: 'Downtown',   corridor: 'C' },
  '204': { fare: 422,  from: 'Nyanza',    to: 'Nyabugogo',  corridor: 'C' },
  '208': { fare: 278,  from: 'Nyanza',    to: 'Gahanga',    corridor: 'C' },
  '211': { fare: 364,  from: 'Nyanza',    to: 'Kacyiru',    corridor: 'C' },
  '213': { fare: 323,  from: 'Nyanza',    to: 'Kimironko',  corridor: 'C' },
  '214': { fare: 422,  from: 'Nyanza',    to: 'Nyabugogo',  corridor: 'C' },
  // ── Corridor D ──
  '205': { fare: 377,  from: 'Downtown',  to: 'Bwerankori', corridor: 'D' },
  '206': { fare: 382,  from: 'Nyabugogo', to: 'Bwerankori', corridor: 'D' },
  '212': { fare: 383,  from: 'Nyabugogo', to: 'St. Joseph', corridor: 'D' },
  '215': { fare: 408,  from: 'Kimironko', to: 'Bwerankori', corridor: 'D' },
  // ── Corridor E ──
  '301': { fare: 403,  from: 'Downtown',  to: 'Kinyinya',   corridor: 'E' },
  '302': { fare: 355,  from: 'Kimironko', to: 'Downtown',   corridor: 'E' },
  '303': { fare: 301,  from: 'Downtown',  to: 'Batsinda',   corridor: 'E' },
  '304': { fare: 371,  from: 'Downtown',  to: 'Kacyiru',    corridor: 'E' },
  '306': { fare: 301,  from: 'Kimironko', to: 'Birembo',    corridor: 'E' },
  '308': { fare: 484,  from: 'Downtown',  to: 'Musave',     corridor: 'E' },
  '309': { fare: 301,  from: 'Kimironko', to: 'Kinyinya',   corridor: 'E' },
  '313': { fare: 301,  from: 'Downtown',  to: 'Batsinda',   corridor: 'E' },
  '316': { fare: 204,  from: 'Kimironko', to: 'Musave',     corridor: 'E' },
  '318': { fare: 301,  from: 'Kimironko', to: 'Batsinda',   corridor: 'E' },
  '322': { fare: 355,  from: 'Kimironko', to: 'Masaka',     corridor: 'E' },
  '325': { fare: 420,  from: 'Kabuga',    to: 'Kimironko',  corridor: 'E' },
  // ── Corridor F ──
  '305': { fare: 371,  from: 'Nyabugogo', to: 'Kimironko',  corridor: 'F' },
  '310': { fare: 301,  from: 'Nyabugogo', to: 'Batsinda',   corridor: 'F' },
  '311': { fare: 301,  from: 'Nyabugogo', to: 'Batsinda',   corridor: 'F' },
  '314': { fare: 339,  from: 'Nyabugogo', to: 'Kimironko',  corridor: 'F' },
  '315': { fare: 387,  from: 'Nyabugogo', to: 'Kinyinya',   corridor: 'F' },
  '317': { fare: 342,  from: 'Downtown',  to: 'Kinyinya',   corridor: 'F' },
  '321': { fare: 462,  from: 'Nyabugogo', to: 'Gasanze',    corridor: 'F' },
  // ── Corridor G ──
  '401': { fare: 243,  from: 'Downtown',  to: 'Nyamirambo', corridor: 'G' },
  '402': { fare: 307,  from: 'Downtown',  to: 'Nyamirambo', corridor: 'G' },
  '403': { fare: 420,  from: 'Downtown',  to: 'Nyacyonga',  corridor: 'G' },
  '404': { fare: 383,  from: 'Nyabugogo', to: 'Bishenyi',   corridor: 'G' },
  '405': { fare: 484,  from: 'Nyabugogo', to: 'Kanyinya',   corridor: 'G' },
  '406': { fare: 377,  from: 'Mageragere',to: 'Nyamirambo', corridor: 'G' },
  '407': { fare: 306,  from: 'Nyabugogo', to: 'Nyacyonga',  corridor: 'G' },
  '414': { fare: 310,  from: 'Nyabugogo', to: 'Karama',     corridor: 'G' },
  '415': { fare: 205,  from: 'Nyabugogo', to: 'Downtown',   corridor: 'G' },
  '416': { fare: 383,  from: 'Nyabugogo', to: 'Gihara',     corridor: 'G' },
  '417': { fare: 205,  from: 'Nyamirambo',to: 'Karama',     corridor: 'G' },
  '418': { fare: 278,  from: 'Nyabugogo', to: 'Bweramvura', corridor: 'G' },
  '419': { fare: 307,  from: 'Nyabugogo', to: 'Cyumbati',   corridor: 'G' },
};

// ─── App data — paste latest ROUTES from the PWA here before auditing ─
// This mirrors what's in the HTML. Run this script to compare.
const APP_DATA = [
  {num:'101',fare:307, from:'Remera',    to:'Downtown',   cor:'A'},
  {num:'102',fare:741, from:'Kabuga',    to:'Nyabugogo',  cor:'A'},
  {num:'103',fare:484, from:'Downtown',  to:'Rubirizi',   cor:'A'},
  {num:'105',fare:355, from:'Remera',    to:'Nyabugogo',  cor:'A'},
  {num:'108',fare:256, from:'Remera',    to:'Nyanza',     cor:'A'},
  {num:'109',fare:306, from:'Remera',    to:'Bwerankori', cor:'A'},
  {num:'112',fare:307, from:'Remera',    to:'Nyabugogo',  cor:'A'},
  {num:'120',fare:295, from:'Remera',    to:'SEZ',        cor:'A'},
  {num:'124',fare:741, from:'Downtown',  to:'Kabuga',     cor:'A'},
  {num:'125',fare:267, from:'Remera',    to:'Busanza',    cor:'A'},
  {num:'106',fare:269, from:'Remera',    to:'Ndera',      cor:'B'},
  {num:'107',fare:384, from:'Remera',    to:'Masaka',     cor:'B'},
  {num:'111',fare:420, from:'Remera',    to:'Kabuga',     cor:'B'},
  {num:'113',fare:227, from:'Remera',    to:'Busanza',    cor:'B'},
  {num:'114',fare:224, from:'Remera',    to:'Kibaya',     cor:'B'},
  {num:'115',fare:291, from:'Remera',    to:'Busanza',    cor:'B'},
  {num:'118',fare:565, from:'Nyabugogo', to:'Kibaya',     cor:'B'},
  {num:'202',fare:340, from:'Nyanza',    to:'Downtown',   cor:'C'},
  {num:'203',fare:390, from:'Nyanza',    to:'Downtown',   cor:'C'},
  {num:'204',fare:422, from:'Nyanza',    to:'Nyabugogo',  cor:'C'},
  {num:'208',fare:278, from:'Nyanza',    to:'Gahanga',    cor:'C'},
  {num:'211',fare:364, from:'Nyanza',    to:'Kacyiru',    cor:'C'},
  {num:'213',fare:323, from:'Nyanza',    to:'Kimironko',  cor:'C'},
  {num:'214',fare:422, from:'Nyanza',    to:'Nyabugogo',  cor:'C'},
  {num:'205',fare:377, from:'Downtown',  to:'Bwerankori', cor:'D'},
  {num:'206',fare:382, from:'Nyabugogo', to:'Bwerankori', cor:'D'},
  {num:'212',fare:383, from:'Nyabugogo', to:'St. Joseph', cor:'D'},
  {num:'215',fare:408, from:'Kimironko', to:'Bwerankori', cor:'D'},
  {num:'301',fare:403, from:'Downtown',  to:'Kinyinya',   cor:'E'},
  {num:'302',fare:355, from:'Kimironko', to:'Downtown',   cor:'E'},
  {num:'303',fare:301, from:'Downtown',  to:'Batsinda',   cor:'E'},
  {num:'304',fare:371, from:'Downtown',  to:'Kacyiru',    cor:'E'},
  {num:'306',fare:301, from:'Kimironko', to:'Birembo',    cor:'E'},
  {num:'308',fare:484, from:'Downtown',  to:'Musave',     cor:'E'},
  {num:'309',fare:301, from:'Kimironko', to:'Kinyinya',   cor:'E'},
  {num:'313',fare:301, from:'Downtown',  to:'Batsinda',   cor:'E'},
  {num:'316',fare:204, from:'Kimironko', to:'Musave',     cor:'E'},
  {num:'318',fare:301, from:'Kimironko', to:'Batsinda',   cor:'E'},
  {num:'322',fare:355, from:'Kimironko', to:'Masaka',     cor:'E'},
  {num:'325',fare:420, from:'Kabuga',    to:'Kimironko',  cor:'E'},
  {num:'305',fare:371, from:'Nyabugogo', to:'Kimironko',  cor:'F'},
  {num:'310',fare:301, from:'Nyabugogo', to:'Batsinda',   cor:'F'},
  {num:'311',fare:301, from:'Nyabugogo', to:'Batsinda',   cor:'F'},
  {num:'314',fare:339, from:'Nyabugogo', to:'Kimironko',  cor:'F'},
  {num:'315',fare:387, from:'Nyabugogo', to:'Kinyinya',   cor:'F'},
  {num:'317',fare:342, from:'Downtown',  to:'Kinyinya',   cor:'F'},
  {num:'321',fare:462, from:'Nyabugogo', to:'Gasanze',    cor:'F'},
  {num:'401',fare:243, from:'Downtown',  to:'Nyamirambo', cor:'G'},
  {num:'402',fare:307, from:'Downtown',  to:'Nyamirambo', cor:'G'},
  {num:'403',fare:420, from:'Downtown',  to:'Nyacyonga',  cor:'G'},
  {num:'404',fare:383, from:'Nyabugogo', to:'Bishenyi',   cor:'G'},
  {num:'405',fare:484, from:'Nyabugogo', to:'Kanyinya',   cor:'G'},
  {num:'406',fare:377, from:'Mageragere',to:'Nyamirambo', cor:'G'},
  {num:'407',fare:306, from:'Nyabugogo', to:'Nyacyonga',  cor:'G'},
  {num:'414',fare:310, from:'Nyabugogo', to:'Karama',     cor:'G'},
  {num:'415',fare:205, from:'Nyabugogo', to:'Downtown',   cor:'G'},
  {num:'416',fare:383, from:'Nyabugogo', to:'Gihara',     cor:'G'},
  {num:'417',fare:205, from:'Nyamirambo',to:'Karama',     cor:'G'},
  {num:'418',fare:278, from:'Nyabugogo', to:'Bweramvura', cor:'G'},
  {num:'419',fare:307, from:'Nyabugogo', to:'Cyumbati',   cor:'G'},
];

// ─── CLI arg parsing ──────────────────────────────────────────────────
const args = process.argv.slice(2);
const flagIndex = (f) => args.indexOf(f);
const flagVal   = (f) => { const i = flagIndex(f); return i !== -1 ? args[i+1] : null; };

let routesToCheck;
if (flagIndex('--all') !== -1) {
  routesToCheck = APP_DATA;
} else if (flagVal('--routes')) {
  const nums = flagVal('--routes').split(',');
  routesToCheck = APP_DATA.filter(r => nums.includes(r.num));
} else {
  // Default: 5 random routes (the weekly spot-check)
  const sampleSize = parseInt(flagVal('--sample') || '5');
  const shuffled = [...APP_DATA].sort(() => Math.random() - 0.5);
  routesToCheck = shuffled.slice(0, sampleSize);
}

// ─── Audit ────────────────────────────────────────────────────────────
const now    = new Date();
const dateStr = now.toISOString().split('T')[0];
const issues  = [];
const passing = [];

console.log('\n╔════════════════════════════════════════════════╗');
console.log(`║  Plateau Transit — Weekly Route Audit          ║`);
console.log(`║  ${dateStr}  ·  Checking ${routesToCheck.length} route(s)`.padEnd(50) + '║');
console.log('╚════════════════════════════════════════════════╝\n');

for (const appRoute of routesToCheck) {
  const ref = RURA_REFERENCE[appRoute.num];
  const routeIssues = [];

  if (!ref) {
    routeIssues.push({ field: 'existence', detail: `Route ${appRoute.num} found in app but NOT in RURA reference — may have been removed` });
  } else {
    // Fare check
    if (appRoute.fare !== ref.fare) {
      routeIssues.push({
        field: 'fare',
        detail: `App: ${appRoute.fare} RWF — RURA: ${ref.fare} RWF — DIFF: ${appRoute.fare - ref.fare > 0 ? '+' : ''}${appRoute.fare - ref.fare} RWF`,
      });
    }
    // Corridor check
    if (appRoute.cor !== ref.corridor) {
      routeIssues.push({
        field: 'corridor',
        detail: `App: ${appRoute.cor} — RURA: ${ref.corridor}`,
      });
    }
    // Destination check (fuzzy — RURA names sometimes differ slightly)
    const toMatch = appRoute.to.toLowerCase().includes(ref.to.toLowerCase()) ||
                    ref.to.toLowerCase().includes(appRoute.to.toLowerCase());
    if (!toMatch) {
      routeIssues.push({
        field: 'destination',
        detail: `App: "${appRoute.to}" — RURA: "${ref.to}"`,
      });
    }
  }

  const status = routeIssues.length === 0 ? '✓' : '✗';
  const label  = `  ${status} Route ${appRoute.num.padEnd(4)} ${(appRoute.from + ' → ' + appRoute.to).padEnd(36)}`;

  if (routeIssues.length === 0) {
    console.log(`${label} OK`);
    passing.push(appRoute.num);
  } else {
    console.log(`${label} ⚠  ${routeIssues.length} issue(s)`);
    routeIssues.forEach(i => console.log(`       ${i.field.toUpperCase()}: ${i.detail}`));
    issues.push({ route: appRoute.num, issues: routeIssues });
  }
}

// ─── Check for RURA routes missing from app ───────────────────────────
if (flagIndex('--all') !== -1) {
  const appNums = new Set(APP_DATA.map(r => r.num));
  const missing = Object.keys(RURA_REFERENCE).filter(n => !appNums.has(n));
  if (missing.length) {
    console.log(`\n  ⚠  Routes in RURA reference but MISSING from app: ${missing.join(', ')}`);
    missing.forEach(n => issues.push({ route: n, issues: [{ field: 'missing', detail: 'In RURA reference but not in app data' }] }));
  }
}

// ─── Summary ──────────────────────────────────────────────────────────
console.log('\n─────────────────────────────────────────────────');
console.log(`  Checked:  ${routesToCheck.length} routes`);
console.log(`  Passing:  ${passing.length}`);
console.log(`  Issues:   ${issues.length}`);

if (issues.length === 0) {
  console.log('\n  ✅ All checked routes match RURA reference. No action needed.');
  console.log('  Success signal: 0 user reports of incorrect data expected this week.\n');
} else {
  console.log('\n  ❌ Issues found. Fix before Monday peak hours.\n');
  console.log('  Fix checklist:');
  issues.forEach(({ route, issues: ilist }) => {
    ilist.forEach(i => {
      console.log(`  [ ] Route ${route} — ${i.field}: ${i.detail}`);
    });
  });
  console.log('\n  After fixing: re-run this script with the same --routes flag to verify.');
  console.log('  Then bump CACHE_VERSION in sw.js and update CHANGELOG.md.\n');
}

// ─── Append to audit log ──────────────────────────────────────────────
const logEntry = {
  ts:         now.toISOString(),
  checked:    routesToCheck.map(r => r.num),
  pass_count: passing.length,
  fail_count: issues.length,
  issues,
};
appendFileSync(LOG, JSON.stringify(logEntry) + '\n');
console.log(`  Audit logged → ${LOG}`);
console.log('─────────────────────────────────────────────────\n');

process.exit(issues.length > 0 ? 1 : 0);

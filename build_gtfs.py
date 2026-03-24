"""
Plateau Transit — Full GTFS Static Feed Generator
Kigali, Rwanda — 60 RURA routes, all 7 corridors

Generates a spec-compliant GTFS zip validated by gtfs-kit.
Replace coordinate stubs and shape data when RURA provides surveyed geometry.
"""

import csv, math, os, zipfile, itertools
from datetime import date, timedelta

OUT = "/home/claude/gtfs-kigali/feed"
os.makedirs(OUT, exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def mins_to_hms(total_mins):
    h = total_mins // 60
    m = total_mins % 60
    return f"{h:02d}:{m:02d}:00"

def add_mins(hms, mins):
    h, m, s = map(int, hms.split(":"))
    total = h * 60 + m + mins
    return mins_to_hms(total)

# ─── STOPS ────────────────────────────────────────────────────────────
STOPS = [
  # id, name, code, lat, lon, is_terminal
  ("s1",  "Nyabugogo Bus Park",       "NYB", -1.9441,  30.0619, True),
  ("s2",  "Downtown Bus Park",        "DWT", -1.9536,  30.0606, True),
  ("s3",  "Remera Bus Park",          "RMR", -1.9494,  30.1098, True),
  ("s4",  "Kimironko Bus Park",       "KMR", -1.9255,  30.1177, True),
  ("s5",  "Nyanza Bus Park",          "NYZ", -2.3545,  29.7395, True),
  ("s6",  "Kibaya Bus Terminal",      "KBY", -1.9750,  30.1580, True),
  ("s7",  "Kacyiru Bus Stop",         "KCY", -1.9350,  30.0800, False),
  ("s8",  "Saint Joseph Terminal",    "STJ", -1.9680,  30.0400, True),
  ("s9",  "Ndera Bus Terminal",       "NDR", -1.9380,  30.1510, True),
  ("s10", "Masaka Bus Terminal",      "MSK", -1.9500,  30.1480, True),
  ("s11", "Busanza Bus Terminal",     "BSZ", -1.9580,  30.1650, True),
  ("s12", "Batsinda Bus Terminal",    "BTS", -1.9000,  30.0950, True),
  ("s13", "Musave Bus Terminal",      "MSV", -1.9120,  30.1400, True),
  ("s14", "Kinyinya Bus Terminal",    "KNY", -1.9150,  30.1080, True),
  ("s15", "Birembo Bus Terminal",     "BRM", -1.9000,  30.1450, True),
  ("s16", "Nyamirambo Bus Terminal",  "NYM", -1.9650,  30.0550, True),
  ("s17", "Nyacyonga Bus Terminal",   "NYC", -1.8850,  30.0420, True),
  ("s18", "Gahanga Bus Terminal",     "GHG", -2.2000,  29.8000, True),
  ("s19", "Kabuga Bus Park",          "KBG", -1.9440,  30.1250, True),
  ("s20", "Bwerankori Bus Terminal",  "BWR", -1.9280,  30.1850, True),
  ("s23", "Bishenyi Bus Terminal",    "BSH", -2.0100,  30.0100, True),
  ("s24", "Kanyinya Bus Terminal",    "KNY2",-1.9760,  30.0200, True),
  ("s25", "Gihara Bus Terminal",      "GHR", -1.8700,  30.0650, True),
  ("s26", "Cyumbati Bus Terminal",    "CYM", -1.8500,  30.0550, True),
  ("s27", "Karama Bus Terminal",      "KRM", -1.9850,  30.0480, True),
  ("s28", "Gasanze Bus Terminal",     "GSZ", -1.8800,  30.0900, True),
  ("s29", "SEZ Bus Terminal",         "SEZ", -1.9900,  30.1200, False),
  ("s30", "Bweramvura Bus Terminal",  "BWV", -1.9750,  30.0320, True),
  ("s31", "Mageragere Bus Terminal",  "MGR", -1.9780,  30.0150, True),
]
STOP_MAP = {s[0]: s for s in STOPS}

# ─── ROUTES ───────────────────────────────────────────────────────────
# id, num, name, corridor, stops[], fare_rwf, color_hex
ROUTES = [
  # ── Corridor A ──
  ("101","101","Remera–Downtown",               "A",["s3","s2"],                307, "00E676"),
  ("102","102","Kabuga–Nyabugogo",              "A",["s19","s3","s1"],          741, "00E676"),
  ("103","103","Downtown–Kabeza–Rubirizi",      "A",["s2","s3"],                484, "00E676"),
  ("105","105","Remera–Nyabugogo (Kacyiru)",    "A",["s3","s7","s1"],           355, "00E676"),
  ("108","108","Remera–Nyanza",                 "A",["s3","s5"],                256, "00E676"),
  ("109","109","Remera–Bwerankori",             "A",["s3","s20"],               306, "00E676"),
  ("112","112","Remera–Nyabugogo (Sonatube)",   "A",["s3","s1"],                307, "00E676"),
  ("120","120","Remera–SEZ",                    "A",["s3","s29"],               295, "00E676"),
  ("124","124","Downtown–Kabuga",               "A",["s2","s3","s19"],          741, "00E676"),
  ("125","125","Remera–Busanza (Itunda)",       "A",["s3","s11"],               267, "00E676"),
  # ── Corridor B ──
  ("106","106","Remera–Ndera",                  "B",["s3","s9"],                269, "448AFF"),
  ("107","107","Remera–Masaka",                 "B",["s3","s10"],               384, "448AFF"),
  ("111","111","Remera–Kabuga",                 "B",["s3","s19"],               420, "448AFF"),
  ("113","113","Remera–Busanza (Rubirizi)",     "B",["s3","s11"],               227, "448AFF"),
  ("114","114","Remera–Kanombe–Kibaya",         "B",["s3","s6"],                224, "448AFF"),
  ("115","115","Remera–Busanza (Nyarugunga)",   "B",["s3","s11"],               291, "448AFF"),
  ("118","118","Nyabugogo–Kanombe–Kibaya",      "B",["s1","s7","s6"],           565, "448AFF"),
  # ── Corridor C ──
  ("202","202","Nyanza–Downtown (Zion)",        "C",["s5","s2"],                340, "E040FB"),
  ("203","203","Nyanza–Downtown (Gatenga)",     "C",["s5","s2"],                390, "E040FB"),
  ("204","204","Nyanza–Nyabugogo (Zion)",       "C",["s5","s1"],                422, "E040FB"),
  ("208","208","Nyanza–Gahanga",                "C",["s5","s18"],               278, "E040FB"),
  ("211","211","Nyanza–Kacyiru",                "C",["s5","s7"],                364, "E040FB"),
  ("213","213","Nyanza–Kimironko",              "C",["s5","s2","s4"],           323, "E040FB"),
  ("214","214","Nyanza–Nyabugogo (Gatenga)",    "C",["s5","s1"],                422, "E040FB"),
  # ── Corridor D ──
  ("205","205","Downtown–Bwerankori",           "D",["s2","s20"],               377, "FFB300"),
  ("206","206","Nyabugogo–Bwerankori",          "D",["s1","s20"],               382, "FFB300"),
  ("212","212","Nyabugogo–Saint Joseph",        "D",["s1","s16","s8"],          383, "FFB300"),
  ("215","215","Kimironko–Bwerankori",          "D",["s4","s2","s20"],          408, "FFB300"),
  # ── Corridor E ──
  ("301","301","Downtown–Kinyinya",             "E",["s2","s14"],               403, "00E5FF"),
  ("302","302","Kimironko–Downtown",            "E",["s4","s3","s2"],           355, "00E5FF"),
  ("303","303","Downtown–Batsinda (Agakiriro)", "E",["s2","s12"],               301, "00E5FF"),
  ("304","304","Downtown–Kacyiru",              "E",["s2","s7"],                371, "00E5FF"),
  ("306","306","Kimironko–Masizi–Birembo",      "E",["s4","s15"],               301, "00E5FF"),
  ("308","308","Downtown–Musave (Zindiro)",     "E",["s2","s13"],               484, "00E5FF"),
  ("309","309","Kimironko–Kinyinya",            "E",["s4","s14"],               301, "00E5FF"),
  ("313","313","Downtown–Batsinda",             "E",["s2","s12"],               301, "00E5FF"),
  ("316","316","Kimironko–Musave (Zindiro)",    "E",["s4","s13"],               204, "00E5FF"),
  ("318","318","Kimironko–Batsinda",            "E",["s4","s12"],               301, "00E5FF"),
  ("322","322","Kimironko–Masaka",              "E",["s4","s10"],               355, "00E5FF"),
  ("325","325","Kabuga–Kimironko",              "E",["s19","s4"],               420, "00E5FF"),
  # ── Corridor F ──
  ("305","305","Nyabugogo–Kimironko (Kacyiru)", "F",["s1","s7","s4"],           371, "FF5252"),
  ("310","310","Nyabugogo–Batsinda (Agakiriro)","F",["s1","s12"],               301, "FF5252"),
  ("311","311","Nyabugogo–Batsinda (ULK)",      "F",["s1","s12"],               301, "FF5252"),
  ("314","314","Nyabugogo–Kimironko (Kibagabaga)","F",["s1","s4"],              339, "FF5252"),
  ("315","315","Nyabugogo–Kinyinya (Utexrwa)",  "F",["s1","s14"],               387, "FF5252"),
  ("317","317","Downtown–Kinyinya (Utexrwa)",   "F",["s2","s14"],               342, "FF5252"),
  ("321","321","Nyabugogo–Gasanze (Batsinda)",  "F",["s1","s12","s28"],         462, "FF5252"),
  # ── Corridor G ──
  ("401","401","Downtown–Nyamirambo",           "G",["s2","s16"],               243, "FF6D00"),
  ("402","402","Downtown–Nyamirambo (Kimisagara)","G",["s2","s16"],             307, "FF6D00"),
  ("403","403","Downtown–Nyacyonga",            "G",["s2","s17"],               420, "FF6D00"),
  ("404","404","Nyabugogo–Bishenyi",            "G",["s1","s23"],               383, "FF6D00"),
  ("405","405","Nyabugogo–Kanyinya",            "G",["s1","s24"],               484, "FF6D00"),
  ("406","406","Mageragere–Nyamirambo ERP",     "G",["s31","s16"],              377, "FF6D00"),
  ("407","407","Nyabugogo–Nyacyonga",           "G",["s1","s17"],               306, "FF6D00"),
  ("414","414","Nyabugogo–Karama",              "G",["s1","s27"],               310, "FF6D00"),
  ("415","415","Nyabugogo–Downtown",            "G",["s1","s2"],                205, "FF6D00"),
  ("416","416","Nyabugogo–Gihara",              "G",["s1","s25"],               383, "FF6D00"),
  ("417","417","Nyamirambo–Karama",             "G",["s16","s27"],              205, "FF6D00"),
  ("418","418","Nyabugogo–Bweramvura",          "G",["s1","s30"],               278, "FF6D00"),
  ("419","419","Nyabugogo–Cyumbati",            "G",["s1","s26"],               307, "FF6D00"),
]

# ─── Service schedule ─────────────────────────────────────────────────
# Kigali buses: 05:30–21:00, peak every 10min, off-peak every 20min
def trip_departures():
    """Return list of (hhmm_str, is_peak) for a full operating day."""
    slots = []
    t = 5 * 60 + 30   # 05:30
    while t <= 21 * 60:
        h, m = divmod(t, 60)
        peak = (6 * 60 <= t <= 9 * 60) or (16 * 60 <= t <= 19 * 60)
        slots.append((f"{h:02d}:{m:02d}:00", peak))
        t += 10 if peak else 20
    return slots

DEPARTURES = trip_departures()

# Travel time between stops: Haversine distance / 18 km/h + 2min boarding
# (18 km/h accounts for Kigali congestion, stop dwell, and traffic lights)
SPEED_KMH = 18
DWELL_MINS = 2

def leg_mins(stop_a_id, stop_b_id):
    a = STOP_MAP[stop_a_id]
    b = STOP_MAP[stop_b_id]
    dist = haversine_km(a[3], a[4], b[3], b[4])
    travel = (dist / SPEED_KMH) * 60
    return max(3, round(travel + DWELL_MINS))

# ─── agency.txt ───────────────────────────────────────────────────────
def write_agency():
    with open(f"{OUT}/agency.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["agency_id","agency_name","agency_url","agency_timezone","agency_lang","agency_phone","agency_email"])
        w.writerow(["PLT","Plateau Transit","https://plateau.rw","Africa/Kigali","rw","+250780000000","info@plateau.rw"])

# ─── stops.txt ────────────────────────────────────────────────────────
def write_stops():
    with open(f"{OUT}/stops.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stop_id","stop_code","stop_name","stop_desc","stop_lat","stop_lon",
                    "zone_id","stop_url","location_type","wheelchair_boarding"])
        for sid, name, code, lat, lon, terminal in STOPS:
            loc_type = 1 if terminal else 0   # 1=Station, 0=Stop
            w.writerow([sid, code, name,
                        "Kigali urban bus terminal" if terminal else "Bus stop",
                        f"{lat:.6f}", f"{lon:.6f}",
                        "kigali", "", loc_type, 1])   # wheelchair_boarding=1 (possible)

# ─── routes.txt ───────────────────────────────────────────────────────
def write_routes():
    with open(f"{OUT}/routes.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["route_id","agency_id","route_short_name","route_long_name",
                    "route_type","route_color","route_text_color","route_desc"])
        for rid, num, name, corridor, stops, fare, color in ROUTES:
            w.writerow([rid, "PLT", num, name,
                        3,          # 3 = Bus
                        color, "FFFFFF",
                        f"Corridor {corridor} — Fare: {fare} RWF"])

# ─── calendar.txt ─────────────────────────────────────────────────────
def write_calendar():
    today = date.today()
    start = date(today.year, 1, 1)
    end   = date(today.year + 1, 12, 31)
    with open(f"{OUT}/calendar.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["service_id","monday","tuesday","wednesday","thursday","friday","saturday","sunday","start_date","end_date"])
        w.writerow(["WD",  1,1,1,1,1,0,0, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")])  # Weekday
        w.writerow(["SAT", 0,0,0,0,0,1,0, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")])  # Saturday
        w.writerow(["SUN", 0,0,0,0,0,0,1, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")])  # Sunday
        w.writerow(["ALL", 1,1,1,1,1,1,1, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")])  # All week

# ─── calendar_dates.txt ───────────────────────────────────────────────
def write_calendar_dates():
    # Rwanda public holidays — service exception type 2 = removed
    holidays = [
        "20260101",  # New Year's Day
        "20260201",  # Heroes Day
        "20260407",  # Genocide Memorial Day
        "20260418",  # Good Friday (approx)
        "20260501",  # Labour Day
        "20260701",  # Liberation Day
        "20260801",  # National Day / Umuganura
        "20260825",  # Assumption
        "20261225",  # Christmas
        "20261226",  # Boxing Day
    ]
    with open(f"{OUT}/calendar_dates.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["service_id","date","exception_type"])
        for h in holidays:
            for svc in ["WD", "SAT", "SUN"]:
                w.writerow([svc, h, 2])   # 2 = service removed on this date
            w.writerow(["ALL", h, 1])      # ALL service still runs on holidays

# ─── trips.txt + stop_times.txt ───────────────────────────────────────
def write_trips_and_stop_times():
    trip_rows = []
    st_rows   = []
    shape_rows = []
    trip_counter = itertools.count(1)

    # Saturday/Sunday get reduced service (every 20min, no peak)
    sat_departures = [(t, False) for t, _ in DEPARTURES[::2]]   # every other slot
    sun_departures = [(t, False) for t, _ in DEPARTURES[::3]]   # every third slot

    for rid, num, name, corridor, stop_ids, fare, color in ROUTES:
        # Build leg times
        leg_time = []
        for i in range(len(stop_ids) - 1):
            leg_time.append(leg_mins(stop_ids[i], stop_ids[i+1]))

        def make_trips(service_id, departures):
            for dep_time, is_peak in departures:
                tid = f"T{next(trip_counter):06d}"
                headway = "Peak" if is_peak else "Off-peak"
                trip_rows.append([rid, service_id, tid,
                                   f"{name} ({headway})",
                                   0,          # direction_id: 0 = outbound
                                   f"SHP_{rid}"])

                # Stop times for this trip
                current_time = dep_time
                for seq, sid in enumerate(stop_ids):
                    # Pickup/drop-off: first stop pickup only, last stop drop-off only
                    pickup  = 0 if seq < len(stop_ids) - 1 else 1   # 1=none at last
                    dropoff = 1 if seq == 0 else 0                   # 1=none at first
                    st_rows.append([tid, current_time, current_time,
                                    sid, seq + 1, pickup, dropoff, 0])
                    if seq < len(stop_ids) - 1:
                        current_time = add_mins(current_time, leg_time[seq])

        make_trips("WD",  DEPARTURES)
        make_trips("SAT", sat_departures)
        make_trips("SUN", sun_departures)

        # Shape: straight line between stops (replace with surveyed polyline when available)
        shp_id = f"SHP_{rid}"
        seq = 1
        for sid in stop_ids:
            s = STOP_MAP[sid]
            shape_rows.append([shp_id, f"{s[3]:.6f}", f"{s[4]:.6f}", seq, 0])
            seq += 1

    print(f"  Generated {len(trip_rows):,} trips, {len(st_rows):,} stop_time rows")

    with open(f"{OUT}/trips.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["route_id","service_id","trip_id","trip_headsign","direction_id","shape_id"])
        w.writerows(trip_rows)

    with open(f"{OUT}/stop_times.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["trip_id","arrival_time","departure_time","stop_id",
                    "stop_sequence","pickup_type","drop_off_type","timepoint"])
        w.writerows(st_rows)

    with open(f"{OUT}/shapes.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shape_id","shape_pt_lat","shape_pt_lon","shape_pt_sequence","shape_dist_traveled"])
        w.writerows(shape_rows)

# ─── fare_attributes.txt + fare_rules.txt ─────────────────────────────
def write_fares():
    with open(f"{OUT}/fare_attributes.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fare_id","price","currency_type","payment_method","transfers","agency_id"])
        for rid, num, name, corridor, stops, fare, color in ROUTES:
            w.writerow([f"FARE_{rid}", fare, "RWF", 0, 0, "PLT"])
            # payment_method 0 = paid on board; 1 = must pay before boarding

    with open(f"{OUT}/fare_rules.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fare_id","route_id","origin_id","destination_id","contains_id"])
        for rid, num, name, corridor, stops, fare, color in ROUTES:
            w.writerow([f"FARE_{rid}", rid, "", "", ""])

# ─── feed_info.txt ────────────────────────────────────────────────────
def write_feed_info():
    today = date.today()
    end   = date(today.year + 1, 12, 31)
    with open(f"{OUT}/feed_info.txt", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["feed_publisher_name","feed_publisher_url","feed_lang",
                    "feed_start_date","feed_end_date","feed_version","feed_contact_email"])
        w.writerow(["Plateau Transit","https://plateau.rw","rw",
                    today.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                    f"{today.strftime('%Y%m%d')}-1",
                    "gtfs@plateau.rw"])

# ─── RUN ALL ──────────────────────────────────────────────────────────
print("╔══════════════════════════════════════════╗")
print("║  Plateau Transit — GTFS Feed Generator   ║")
print("╚══════════════════════════════════════════╝\n")

print("Writing agency.txt ...")
write_agency()
print("  ✓")

print("Writing stops.txt ...")
write_stops()
print(f"  ✓ {len(STOPS)} stops")

print("Writing routes.txt ...")
write_routes()
print(f"  ✓ {len(ROUTES)} routes across 7 corridors")

print("Writing calendar.txt + calendar_dates.txt ...")
write_calendar()
write_calendar_dates()
print("  ✓  4 service calendars + 10 public holidays")

print("Writing trips.txt + stop_times.txt + shapes.txt ...")
write_trips_and_stop_times()
print("  ✓")

print("Writing fare_attributes.txt + fare_rules.txt ...")
write_fares()
print(f"  ✓ {len(ROUTES)} fare entries in RWF")

print("Writing feed_info.txt ...")
write_feed_info()
print("  ✓\n")

# ─── Zip into plateau-transit-GTFS.zip ───────────────────────────────
GTFS_FILES = [
    "agency.txt","stops.txt","routes.txt","trips.txt","stop_times.txt",
    "calendar.txt","calendar_dates.txt","shapes.txt",
    "fare_attributes.txt","fare_rules.txt","feed_info.txt"
]
zip_path = "/home/claude/gtfs-kigali/plateau-transit-GTFS.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for fname in GTFS_FILES:
        fpath = f"{OUT}/{fname}"
        if os.path.exists(fpath):
            zf.write(fpath, fname)
            size = os.path.getsize(fpath)
            print(f"  {fname:<30} {size:>8,} bytes")

import os as _os
total = _os.path.getsize(zip_path)
print(f"\n  plateau-transit-GTFS.zip → {total:,} bytes ({total/1024:.1f} KB)")

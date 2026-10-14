from datetime import timedelta, date
import requests

CATEGORY_MAP = {
    #"ps": "Protección Solar",
   # "cv": "Cerramientos y Ventana",
    "pa": "Puertas y Automatismos"
}


import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from datetime import timedelta, date, datetime
import requests, urllib3, time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CATEGORY_MAP = {
    "ps": "Protección Solar",
    "cv": "Cerramientos y Ventana",
    "pa": "Puertas y Automatismos",
}

def build_interempresas(code, days=30, needs_firecrawl=False):
    name = CATEGORY_MAP.get(code.lower())
    today = date.today()
    found = []
    prev = None
    for i in range(days):
        dt = today - timedelta(days=i)
        url = f"https://www.interempresas.net/Boletin/NL/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/{code}.html"
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            valid = r.status_code == 200 and "Ruta de acceso no encontrada" not in r.text and len(r.text.strip()) > 80
        except Exception:
            valid = False
        if valid:
            gap = (prev - dt).days if prev else None
            found.append(url)
            print(f"[{name}] {dt}  gap={gap}  ({len(found)})", flush=True)
            prev = dt
    return {"rss": False, "name": name, "feed_urls": found, "needs_firecrawl": needs_firecrawl}

from datetime import datetime

for code in CATEGORY_MAP:
    result = build_interempresas(code)
    dates = []
    for url in result["feed_urls"]:
        parts = url.removesuffix(".html").split("/")
        y, m, d = int(parts[-4]), int(parts[-3]), int(parts[-2])
        dates.append(datetime(y, m, d).date())
    gaps = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
    print(result["name"])
    print("  dates:", dates)
    print("  gaps (days):", gaps)
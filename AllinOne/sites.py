"""
Single source of truth for the newsletter list.

Both process.py and the workflow read this file, so adding a site here adds a
machine to the next run. Nothing else needs editing.

Order matters: the workflow passes each job its position in this list, so don't
reorder it mid-run. Appending to the end is always safe.
"""


from datetime import timedelta,date
import requests

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CATEGORY_MAP = {
    "ps": "Protección Solar",
    "cv": "Cerramientos y Ventana",
    "pa": "Puertas y Automatismos",
}

def build_interempresas(code, days=7, needs_firecrawl=False):
    name = CATEGORY_MAP.get(code.lower())
    today = date.today()
    for i in range(days):
        dt = today - timedelta(days=i)
        url = f"https://www.interempresas.net/Boletin/NL/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/{code}.html"
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            valid = r.status_code == 200 and "Ruta de acceso no encontrada" not in r.text and len(r.text.strip()) > 80
        except Exception:
            valid = False
        if valid:
            return {"rss": False,"name": name, "feed_url": url, "needs_firecrawl": needs_firecrawl}
    #return {"rss": False,"name": name, "feed_url": None, "needs_firecrawl": needs_firecrawl}


SITES = [
{"rss": True,"name": "WindowVision", "feed_url": "https://www.wf-vision.com/feed/", "needs_firecrawl": True},
{"rss": True,"name": "leMoniteur", "feed_url": "https://www.lemoniteur.fr/arc/outboundfeeds/rss/", "needs_firecrawl": False},
{"rss": True,"name": "BauInfoConsult", "feed_url": "https://bauinfoconsult.de/feed/", "needs_firecrawl": False},
{"rss": True,"name": "Geb", "feed_url": "https://www.geb-info.de/rss_feed/geb-rss-feed-meldungen", "needs_firecrawl": False},
{"rss": True,"name": "GlasWelt", "feed_url": "https://www.glaswelt.de/rss_feed/gw-rss-feed-meldungen", "needs_firecrawl": False},
{"rss": True,"name": "Kunstsoff", "feed_url":  "https://www.kunststoffweb.de/rss/", "needs_firecrawl": False},
{"rss": True,"name": "CePro", "feed_url": "https://www.cepro.com/feed/", "needs_firecrawl": False},
{"rss": True,"name": "Orgalim", "feed_url": "https://orgalim.eu/en/feed/", "needs_firecrawl": False},
{"rss": True,"name": "CodeConfiance", "feed_url": "https://www.codeconfiance.com/feed/", "needs_firecrawl": False},
{"rss": False,"name": "TechnicBaie", "feed_url": "https://technicbaie.fr/", "needs_firecrawl": True},
{"rss": True,"name": "Securitynsales", "feed_url": "http://feeds.feedburner.com/SecuritySalesIntegration-News", "needs_firecrawl": False},
{"rss": True,"name": "Haustec", "feed_url": "https://www.haustec.de/rss/heizung", "needs_firecrawl": False}
]


SITES.extend(build_interempresas(code,needs_firecrawl=True) for code in ["PA","CV","PS"])
#print(SITES)
SITES = [s for s in SITES if s]



# Names are used as the job labels in the Actions UI, so they must be unique.
_names = [site["name"] for site in SITES]
assert len(_names) == len(set(_names)), f"duplicate site name in SITES: {_names}"
#print(SITES)
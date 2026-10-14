import ssl
import feedparser
import time as time_module
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from datetime import date, time, timedelta
import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import os


ssl._create_default_https_context = ssl._create_unverified_context

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
_orig = requests.Session.request
def _no_verify(self, method, url, **kwargs):
    kwargs['verify'] = False
    return _orig(self, method, url, **kwargs)
requests.Session.request = _no_verify

import json
from firecrawl import Firecrawl



app = Firecrawl(api_key=os.getenv("FIRE_CRAWL"))
where are the api keys ?

CATEGORY_MAP = {
    "ps": "Protección Solar",
    "cv": "Cerramientos y Ventana",
    "pa": "Puertas y Automatismos",
}

def build_interempresas(code, days=60, needs_firecrawl=False):
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
    return {"rss": False,"name": name, "feed_url": None, "needs_firecrawl": needs_firecrawl}


SITES = [  
    "https://www.batiactu.com/accueil.rss",
    "https://technicbaie.fr/",
    "https://www.lemoniteur.fr/arc/outboundfeeds/rss/",
    "https://bauinfoconsult.de/feed/" ,
    "https://www.geb-info.de/rss_feed/geb-rss-feed-meldungen",
    "https://www.haustec.de/rss/heizung",
    "https://us11.campaign-archive.com/feed?u=3c690b345db3823f0db0cac0f&id=bfc8c22a7a",
    "https://www.kunststoffweb.de/rss/",
    "https://www.cepro.com/feed/",
    "http://feeds.feedburner.com/SecuritySalesIntegration",
    "https://www.wf-vision.com/feed/"
    #"https://www.glaswelt.de/rss_feed/gw-rss-feed-meldungen",
    #"https://us14.campaign-archive.com/feed?u=f8bcf676bb27fc2419df09e98&id=c744bdaafe",
    
    #"https://www.avproglobal.com/blogs/news/tagged/avpro-global.atom"
         
          ]

SITES.extend(build_interempresas(code,needs_firecrawl=True) for code in ["PS"] )#PA,CV,PS
print(SITES)
results = []



# Step 1: Extract article list from homepage
#---------------------------------------------------------------------------------------------
ARTICLE_SCHEMA = {
"type": "object",
"properties": {
    "articles": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "url": {"type": "string"}
            },
            "required": ["title", "url"]
        }
    }
},
"required": ["articles"]
}

def get_articles_from_rss(feed_url, needs_firecrawl=False):
    if needs_firecrawl:
        try:
            result = app.scrape(feed_url, formats=["rawHtml"], proxy="enhanced",max_age=0)
            xml = result.raw_html if hasattr(result, "raw_html") else result.rawHtml
        except Exception as e:
                print(f"⚠ Skipped site {feed_url}: {e}")
    else:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        xml = requests.get(feed_url, headers=headers).text

    feed = feedparser.parse(xml)
    print(f"{len(feed.entries)} articles from {feed_url}")
    return [{"title": e.title, "url": e.link} for e in feed.entries]



def get_articles_from_site(base_url):
    try:
        homepage = app.scrape(
            base_url,
            formats=[{
                "type": "json",
                "schema": ARTICLE_SCHEMA,
                "prompt": "Extract all the articles on the page, each with title url and a 2 line summary, all translated to English."
            }],
            only_main_content=False,
            max_age=0
        )
        data = homepage.json
        print(f"{len(data.get('articles', []))} articles from {base_url}")
        if isinstance(data, dict):
            return data.get("articles", [])
        elif isinstance(data, list):
            return data
        else:
            return []
    except Exception as e:
        print(f"⚠ Skipped site {base_url}: {e}")
        return []


for site in SITES:    
    # step 1---------get the articles--------------------------------------------------------------
    if site.get("rss"):
        print("camino RSS")
        articles_raw = get_articles_from_rss(site["feed_url"], site["needs_firecrawl"])
    else:
        print("camino Normal")
        articles_raw = get_articles_from_site(site["feed_url"])
    # Step 2: Scrape each article and generate a 3-line summary
    for article in articles_raw:
        time_module.sleep(5)#rate limits apply 
        url = article.get("url", "")
        title = article.get("title", "")

        if not url or not url.startswith("http"):
            continue
        try:
            page = app.scrape(
                url,
                formats=["markdown",{
                    "type": "json",
                    "prompt": "Summarize this article in exactly 3 lines. Return a JSON object with a 'summary' field."
                }]
            )

            summary = page.json.get("summary", "") if page.json else ""
            print(page.markdown[:200])
        except Exception as e:
            print(f"⚠ unable to summarize {url}: {e}")
            continue

        
        results.append({
    "site": site["name"],
    "title": title,
    "url": url,
    "summary": summary,
    "content": page.markdown or ""
})

        print(f"✓ {title[:60]}")
        

with open("newsletter.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nDone. {len(results)} articles saved to newsletter.json")

j


"""
# Generate PDF

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch

styles = getSampleStyleSheet()
style_site = ParagraphStyle("site", fontSize=22, fontName="Helvetica-Bold", textColor=colors.HexColor("#2C3E50"), spaceAfter=16, spaceBefore=20)
style_title = ParagraphStyle("title", fontSize=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#1A1A1A"), spaceAfter=4, spaceBefore=14)
style_url = ParagraphStyle("url", fontSize=8, fontName="Helvetica-Oblique", textColor=colors.HexColor("#7F8C8D"), spaceAfter=6)
style_summary = ParagraphStyle("summary", fontSize=10, fontName="Helvetica", textColor=colors.HexColor("#333333"), spaceAfter=4, leading=16)

doc = SimpleDocTemplate("newsletter.pdf", pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
story = []

current_site = None
for article in results:
    if article["site"] != current_site:
        if current_site is not None:
            story.append(PageBreak())
        current_site = article["site"]
        site_label = current_site.replace("https://www.", "").replace("/", "").split(".")[0].capitalize()
        story.append(Paragraph(site_label, style_site))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2C3E50"), spaceAfter=12))

    story.append(Paragraph(article["title"], style_title))
    story.append(Paragraph(article["url"], style_url))
    story.append(Paragraph(article["summary"], style_summary))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD"), spaceAfter=6))

doc.build(story)
print("PDF saved to newsletter.pdf")
"""

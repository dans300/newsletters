import ssl
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors



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


import os

app = Firecrawl(api_key=os.getenv("FIRE_CRAWL"))
#groupsomfy fc-3840d2d759ba4fc780bdbe2cf53ddfa5
#brandon api fc-5be3e611cd87485e9e703556a4522f78
#GITHUB fc-0647e8554d984502b02fcb4e59109672
SITES = [  
    #"https://www.batiactu.com/accueil.rss",
    "https://www.lemoniteur.fr/arc/outboundfeeds/rss/",
   "https://us14.campaign-archive.com/feed?u=f8bcf676bb27fc2419df09e98&id=c744bdaafe"
   #"https://bauinfoconsult.de/feed/" 
    #"https://www.geb-info.de/rss_feed/geb-rss-feed-meldungen",
    #"https://www.glaswelt.de/rss_feed/gw-rss-feed-meldungen",
    #"https://www.haustec.de/rss/heizung"
    #"https://us11.campaign-archive.com/feed?u=3c690b345db3823f0db0cac0f&id=bfc8c22a7a",
    #"https://www.kunststoffweb.de/rss/" 
    #"https://www.avproglobal.com/blogs/news/tagged/avpro-global.atom"
         
          ]

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

for base_url in SITES:
    print(f"\n--- Scraping {base_url} ---")

    try:
        homepage = app.scrape(
            base_url,
            formats=[{
                "type": "json",
                "schema": ARTICLE_SCHEMA,
                "prompt": "Extract all news articles visible on the page,each with title url and a 2 line summary ,all translated to English."
            }]
        )
        data = homepage.json
        if isinstance(data, dict):
            articles_raw = data.get("articles", [])
        elif isinstance(data, list):
            articles_raw = data
        else:
            articles_raw = []
    except Exception as e:
        print(f"⚠ Skipped site {base_url}: {e}")
        continue

    
    #---------------------------------------------------------------------------------------------
    

    # Step 2: Scrape each article and generate a 3-line summary
    for article in articles_raw:
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
            print(f"⚠ Skipped {url}: {e}")
            continue

        
        results.append({
    "site": base_url,
    "title": title,
    "url": url,
    "summary": summary,
    "content": page.markdown or ""
})

        print(f"✓ {title[:60]}")
        

with open("newsletter.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nDone. {len(results)} articles saved to newsletter.json")




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

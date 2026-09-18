

import site
import ssl
from datetime import date, time, timedelta
import feedparser
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import requests
import urllib3
import time as time_module
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context
import os


import requests
_orig = requests.Session.request
def _no_verify(self, method, url, **kwargs):
    kwargs['verify'] = False
    return _orig(self, method, url, **kwargs)
requests.Session.request = _no_verify

import json
from firecrawl import Firecrawl


app = Firecrawl(api_key=os.getenv("FIRE_CRAWL"))
#groupsomfy fc-3840d2d759ba4fc780bdbe2cf53ddfa5
#brandon api fc-5be3e611cd87485e9e703556a4522f78
#GITHUB fc-0647e8554d984502b02fcb4e59109672
#somfy fc-c925bfee660343c4af8349e197605baf
#UDEA fc-3218cf41b6364aa29841b43267cfaf71


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

SITES  = [

        #{"rss": True,"name": "Security and sales", "feed_url": "http://feeds.feedburner.com/SecuritySalesIntegration", "needs_firecrawl": False}, 
        #{"rss": True,"name": "GEB", "feed_url": "https://www.geb-info.de/rss_feed/geb-rss-feed-meldungen", "needs_firecrawl": False}, 
        #{"rss": True,"name": "Glaswelt", "feed_url": "https://www.glaswelt.de/rss_feed/gw-rss-feed-meldungen", "needs_firecrawl": False}, 
        #{"rss": True,"name": "Haustec", "feed_url": "https://www.haustec.de/rss/heizung", "needs_firecrawl": False}, 
        #{"rss": True,"name": "WindowVision", "feed_url": "https://www.wf-vision.com/feed/", "needs_firecrawl": True} 
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
                    "prompt": "Summarize this article in exactly 3 lines in english. Return a JSON object with a 'summary' field."
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



#-----------------------------------------------------PIPELINE 2------------------------------------------------------------------------------------------------------------------

import json,os
from xml.parsers.expat import model
from firecrawl import Firecrawl
from openai import OpenAI
from datetime import date
from urllib.parse import urlparse
from openai import OpenAI
import httpx
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from urllib.parse import urlparse
import time
import re
import time
from collections import Counter
import re
today = date.today().strftime("%B %d, %Y")

# Create a custom HTTP client that disables SSL verification
custom_http_client = httpx.Client(verify=False)


##################################################################all types of CLASSIFICATIONs ##############################################################################

"""
get_somfy_category la original qui marche bien 
get_somfy_category2 el de democracy (not in here)
get_somfy_category3 es firecrawl que lo hace 

""" 


client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

def get_somfy_category(title, summary):
    name="gemma3:4b" 
    system_instruction = ( "You are a master classifier for a construction news dashboard. "
                       " Assign each article with one word following the following logic:"
                         "if the article talks about anything a corporate decision where a product is not involved,assign the word (corporate) to the article, else"
                         "if the article talks about anything related to Law check if its a law assign the word (regulation) to the article , else"
                         "if the article talks about anything related to construction check if its residential -> housing: homes, apartments, social housing, student housing OR non-residential meaning everything else built: offices, retail, warehouses, "
                         "hotels, hospitals, schools, roads, infrastructure and finally assign whichever of the two it is either (residential) or (non-residential) to the article , else"
                         "if the artcile talks about anything related to a technology or product assign one word from [Access Control, Closures, Window, Glazing, Ventilation, Heating, Air conditioning, Lighting, Sun Shading] to the article, else"
                         "if the artcile talks about anything related to special or extraordinary events assign the word (events) to the article.if the article wasnt assigned to any of the former categories then assign the word (others) to it."
                         "Follow these rules: NEVER create new categories and every article must"
                       "be classified to one and only one word in (corporate),(regulation), (residential), (non-residential),  (Access Control), (Closures), (Window), (Glazing), (Ventilation), (Heating), (Air conditioning), (Lighting), (Sun Shading),(events), (others)."
    )                                               
    response = None
    prompt = f"Title: {title}\nSummary: {summary}\n\nCategory:"
    #((((((((((((((((((((((((((()))))))))))))))))))))))))))
    for provider in ["Together", "Fireworks", "DeepInfra"]:
        try:
            response = client.chat.completions.create(
        model=name,
         
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],extra_body={
        "provider": {
            "order": [
                provider
            ],  # Example preference order
            "allow_fallbacks": True,
        }
        },
        temperature=0.0, # Zero temperature ensures consistency for the user
        max_tokens=500,
        #extra_body={"think": False},  # Disable internal reasoning to prevent hallucinations
        #timeout=10.0
    )
            break
        except Exception:
            continue
    #((((((((((((((((((((((((((()))))))))))))))))))))))))))
    # 🛑 SAFETY GUARD: If all 3 providers failed, don't try to read .choices[0]
    if not response :
        return "others"
    
    raw = response.choices[0].message.content.strip()
  
    allowed = ["corporate", "regulation",
            "residential", "non-residential",
            "Access Control", "Closures", "Window", "Glazing", "Ventilation",
            "Heating", "Air conditioning", "Lighting", "Sun Shading",
            "events", "others"]
    for word in allowed:
        if word.lower() in raw.lower():
            return word
    return "others"  # Fallback category

def get_somfy_category3(url):
    from typing import Literal
    from pydantic import BaseModel

    ALLOWED = ["corporate","regulation", "residential", "non-residential", "Access Control", "Closures", "Window", "Glazing", "Ventilation", "Heating", "Air conditioning", "Lighting", "Sun Shading","events", "others"]

    class Classification(BaseModel):
        category: Literal[tuple(ALLOWED)]   # derived from ALLOWED, edit that list only

    system_instruction = ("You are a master classifier for a construction news dashboard. "
                       " Assign each article with one word following the following logic:"
                         "if the article talks about anything a corporate decision where a product is not involved,assign the word (corporate) to the article, else"
                         "if the article talks about anything related to Law check if its a law assign the word (regulation) to the article , else"
                         "if the article talks about anything related to construction check if its residential -> housing: homes, apartments, social housing, student housing OR non-residential meaning everything else built: offices, retail, warehouses, "
                         "hotels, hospitals, schools, roads, infrastructure and finally assign whichever of the two it is either (residential) or (non-residential) to the article , else"
                         "if the artcile talks about anything related to a technology or product assign one word from [Access Control, Closures, Window, Glazing, Ventilation, Heating, Air conditioning, Lighting, Sun Shading] to the article, else"
                         "if the artcile talks about anything related to special or extraordinary events assign the word (events) to the article.if the article wasnt assigned to any of the former categories then assign the word (others) to it."
                         "Follow these rules: NEVER create new categories and every article must"
                       "be classified to one and only one word in (corporate),(regulation), (residential), (non-residential),  (Access Control), (Closures), (Window), (Glazing), (Ventilation), (Heating), (Air conditioning), (Lighting), (Sun Shading),(events), (others)."
        ) 
    response = None
    #((((((((((((((((((((((((((()))))))))))))))))))))))))))
    for attempt in range(3):
        try:
            response = app.scrape(url, formats=[{
                "type": "json",
                "prompt": system_instruction,
                "schema": Classification.model_json_schema(),
            }])
            break
        except Exception:
            continue
    #((((((((((((((((((((((((((()))))))))))))))))))))))))))
    # 🛑 SAFETY GUARD: if all 3 attempts failed, don't try to read .json
    if not response:
        return "others"

    data = getattr(response, "json", None)
    if data is None and isinstance(response, dict):   # SDK version differences
        data = response.get("json")
    if not data:
        return "others"

    raw = str(data.get("category", ""))

    for word in ALLOWED:
        if word.lower() == raw.lower():
            return word
    return "others"  # Fallback category

def Firecrawl_clean_article(url):
    from pydantic import BaseModel

    class Body(BaseModel):
        text: str

    instruction = (
        "Extract only the main article text. "
        "Remove all navigation links, job listings, webinar ads, newsletter signups, "
        "event listings, service promotions, 'Les plus lus' sections, and any other "
        "site furniture. Translate the result into English. "
        "Plain text only, no HTML tags, no links, nothing inside brackets. "
        "Preserve paragraphs."
    )

    response = None
    for attempt in range(3):
        try:
            response = app.scrape(url, formats=[{
                "type": "json",
                "prompt": instruction,
                "schema": Body.model_json_schema(),
            }], only_main_content=True)
            break
        except Exception:
            continue

    if not response:
        return "unable to retrieve cleaned content"

    data = getattr(response, "json", None)
    if data is None and isinstance(response, dict):
        data = response.get("json")
    if not data:
        return "unable to retrieve cleaned content"

    return (data.get("text") or "").strip() or "unable to retrieve cleaned content"

def clean_article(content):
    response = client.chat.completions.create(
        model="llama3.1:8b",
        messages=[
            {"role": "system", "content": (
                "You are a text cleaner. Extract only the main article text from the content provided. "
                "Remove all navigation links, job listings, webinar ads, newsletter signups, event listings, "
                "service promotions, 'Les plus lus' sections, and any other site furniture."
                "there shouldnt be any html tags in the output, only plain text.No links. No information within brackets should be included  "
                "Return only the clean article body text, preserving paragraphs.your outputis only whats asked dont say anything else"
                "like 'Here is the cleaned text' or 'The cleaned article is as follows'."
            )},
            {"role": "user", "content": content[:6000]}  # truncate to avoid context overflow
        ],
        temperature=0.0,
        max_tokens=1000
    )
    return response.choices[0].message.content.strip()

################################################################################TRANSLATION##################################################################################
from py3langid import classify


def is_english(text,t):
    """Ask gemma whether the text is English. True / False."""
    text = (text or "").strip()
    t=1 if t>1 else t
    if not text:
        return True

    try:
        response = client.chat.completions.create(
            model="gemma3:4b",
            messages=[
                {"role": "system", "content":
                    "You decide what language a text is written in. "
                    "Answer with exactly one word: YES if the text is English, "
                    "NO if it is any other language. Brand names, product names "
                    "and company names do not make a text non-English. "
                    "Nothing else, no explanation."},
                {"role": "user", "content": text[:800]},
            ],
            temperature=0.0+t,
            max_tokens=5,
        )
        answer = (response.choices[0].message.content or "").strip().upper()
    except Exception as exc:
        print(f"    ! language check failed: {type(exc).__name__}: {exc}")
        return True                       # on failure, assume English and move on

    if answer.startswith("Y"):
        return True

    print("not english---->   ", text[:120])
    return False



def translate(content,t):
    response = None
    t=1 if t>1 else t
    for provider in ["DeepInfra", "Together", "Fireworks"]:
        try:
            response = client.chat.completions.create(
                model="gemma3:4b",#"llama-3.1-8b",
                messages=[
                    {"role": "system", "content": (
                        "You are a translator, you must translate the following text to English.  "
                        "Return only the translated text in english.your output is only whats asked dont say anything else"
                        "like 'Here is the translated text' or 'The translated article is as follows'."
                    )},
                    {"role": "user", "content": content[:6000]}  # truncate to avoid context overflow
                ],extra_body={
                "provider": {
                   "order":[ provider ],  # Example preference order
                    "allow_fallbacks": True,
                }
            },
                temperature=0.0+t,
                max_tokens=1000
            )
            break
        except Exception:
            continue
    try:
        return response.choices[0].message.content.strip()
    except Exception:
        return "* " + content#translation failed, returning original content with asterisk to indicate failure


def clip(text):
    MAX_WORDS = 10
    """Cut to MAX_WORDS and tidy any punctuation left dangling at the cut."""
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])
    return text.rstrip(" ,;:-")


def translate_title(title,t):
    t=1 if t>1 else t
    response = None
    try:
        response = client.chat.completions.create(
            model="gemma3:4b",#"llama-3.1-8b",
            messages=[
                {"role": "system", "content": (
                    "You are a summarizer, you must summarize the following headline into one sentence in english of 5 words or less. "
                    "Return only the English sentence in 5 words or less. your output is only whats asked "
                    "dont say anything else like 'Here is the translated text' or 'The translated "
                    "article is as follows'. "
                )},

                {"role": "user", "content": title[:300]}],  # truncate to avoid context overflow,
            temperature=0.0+t,
            max_tokens=60,
            stop=["\n"]
            
        )
    except Exception:
        return "* " + title

    try:
        out = response.choices[0].message.content.strip()
    except Exception:
        return "* " + title

    out = out.strip('"\'').split("\n")[0].strip()
    return clip(out) if out else "* " + title



#############################################################################################################################################################################

# Load, Process, and Save
with open("newsletter.json", "r", encoding="utf-8") as file:
    articles = json.load(file)

default_category="others"

for i, article in enumerate(articles):
    article["anchor_id"] = f"art_{i}"    

    t=0
    title=translate_title(article.get("title", ""),t)
    summary=translate(article.get("summary", ""),t)
    max_iters=5
    title = translate_title(article.get("title", ""), t)

    for _ in range(max_iters):
        if is_english(title, t):
            break
        print("---------------------------------------------------------------------title not in english, translating again")
        t += 0.2
        title = translate_title(article.get("title", ""), t)
    else:
        print("################################################## Giving up on title, using:", title[:60])

    t=0
   
    for _ in range(max_iters):
        if is_english(summary, t):
            break
        print("---------------------------summary not in english, translating again")
        t+=0.2
        summary=translate(article.get("summary", ""), t)
    else:
        print("################################################## Giving up on summary, using:", summary[:60])

    article["title"] = title
    article["summary"] = summary

    category = get_somfy_category(title, summary)
    article["category"] = category
    
    print(f"[{category}] {title[:50]}...")


print("**************************            CLEANING ARTICLES           ********************************")
for i, article in enumerate(articles):
    print(f"Cleaning article {i+1}/{len(articles)}: {article.get('title', '')[:60]}...")
    raw_content = article.get("content", "")
    if raw_content:
        article["clean_content"] = clean_article(article["content"])
    else:
        article["clean_content"] = " unable to retrieve cleaned article content"





with open("articles_classified.json", "w", encoding="utf-8") as file:
    json.dump(articles, file, indent=2)

print("\n--- Processing Complete: 'articles_classified.json' is ready. ---")




###########################################################################  PDF ############################################################################################

from collections import defaultdict
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
import json,os
from xml.parsers.expat import model
from firecrawl import Firecrawl
from openai import OpenAI
from datetime import date
from urllib.parse import urlparse
from openai import OpenAI
import httpx
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
import time
from collections import Counter
import re
today = date.today().strftime("%B %d, %Y")



bad = [a for a in articles if '"' in a.get("url", "")]
print(len(bad), "articles with broken urls")

#---------------------------------------------Repair URLS------------------------------------------------------------------
repaired = recovered = 0

for article in articles:
    url = article.get("url") or ""
    if '"' not in url:
        continue

    # the real url is everything before the first stray quote
    article["url"] = url.split('"')[0].strip()
    repaired += 1

    # the summary that got glued on is usually still readable - take it back
    # if the summary field is empty
    match = re.search(r'"summary"\s*:\s*"(.*?)"?\s*$', url, re.S)
    if match and not (article.get("summary") or "").strip():
        article["summary"] = match.group(1).strip()
        recovered += 1

print(f"{repaired} urls repaired, {recovered} summaries recovered")
#-----------------------------------------------------------------------------------------------------------------------------

grouped = defaultdict(list)
for article in articles:
    cat = article.get("category", "others")
    grouped[cat].append(article)

categories = list(grouped.keys())

from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import Table, TableStyle, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import glob

# ── Fonts ─────────────────────────────────────────────────────────────────────
# Try a real serif for headings. Falls back to the built-ins if not installed.
def _register(name, patterns):
    for pattern in patterns:
        hits = glob.glob(pattern, recursive=True)
        if hits:
            try:
                pdfmetrics.registerFont(TTFont(name, hits[0]))
                return True
            except Exception:
                pass
    return False

HEAD = "Times-Bold"
HEAD_REG = "Times-Roman"
if _register("Serif", ["/usr/share/fonts/**/DejaVuSerif.ttf",
                       "C:/Windows/Fonts/georgia.ttf",
                       "/System/Library/Fonts/Supplemental/Georgia.ttf"]) and \
   _register("Serif-Bold", ["/usr/share/fonts/**/DejaVuSerif-Bold.ttf",
                            "C:/Windows/Fonts/georgiab.ttf",
                            "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"]):
    HEAD, HEAD_REG = "Serif-Bold", "Serif"

BODY = "Helvetica"
BODY_BOLD = "Helvetica-Bold"
BODY_IT = "Helvetica-Oblique"

# ── Palette ───────────────────────────────────────────────────────────────────
INK      = colors.HexColor("#14213D")   # headings
ACCENT   = colors.HexColor("#C1440E")   # rules, category marks
MUTED    = colors.HexColor("#6B7280")   # metadata
TEXT     = colors.HexColor("#2B2B33")   # body copy
HAIRLINE = colors.HexColor("#E5E7EB")   # separators

# ── Text safety ───────────────────────────────────────────────────────────────
# Paragraph() parses its input as mini-HTML, so anything interpolated in has to
# be escaped or it can break the parser (a quote inside href= is fatal).
from xml.sax.saxutils import escape as _xml_escape
import re as _re

def esc(text):
    """Escape a value before putting it inside a Paragraph."""
    return _xml_escape(str(text or ""))

def safe_url(url):
    """Keep only the URL, cutting anything a corrupted field glued onto it."""
    url = str(url or "").strip()
    url = _re.split(r'["\'\s<>]', url)[0]
    return _xml_escape(url, {'"': "&quot;"})

# ── Styles ────────────────────────────────────────────────────────────────────
style_eyebrow = ParagraphStyle("eyebrow", fontSize=9, fontName=BODY_BOLD, textColor=ACCENT,
                               spaceAfter=10, leading=12)
style_date    = ParagraphStyle("date", fontSize=14, fontName=BODY, textColor=ACCENT,
                               alignment=TA_CENTER, spaceBefore=8, spaceAfter=4)
style_stats   = ParagraphStyle("stats", fontSize=9.5, fontName=BODY, textColor=MUTED,
                               alignment=TA_CENTER, spaceAfter=28)

style_toc_link  = ParagraphStyle("toc_link", fontSize=12, fontName=BODY, textColor=INK, leading=15)
style_toc_sub   = ParagraphStyle("toc_sub", parent=style_toc_link, leftIndent=16, textColor=TEXT)
style_toc_count = ParagraphStyle("toc_count", fontSize=10, fontName=BODY, textColor=MUTED,
                                 alignment=TA_RIGHT, leading=15)
style_toc_group = ParagraphStyle("toc_group", fontSize=9, fontName=BODY_BOLD, textColor=ACCENT,
                                 leading=14)

style_cat     = ParagraphStyle("cat", fontSize=26, leading=30, fontName=HEAD, textColor=INK,
                               spaceAfter=2)
style_catmeta = ParagraphStyle("catmeta", fontSize=9.5, fontName=BODY, textColor=MUTED,
                               spaceAfter=14)

style_title   = ParagraphStyle("title", fontSize=12.5, leading=16, fontName=BODY_BOLD,
                               textColor=INK, spaceBefore=14, spaceAfter=3)
style_meta    = ParagraphStyle("meta", fontSize=8.5, fontName=BODY, textColor=MUTED, spaceAfter=6)
style_summary = ParagraphStyle("summary", fontSize=10, fontName=BODY, textColor=TEXT,
                               leading=15.5, spaceAfter=10)
style_back    = ParagraphStyle("back", fontSize=9, fontName=BODY, textColor=ACCENT, spaceBefore=16)

style_site = ParagraphStyle("site", fontSize=22, leading=26, fontName=HEAD, textColor=INK,
                            spaceAfter=4, spaceBefore=0)
style_body = ParagraphStyle("body", fontSize=10, fontName=BODY, textColor=TEXT,
                            leading=16, spaceAfter=8)

# ── Site naming ───────────────────────────────────────────────────────────────
SITE_OVERRIDES = {
    "https://us14.campaign-archive.com/feed?u=f8bcf676bb27fc2419df09e98&id=c744bdaafe": "FIEC",
    "https://us11.campaign-archive.com/feed?u=3c690b345db3823f0db0cac0f&id=bfc8c22a7a": "TheConstructionVoice",
    "wsj.com": "WSJ",
}



def get_site_name(url):
    return next(d.get("name") for d in SITES if d.get("feed_url") == url)

sites = list(dict.fromkeys(get_site_name(a.get("feed_url")) for a in SITES))
title_text = " | ".join(sites)
file_name = title_text.replace(" | ", "") + " " + today + ".pdf"

# --- titles auto size ---
_n = len(title_text)
_size = 32 if _n < 30 else 24 if _n < 60 else 18 if _n < 110 else 14
style_cover = ParagraphStyle("cover", fontSize=_size, leading=_size * 1.2,
                             fontName=HEAD, textColor=INK, spaceAfter=6)

style_cover_big = ParagraphStyle("cover_big", fontSize=32, leading=38, fontName=HEAD,
                                 textColor=INK, spaceAfter=6)


style_footer_link = ParagraphStyle("footer_link", fontSize=10, fontName=BODY_BOLD, textColor=ACCENT, alignment=TA_RIGHT)
back_to_top_flowable = Paragraph('<a href="#top" color="#C1440E">▲ Top</a>', style_footer_link)
# ── Category ordering ─────────────────────────────────────────────────────────
PRODUCT_CATS = ["Access Control", "Closures", "Window", "Glazing", "Ventilation",
                "Heating", "Air conditioning", "Lighting", "Sun Shading"]

CONSTRUCTION_CATS = ["residential", "non-residential"]

# each entry is (heading shown on the cover, the categories it contains).
# groups appear in this order, after the ungrouped categories. add more freely.
GROUPS = [
    ("CONSTRUCTION", CONSTRUCTION_CATS),
    ("PRODUCTS &amp; TECH", PRODUCT_CATS),
]

def label(cat):
    return cat[0].upper() + cat[1:] if cat else cat

_grouped_names = {c for _, members in GROUPS for c in members}

top_cats = sorted(
    [c for c in categories if c not in _grouped_names and c.lower() != "others"],
    key=str.lower
)
others_cat = next((c for c in categories if c.lower() == "others"), None)


group_cats = [(heading, sorted([c for c in categories if c in members], key=str.lower))
              for heading, members in GROUPS]
group_cats = [(heading, members) for heading, members in group_cats if members]

ordered_cats = top_cats + [c for _, members in group_cats for c in members]
if others_cat:
    ordered_cats.append(others_cat)

# ── Page furniture ────────────────────────────────────────────────────────────
def page_footer(canvas, doc_):
    canvas.saveState()
    if canvas.getPageNumber() > 1:
        canvas.setFont(BODY, 8)
        page_no = str(canvas.getPageNumber())
        right_x = letter[0] - inch

        
        arrow_w = canvas.stringWidth("\u25B2 Top", BODY_BOLD, 10) + 4
        back_to_top_flowable.wrap(arrow_w, 0.3 * inch)
        back_to_top_flowable.drawOn(canvas, right_x - arrow_w, 0.58 * inch)

        room = (right_x - arrow_w - 10 - inch) - canvas.stringWidth(page_no, BODY, 8) - 18
        footer_fs = 8.0
        while footer_fs > 5.0 and canvas.stringWidth(title_text, BODY, footer_fs) > room:
            footer_fs -= 0.25

        canvas.setFont(BODY, footer_fs)
        canvas.setFillColor(MUTED)
        canvas.drawString(inch, 0.62 * inch, title_text)
        canvas.setFont(BODY, 8)
        canvas.drawRightString(right_x - arrow_w - 10, 0.62 * inch, page_no)
        canvas.setStrokeColor(HAIRLINE)
        canvas.setLineWidth(0.5)
        canvas.line(inch, 0.8 * inch, letter[0] - inch, 0.8 * inch)
    canvas.restoreState()

def rule(color=HAIRLINE, thickness=0.6, space_after=0):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=space_after)

doc = SimpleDocTemplate(file_name, pagesize=letter,
                        leftMargin=inch, rightMargin=inch,
                        topMargin=inch, bottomMargin=1.1 * inch,
                        title=f"{title_text} — {today}")
story = []

# ── Cover ─────────────────────────────────────────────────────────────────────
cover_block = [
    Paragraph("SUPER AWESOME NEWSLETTER", style_eyebrow),
    Paragraph(f'<a name="top"/>{esc(title_text)}', style_cover),
    rule(ACCENT, 2),
    Paragraph(today, style_date),
    Paragraph(f"{len(articles)} articles &nbsp;·&nbsp; {len(ordered_cats)} categories "
              f"&nbsp;·&nbsp; {len(sites)} sources", style_stats),
]
story.extend(cover_block)

# how much vertical room is left on page one once the cover block is drawn.
# SimpleDocTemplate pads its frame by 6pt on every side - subtract that or the
# measurement comes out 12pt too generous and the last row spills.
_FRAME_PAD = 6
FRAME_W = letter[0] - 2 * inch - 2 * _FRAME_PAD
FRAME_H = letter[1] - inch - 1.1 * inch - 2 * _FRAME_PAD

def _flowable_height(flowable, width):
    # getSpaceBefore/After work for Paragraph and HRFlowable alike
    return (flowable.wrap(width, FRAME_H)[1]
            + flowable.getSpaceBefore() + flowable.getSpaceAfter())

_used = sum(_flowable_height(f, FRAME_W) for f in cover_block)
_free = FRAME_H - _used - 4            # 4pt of breathing room at the bottom



# contents: build the table, measure it, and grow/shrink until it exactly
# fills the space left on page one. never spills onto page two.

MIN_FS, MAX_FS, MIN_PAD, MAX_PAD = 7.0, 14.0, 1.0, 22.0
def _build_toc(font_size, pad):
    for st in (style_toc_link, style_toc_sub):
        st.fontSize, st.leading = font_size, font_size * 1.25
    style_toc_count.fontSize = font_size - 2
    style_toc_count.leading = font_size * 1.25
    style_toc_group.fontSize = max(font_size - 2.5, 7.5)
    style_toc_group.leading = font_size * 1.25

    rows, row_styles = [], []
    for cat in top_cats:
        anchor = cat.replace(" ", "_").replace("&", "and")
        rows.append([Paragraph(f'<a href="#{anchor}" color="#14213D">{esc(label(cat))}</a>', style_toc_link),
                     Paragraph(str(len(grouped[cat])), style_toc_count)])
        row_styles.append(("LINEBELOW", (0, len(rows) - 1), (-1, len(rows) - 1), 0.5, HAIRLINE))

    for heading, members in group_cats:
        if top_cats or len(group_cats) > 1:      # skip a lone heading with nothing above it
            rows.append([Paragraph(heading, style_toc_group), ""])
            row_styles.append(("TOPPADDING", (0, len(rows) - 1), (-1, len(rows) - 1), pad + 6))
        for cat in members:
            anchor = cat.replace(" ", "_").replace("&", "and")
            rows.append([Paragraph(f'<a href="#{anchor}" color="#2B2B33">{esc(label(cat))}</a>', style_toc_sub),
                         Paragraph(str(len(grouped[cat])), style_toc_count)])
            row_styles.append(("LINEBELOW", (0, len(rows) - 1), (-1, len(rows) - 1), 0.5, HAIRLINE))

    if others_cat:
        anchor = others_cat.replace(" ", "_").replace("&", "and")
        rows.append([Paragraph(f'<a href="#{anchor}" color="#14213D">{esc(label(others_cat))}</a>', style_toc_link),
                        Paragraph(str(len(grouped[others_cat])), style_toc_count)])
        row_styles.append(("LINEBELOW", (0, len(rows) - 1), (-1, len(rows) - 1), 0.5, HAIRLINE))

    table = Table(rows, colWidths=[5.0 * inch, 1.5 * inch])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
    ] + row_styles))
    return table

def _fits(font_size, pad):
    return _build_toc(font_size, pad).wrap(FRAME_W, FRAME_H)[1] <= _free

# 1. largest font whose tightest layout still fits
_toc_fs = MAX_FS
while _toc_fs > MIN_FS and not _fits(_toc_fs, MIN_PAD):
    _toc_fs -= 0.5

# 2. then open the rows up until the page is full
_toc_pad = MIN_PAD
while _toc_pad < MAX_PAD and _fits(_toc_fs, _toc_pad + 0.5):
    _toc_pad += 0.5

toc = _build_toc(_toc_fs, _toc_pad)
story.append(toc)
story.append(PageBreak())

# ── Summaries by category ─────────────────────────────────────────────────────
for cat in ordered_cats:
    anchor = cat.replace(" ", "_").replace("&", "and")
    count = len(grouped[cat])
    story.append(Paragraph(f'<a name="{anchor}"/>{esc(label(cat))}', style_cat))
    story.append(Paragraph(f"{count} article{'s' if count != 1 else ''}", style_catmeta))
    story.append(rule(ACCENT, 1.5, space_after=2))

    for i, article in enumerate(grouped[cat]):
        site_label = article["site"] 
        story.append(Paragraph(
            f'<a name="sum_{article["anchor_id"]}"/>'
            f'<a href="#full_{article["anchor_id"]}" color="#14213D">{esc(article["title"])}</a>',
            style_title))
        story.append(Paragraph(
            f'{esc(site_label)} &nbsp;·&nbsp; <a href="{safe_url(article["url"])}" color="#6B7280">source</a>',
            style_meta))
        story.append(Paragraph(esc(article.get("summary", "")), style_summary))
        if i < count - 1:
            story.append(rule())

    
    story.append(PageBreak())

# ── Full articles ─────────────────────────────────────────────────────────────
story.append(Paragraph("FULL ARTICLES", style_eyebrow))
story.append(Paragraph("Cleaned text", style_cover_big))
story.append(rule(ACCENT, 2, space_after=20))

current_site = None
for article in articles:
    if article["site"] != current_site:
        if current_site is not None:
            story.append(PageBreak())
        current_site = article["site"]
        story.append(Paragraph(esc(current_site), style_site))
        story.append(rule(ACCENT, 1.5, space_after=6))

    story.append(Paragraph(
        f'<a name="full_{article["anchor_id"]}"/>{esc(article["title"])}',style_title))
    story.append(Paragraph(
        f'<a href="{safe_url(article["url"])}" color="#6B7280">{esc(article["url"][:90])}</a>', style_meta))

    for line in article.get("clean_content", "").split("\n"):
        line = line.strip()
        if line:
            story.append(Paragraph(esc(line), style_body))

    story.append(Spacer(1, 6))
    story.append(rule())

doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
print(f"PDF saved to {file_name}")
print(str("this is the NEW GUI"))



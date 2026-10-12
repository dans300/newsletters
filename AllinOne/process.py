"""
Per-site worker. One machine runs one site.

    python process.py --index 3

Picks SITES[index] from sites.py, scrapes + cleans + translates + classifies
ONLY that site, and writes out/<index>-<slug>.json.

No PDF code here. No email here. That is make_pdf.py's job.
"""

import argparse
import json
import os
import re

from sites import SITES

# ── Which site is this machine doing? ─────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--index", type=int, required=True,
                    help="position in sites.py SITES")
args = parser.parse_args()

if not 0 <= args.index < len(SITES):
    raise SystemExit(f"index {args.index} out of range (0..{len(SITES) - 1})")

site = SITES[args.index]
print(f"shard {args.index}: {site['name']}  <-  {site['feed_url']}", flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# PASTE YOUR EXISTING PIPELINE HERE, with two changes:
#
#   1. Delete the `for site in SITES:` loop. You are already inside one site -
#      `site` is the dict above, with the same keys it always had (rss, name,
#      feed_url, needs_firecrawl). Everything that was indented under that loop
#      moves out one level.
#
#   2. Do NOT assign `anchor_id` here. Every shard would start numbering at 0
#      and the ids would collide after the merge, so the PDF's summary links
#      would jump to the wrong article. make_pdf.py assigns them.
#
# At the end of this block you need a list called `articles`, each item with
# the keys the PDF expects: title, url, summary, category, site, clean_content.
# ══════════════════════════════════════════════════════════════════════════════


import site
import ssl
from datetime import date, time
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
#
#




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



# step 1---------get the articles--------------------------------------------------------------
if site.get("rss"):
    print("camino RSS")
    articles_raw = get_articles_from_rss(site["feed_url"], site["needs_firecrawl"])
else:
    print("camino Normal")
    articles_raw = get_articles_from_site(site["feed_url"])
# Step 2: Scrape each article and generate a 3-line summary
for article in articles_raw:
    #time_module.sleep(1)#rate limits apply 
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


#client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
custom_http_client = httpx.Client(verify=False)
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key= os.getenv("OPENROUTER_API_KEY"),
                http_client=custom_http_client)


def get_somfy_category(title, summary):
    name="google/gemma-3-4b-it"
    
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
        timeout=180.0
    )
            break
        except Exception:
            time.sleep(2)
            continue
    #((((((((((((((((((((((((((()))))))))))))))))))))))))))
    # 🛑 SAFETY GUARD: If all 3 providers failed, don't try to read .choices[0]
    if not response :
        print("⚠ All providers failed for category classification. Defaulting to 'others'.")
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


def get_somfy_categoryOllama(title, summary):
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
        timeout=180.0
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
    try:
        response = client.chat.completions.create(
            model="gemma3:4b",#"llama3.1:8b",
            messages=[
                {"role": "system", "content": (
                    "You are a text cleaner. Extract only the main article text from the content provided. "
                    "Remove all navigation links, job listings, webinar ads, newsletter signups, event listings, "
                    "service promotions, 'Les plus lus' sections, and any other site furniture."
                    "there shouldnt be any html tags in the output, only plain text.No links. No information within brackets should be included  "
                    "Return only the clean article body text, preserving paragraphs.your outputis only whats asked dont say anything else"
                    "like 'Here is the cleaned text' or 'The cleaned article is as follows'."
                )},
                {"role": "user", "content": content[:5000]}  # truncate to avoid context overflow
            ],
            temperature=0.0,
            max_tokens=1000,
            timeout=200.0
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        print(f"  ! clean failed: {type(exc).__name__}", flush=True)
        return content

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
            model="gemma3:4b", #"gemma3:4b" if OLLAMA google/gemma-3-4b-it" IF OPENROUTER
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
            timeout=180.0
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
                max_tokens=1000,
                timeout=180.0
        )
            break
        except Exception:
            time.sleep(2)
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
            model="gemma3:4b",#"llama-3.1-8b" IS THE ORIGINAL MODEL,
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
            timeout=180.0,
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
sleepSeconds=0
for i, article in enumerate(articles):
    #article["anchor_id"] = f"art_{i}"    
    time.sleep(sleepSeconds)
    t=0
    title=translate_title(article.get("title", ""),t)
    time.sleep(sleepSeconds)
    summary=translate(article.get("summary", ""),t)
    time.sleep(sleepSeconds)
    max_iters=1
    time.sleep(sleepSeconds)
    for _ in range(max_iters):
        if is_english(title, t):
            break
        print("---------------------------------------------------------------------title not in english, translating again")
        t += 0.3
        title = translate_title(article.get("title", ""), t)
        time.sleep(sleepSeconds)
    else:
        print("################################################## Giving up on title, using:", title[:60])

    t=0
    time.sleep(sleepSeconds)
    for _ in range(max_iters):
        if is_english(summary, t):
            break
        print("---------------------------summary not in english, translating again")
        t+=0.3
        summary=translate(article.get("summary", ""), t)
        time.sleep(sleepSeconds)
    else:
        print("################################################## Giving up on summary, using:", summary[:60])

    article["title"] = title
    article["summary"] = summary

    category = get_somfy_categoryOllama(title, summary)
    article["category"] = category
    
    print(f"[{category}] {title[:50]}...")

    raw_content = article.get("url", "")
    if raw_content:
        article["clean_content"] = translate(Firecrawl_clean_article(raw_content), 0)
    else:
        article["clean_content"] = " unable to retrieve cleaned article content"

"""SOLUCION : Poner a clean con llama toma demasiado tiempo en github y no es practico , la solucion fue con firecrawl_clean_article y y traducir con Gemma """


with open("articles_classified.json", "w", encoding="utf-8") as file:
    json.dump(articles, file, indent=2)

print("\n--- Processing Complete: 'articles_classified.json' is ready. ---")


####################################################################END OF MY CODE #####################################################




# ── Save this shard's slice ───────────────────────────────────────────────────
def slug(text):
    text = re.sub(r"[^a-z0-9]+", "-", str(text).lower())
    return text.strip("-") or "site"


os.makedirs("out", exist_ok=True)
out_path = f"out/{args.index:02d}-{slug(site['name'])}.json"

with open(out_path, "w", encoding="utf-8") as file:
    json.dump(articles, file, indent=2, ensure_ascii=False)

print(f"wrote {len(articles)} articles to {out_path}", flush=True)

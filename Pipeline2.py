import json,os
from xml.parsers.expat import model
from openai import OpenAI
from datetime import date
from urllib.parse import urlparse
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from urllib.parse import urlparse

import re
today = date.today().strftime("%B %d, %Y")


# Initialize the local Ollama client
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
name="gemma3:4b"
def get_somfy_category(title, summary):
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
   
    prompt = f"Title: {title}\nSummary: {summary}\n\nCategory:"
      
    response = client.chat.completions.create(
        model=name,
         
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0, # Zero temperature ensures consistency for the user
        max_tokens=500,
        #extra_body={"think": False},  # Disable internal reasoning to prevent hallucinations
        #timeout=10.0
    )
    
    raw = response.choices[0].message.content.strip()
  
    allowed = ["corporate", "regulation",
                "residential", "non-residential",
                "Access Control", "Closures", "Window", "Glazing", "Ventilation",
                "Heating", "Air conditioning", "Lighting", "Sun Shading",
                "events", "others"]
    for word in allowed:
        if word.lower() in raw.lower():
            return word
    return "error"  # Fallback category



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



# Load, Process, and Save
with open("newsletter - test.json", "r", encoding="utf-8") as file:
    articles = json.load(file)

for i, article in enumerate(articles):
    article["anchor_id"] = f"art_{i}"    
    category = get_somfy_category(article.get("title", ""), article.get("summary", ""))
    article["category"] = category
    print(f"[{category}] {article['title'][:50]}...")
    raw_content = article.get("content", "")
    if raw_content:
        article["clean_content"] = clean_article(raw_content)
    else:
        article["clean_content"] = ""
    

with open("articles_classified.json", "w", encoding="utf-8") as file:
    json.dump(articles, file, indent=2)

print("\n--- Processing Complete: 'articles_classified.json' is ready. ---")


#############################################PDF##############################################################

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

def strip_scheme(u):
    return u.split("://", 1)[-1]

def get_site_name(url):
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    for key, name in SITE_OVERRIDES.items():
        if key.startswith("http"):
            if strip_scheme(url) == strip_scheme(key):
                return name
        elif netloc.endswith(key):
            return name
    return netloc.split('.')[-2].capitalize()

sites = list(dict.fromkeys(get_site_name(a["site"]) for a in articles if "site" in a))
title_text = " | ".join(sites)
file_name = title_text.replace(" | ", "") + " " + today + ".pdf"

# --- titles auto size ---
_n = len(title_text)
_size = 32 if _n < 30 else 24 if _n < 60 else 18 if _n < 110 else 14
style_cover = ParagraphStyle("cover", fontSize=_size, leading=_size * 1.2,
                             fontName=HEAD, textColor=INK, spaceAfter=6)

style_cover_big = ParagraphStyle("cover_big", fontSize=32, leading=38, fontName=HEAD,
                                 textColor=INK, spaceAfter=6)

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

top_cats = sorted([c for c in categories if c not in _grouped_names], key=str.lower)
group_cats = [(heading, sorted([c for c in categories if c in members], key=str.lower))
              for heading, members in GROUPS]
group_cats = [(heading, members) for heading, members in group_cats if members]

ordered_cats = top_cats + [c for _, members in group_cats for c in members]

# ── Page furniture ────────────────────────────────────────────────────────────
def page_footer(canvas, doc_):
    canvas.saveState()
    if canvas.getPageNumber() > 1:
        canvas.setFont(BODY, 8)
        canvas.setFillColor(MUTED)
        page_no = str(canvas.getPageNumber())
        right_x = letter[0] - inch
        room = (right_x - inch) - canvas.stringWidth(page_no, BODY, 8) - 18

        footer_fs = 8.0
        while footer_fs > 5.0 and canvas.stringWidth(title_text, BODY, footer_fs) > room:
            footer_fs -= 0.25

        canvas.setFont(BODY, footer_fs)
        canvas.drawString(inch, 0.62 * inch, title_text)
        canvas.setFont(BODY, 8)
        canvas.drawRightString(letter[0] - inch, 0.62 * inch, str(canvas.getPageNumber()))
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
        site_label = get_site_name(article["site"]) if article.get("site") else ""
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

    story.append(Paragraph('<a href="#top" color="#C1440E">↑ Back to contents</a>', style_back))
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
        story.append(Paragraph(esc(get_site_name(current_site)), style_site))
        story.append(rule(ACCENT, 1.5, space_after=6))

    story.append(Paragraph(
        f'<a name="full_{article["anchor_id"]}"/>'
        f'<a href="#sum_{article["anchor_id"]}" color="#14213D">{esc(article["title"])}</a>',
        style_title))
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
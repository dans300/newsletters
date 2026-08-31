import json,os
from xml.parsers.expat import model
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



openrouter_key = os.getenv("OPENROUTER_API_KEY")

# Initialize the local Ollama client
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key,
                http_client=custom_http_client)
name="google/gemma-3-4b-it"
def get_somfy_category(title, summary):
    system_instruction = ("You are a master classifier for a construction news dashboard. "
        " Assign each article with one word following the following logic:"
          "if the article talks about anything related to money or the market itself but not a specific company assign the word (Financial) to the article, else "
          "if the article talks about anything a corporate decision where a product is not involved,assign the word (corporate) to the article, else"
          "if the article talks about anything related to Law check if its a law or a sanction and assign whichever of the two it is either (regulation) or (sanction) to the article , else"
          "if the article talks about anything related to construction check if its residental or non residential and assign whichever of the two it is either (residential) or (non-residential) to the article , else"
          "if the artcile talks about anything related to a technology or product assign the word (technology) to the article, else"
          "if the artcile talks about anything related to special or extraordinary events assign the word (events) to the article.if the article wasnt assigned to any of the former categories then assign the word (others) to it."
          "Follow these rules: NEVER create new categories and every article must"
        "be classified to one and only one word in (Financial), (corporate),(regulation), (sanction), (residential), (non-residential),  (technology),(events), (others)."
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
  
    allowed = ["Financial", "corporate","regulation", "sanction", "residential", "non-residential",  "technology","events", "others"]
    for word in allowed:
        if word.lower() in raw.lower():
            return word
    return "others"  # Fallback category

def get_somfy_category2(title, summary):
    """Classify one article with a three-model ranked vote. Returns one word."""
    MODELS = [
        "google/gemma-4-26b-a4b-it",
        "ibm-granite/granite-4.1-8b",
        "deepseek/deepseek-v4-flash-0731",
        ]

    PROVIDERS = ["Together", "Fireworks", "DeepInfra"]

    ALLOWED = [
         "corporate", "regulation", "sanction",
        "residential", "non-residential",
        "Access Control", "Closures", "Window", "Glazing", "Ventilation",
        "Heating", "Air conditioning", "Lighting", "Sun Shading",
        "events", "others",
    ]

    system_instruction = (
        "You are a master classifier for a construction news dashboard. "
            " Assign each article with one word following the following logic:"
              #"if the article talks about anything related to money or the market itself but not a specific company assign the word (Financial) to the article, else "
              "if the article talks about anything a corporate decision where a product is not involved,assign the word (corporate) to the article, else"
              "if the article talks about anything related to Law check if its a law or a sanction and assign whichever of the two it is either (regulation) or (sanction) to the article , else"
              "if the article talks about anything related to construction check if its residential -> housing: homes, apartments, social housing, student housing OR non-residential meaning everything else built: offices, retail, warehouses, "
              "hotels, hospitals, schools, roads, infrastructure and finally assign whichever of the two it is either (residential) or (non-residential) to the article , else"
              "if the artcile talks about anything related to a technology or product assign one word from [Access Control, Closures, Window, Glazing, Ventilation, Heating, Air conditioning, Lighting, Sun Shading] to the article, else"
              "if the artcile talks about anything related to special or extraordinary events assign the word (events) to the article.if the article wasnt assigned to any of the former categories then assign the word (others) to it."
              "Follow these rules: NEVER create new categories and every article must"
            "be classified to one and only one word in (corporate),(regulation), (sanction), (residential), (non-residential),  (Access Control), (Closures), (Window), (Glazing), (Ventilation), (Heating), (Air conditioning), (Lighting), (Sun Shading),(events), (others)."
    )
    prompt = f"Title: {title}\nSummary: {summary}"

    # ── helpers ───────────────────────────────────────────────────────────────
    def extract_content(response):
        """Tolerate OpenRouter error payloads that arrive with HTTP 200."""
        choices = getattr(response, "choices", None)
        if not choices:
            return None, f"no choices ({getattr(response, 'error', None)})"
        message = choices[0].message
        text = (getattr(message, "content", None) or "").strip()
        if text:
            return text, None
        # some models leave content empty and put everything in reasoning
        text = (getattr(message, "reasoning", None) or "").strip()
        if text:
            return text, None
        return None, f"empty (finish={getattr(choices[0], 'finish_reason', '?')})"

    def parse_ranking(raw):
        cleaned = re.sub(r"\s+", " ", raw.strip().lower())
        # canonicalise multi-word labels: "non residential", "air-conditioning",
        # "accesscontrol" all collapse to the exact spelling used in ALLOWED
        for label in ALLOWED:
            parts = re.split(r"[\s-]+", label.lower())
            if len(parts) > 1:
                flexible = r"[\s_-]*".join(re.escape(p) for p in parts)
                cleaned = re.sub(flexible, label.lower(), cleaned)

        found = []
        for label in ALLOWED:
            # compare lowercased - ALLOWED has mixed case, the reply is lowered
            match = re.search(
                rf"(?<![\w-]){re.escape(label.lower())}s?(?![\w-])", cleaned
            )
            if match:
                found.append((match.start(), label))
        return [label for _, label in sorted(found)][:2]

    # ── 1. ask each model, trying providers in order until one answers ────────
    rankings, notes = [], []
    for model in MODELS:
        ranking, note = [], None

        for provider in PROVIDERS:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt},
                    ],
                    extra_body={
                        "provider": {
                            "order": [provider],
                            # False, or OpenRouter reroutes and the loop is moot
                            "allow_fallbacks": True,
                        }
                    },
                    temperature=0.0,
                    max_tokens=200,
                    timeout=60.0,
                )
            except Exception as exc:
                note = f"{provider} {type(exc).__name__}"
                time.sleep(0.3)
                continue

            raw, error = extract_content(response)
            if raw is None:
                note = f"{provider} {error}"
                time.sleep(0.3)
                continue

            ranking = parse_ranking(raw)
            if ranking:
                note = None
                break                       # got an answer - stop trying providers
            note = f"{provider} UNPARSED {raw[:30]!r}"

        rankings.append(ranking)            # exactly one entry per model
        short = model.split("/")[-1]
        notes.append(f"{short}: {', '.join(ranking)}" if ranking
                     else f"{short}: FAILED ({note})")

    votes = [r for r in rankings if r]
    if not votes:
        print("    " + " | ".join(notes) + "  ->  others (no_valid_votes)")
        return "others"

    # ── 2. majority on first choices ──────────────────────────────────────────
    label, count = Counter(r[0] for r in votes).most_common(1)[0]
    method = "majority" if count >= 2 else None

    # ── 3. no majority: points. first choice 2, second 1 ──────────────────────
    if method is None:
        score = Counter()
        for ranking in votes:
            for points, name in zip((2, 1), ranking):
                score[name] += points
        ranked = score.most_common()
        if len(ranked) == 1 or ranked[0][1] > ranked[1][1]:
            label, method = ranked[0][0], "borda"
        else:
            # ── 4. points tied too: fall back to the order of ALLOWED ─────────
            label = min({c for r in votes for c in r}, key=ALLOWED.index)
            method = "precedence"

    print("    " + " | ".join(notes) + f"  ->  {label} ({method})")
    return label  

def clean_article(content):
    response = None
    for provider in ["DeepInfra", "Together", "Fireworks"]:
        try:
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
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
                ],extra_body={
                "provider": {
                    "order":[ provider ],  # Example preference order
                    "allow_fallbacks": True,
                }
            },
                temperature=0.0,
                max_tokens=1000
            )
            break
        except Exception:
            continue
    try:
        return response.choices[0].message.content.strip()
    except Exception:
        return "unable to retrieve cleaned content"

####translator################################################
def translate(content):
    response = None
    for provider in ["DeepInfra", "Together", "Fireworks"]:
        try:
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
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
                temperature=0.0,
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


def translate_title(title):
    response = None
    try:
        response = client.chat.completions.create(
            model="google/gemma-4-26b-a4b-it",
            messages=[
                {"role": "system", "content": (
                    "You are a summarizer, you must summarize the following headline into one sentence in english of 5 words or less. "
                    "Return only the English sentence in 5 words or less. your output is only whats asked "
                    "dont say anything else like 'Here is the translated text' or 'The translated "
                    "article is as follows'. "
                )},

                {"role": "user", "content": title[:300]}],  # truncate to avoid context overflow,
            temperature=0.0,
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
#############################################################

# Load, Process, and Save
with open("newsletter.json", "r", encoding="utf-8") as file:
    articles = json.load(file)

default_category="others"

for i, article in enumerate(articles):
    article["anchor_id"] = f"art_{i}"    
    
    # Try to get the category, catch the crash if the API fails
    try:
        category = get_somfy_category2(article.get("title", ""), article.get("summary", ""))
    except Exception as e:
        print(f"API error on article {i}, defaulting to 'Others': {e}")
        category = default_category

    # If the API succeeds but returns None or an empty string, fallback to Others
    if not category:
        category = default_category

    article["category"] = category
    article["summary"] = translate(article["summary"])  # Translate the summary to English
    # Safely grab the title so the print statement doesn't crash if title is missing
    article["title"] = translate_title(article.get("title", "Untitled"))
    title = article.get("title", "Untitled")
    print(f"[{category}] {title[:50]}...")
    
    raw_content = article.get("content", "")
    if raw_content:
        article["clean_content"] = translate(clean_article(raw_content))
    else:
        article["clean_content"] = ""





with open("articles_classified.json", "w", encoding="utf-8") as file:
    json.dump(articles, file, indent=2)

print("\n--- Processing Complete: 'articles_classified.json' is ready. ---")



from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch

grouped = defaultdict(list)
for article in articles:
    cat = article.get("category", "others")
    grouped[cat].append(article)

categories = list(grouped.keys())

style_toc_title = ParagraphStyle("toc_title", fontSize=24,leading=29, fontName="Helvetica-Bold", textColor=colors.HexColor("#2C3E50"), spaceAfter=16)
style_toc_link  = ParagraphStyle("toc_link",  fontSize=13, fontName="Helvetica",         textColor=colors.HexColor("#2980B9"), spaceAfter=10)
style_cat       = ParagraphStyle("cat",       fontSize=18, fontName="Helvetica-Bold",    textColor=colors.HexColor("#2C3E50"), spaceAfter=8, spaceBefore=10)
style_title     = ParagraphStyle("title",     fontSize=12, fontName="Helvetica-Bold",    textColor=colors.HexColor("#1A1A1A"), spaceAfter=4, spaceBefore=12)
style_url       = ParagraphStyle("url",       fontSize=8,  fontName="Helvetica-Oblique", textColor=colors.HexColor("#7F8C8D"), spaceAfter=4)
style_summary   = ParagraphStyle("summary",   fontSize=10, fontName="Helvetica",         textColor=colors.HexColor("#333333"), spaceAfter=4, leading=16)
style_back      = ParagraphStyle("back",      fontSize=9,  fontName="Helvetica-Oblique", textColor=colors.HexColor("#2980B9"), spaceAfter=12, spaceBefore=10)
style_site = ParagraphStyle("site", fontSize=22, fontName="Helvetica-Bold", textColor=colors.HexColor("#2C3E50"), spaceAfter=16, spaceBefore=20)
style_body = ParagraphStyle("body", fontSize=10, fontName="Helvetica",      textColor=colors.HexColor("#333333"), spaceAfter=4,  leading=16)


# Add entries here for any site whose auto-generated name you don't like.
# Key = a piece of the domain to match, Value = the name to use instead.
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







doc = SimpleDocTemplate(file_name, pagesize=letter,
                        leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
story = []


story.append(Paragraph(f'<a name="top"/>{title_text} — {today}', style_toc_title))
story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2C3E50"), spaceAfter=16))

for cat in categories:
    anchor = cat.replace(" ", "_").replace("&", "and")
    story.append(Paragraph(f'<a href="#{anchor}" color="#2980B9">{cat}</a>', style_toc_link))

story.append(PageBreak())

for cat in categories:
    anchor = cat.replace(" ", "_").replace("&", "and")
    story.append(Paragraph(f'<a name="{anchor}"/>{cat}', style_cat))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2C3E50"), spaceAfter=12))

    for article in grouped[cat]:
        story.append(Paragraph(f'<a name="sum_{article["anchor_id"]}"/><a href="#full_{article["anchor_id"]}" color="#1A1A1A">{article["title"]}</a>', style_title))
        story.append(Paragraph(article["url"], style_url))
        story.append(Paragraph(article.get("summary", ""), style_summary))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD"), spaceAfter=6))

    story.append(Paragraph('<a href="#top" color="#2980B9">↑ Back to top</a>', style_back))
    story.append(PageBreak())

#FULL ARTICLES SECTION
story.append(Paragraph("Full Cleaned Articles", style_toc_title))
story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2C3E50"), spaceAfter=16))

current_site = None
for article in articles:
    if article["site"] != current_site:
        if current_site is not None:
            story.append(PageBreak())
        current_site = article["site"]
        
        # Clean up the site name for the header using urlparse again
        site_label = urlparse(current_site).netloc.split('.')[-2].capitalize()
        story.append(Paragraph(site_label, style_site))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2C3E50"), spaceAfter=12))

    # Add the clickable title that links back up to the summary
    story.append(Paragraph(f'<a name="full_{article["anchor_id"]}"/><a href="#sum_{article["anchor_id"]}" color="#1A1A1A">{article["title"]}</a>', style_title))
    story.append(Paragraph(article["url"], style_url))

    # Add the cleaned body text paragraphs
    for line in article.get("clean_content", "").split("\n"):
        line = line.strip()
        if line:
            story.append(Paragraph(line, style_body))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD"), spaceAfter=6))



doc.build(story)
print(f"PDF saved to {file_name}")
print(name+str(" was used to classify the articles."))
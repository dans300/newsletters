import json
from xml.parsers.expat import model
from openai import OpenAI
from datetime import date
from urllib.parse import urlparse

import re
today = date.today().strftime("%B %d, %Y")


# Initialize the local Ollama client
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
name="gemma3:4b"
def get_somfy_category(title, summary):
    system_instruction = ("You are a master classifier for a construction news dashboard. "
        " Assign each article with one word following the following logic:"
          "if the article talks about anything related to money or the market itself but not a specific company assign the word (Financial) to the article, else "
          "if the article talks about anything a company does ,except for if a product is involved,assign the word (corporate) to the article, else"
          "if the article talks about anything related to Law check if its a law or a sanction and assign whichever of the two it is either (regulation) or (sanction) to the article , else"
          "if the article talks about anything related to construction check if its residental or non residential and assign whichever of the two it is either (residential) or (non-residential) to the article , else"
          "if the artcile talks about anything related to a technology or product assign the word (technology) to the article, else"
          "if the artcile talks about anything related to special or extraordinary events assign the word (events) to the article.if the article wasnt assigned to any of the former categories then assign the word (others) to it."
          "Follow these rules: NEVER create new categories and every article must"
        "be classified to one and only one word in (Financial), (corporate),(regulation), (sanction), (residential), (non-residential),  (technology),(events), (others)."
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
  
    allowed = ["Financial", "corporate","regulation", "sanction", "residential", "non-residential",  "technology","events", "others"]
    for word in allowed:
        if word.lower() in raw.lower():
            return word
    return "error"  # Fallback category

# Load, Process, and Save
with open("newsletter.json", "r", encoding="utf-8") as file:
    articles = json.load(file)

for article in articles:
    category = get_somfy_category(article.get("title", ""), article.get("summary", ""))
    article["category"] = category
    print(f"[{category}] {article['title'][:50]}...")

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


sites = list(dict.fromkeys(urlparse(a["site"]).netloc.split('.')[-2].capitalize() for a in articles if "site" in a))
title_text = " | ".join(sites)
file_name=title_text.replace(" | ", "") +" " + today+".pdf"

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
        story.append(Paragraph(article["title"], style_title))
        story.append(Paragraph(article["url"], style_url))
        story.append(Paragraph(article.get("summary", ""), style_summary))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD"), spaceAfter=6))

    story.append(Paragraph('<a href="#top" color="#2980B9">↑ Back to top</a>', style_back))
    story.append(PageBreak())

doc.build(story)
print(f"PDF saved to {file_name}")
print(name+str(" was used to classify the articles."))
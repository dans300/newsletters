import json,os

from openai import OpenAI

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable

from reportlab.lib.styles import ParagraphStyle

from reportlab.lib.pagesizes import letter

from reportlab.lib import colors

from reportlab.lib.units import inch



client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")



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



with open("newsletter.json", "r", encoding="utf-8") as f:

    articles = json.load(f)



# Clean each article

for i, article in enumerate(articles):

    print(f"Cleaning {i+1}/{len(articles)}: {article['title'][:50]}...")

    raw_content = article.get("content", "")

    if raw_content:

        article["clean_content"] = clean_article(raw_content)

    else:

        article["clean_content"] = ""



""" Save cleaned JSON

with open("newsletter_clean.json", "w", encoding="utf-8") as f:

    json.dump(articles, f, ensure_ascii=False, indent=2)



print("\nCleaned JSON saved.")"""



# Generate PDF

style_site  = ParagraphStyle("site",    fontSize=22, fontName="Helvetica-Bold", textColor=colors.HexColor("#2C3E50"), spaceAfter=16, spaceBefore=20)

style_title = ParagraphStyle("title",   fontSize=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#1A1A1A"), spaceAfter=4,  spaceBefore=14)

style_url   = ParagraphStyle("url",     fontSize=8,  fontName="Helvetica-Oblique", textColor=colors.HexColor("#7F8C8D"), spaceAfter=8)

style_body  = ParagraphStyle("body",    fontSize=10, fontName="Helvetica",      textColor=colors.HexColor("#333333"), spaceAfter=4,  leading=16)



doc = SimpleDocTemplate("articles_clean.pdf", pagesize=letter,

                        leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)

story = []



current_site = None

for article in articles:

    if article["site"] != current_site:

        if current_site is not None:

            story.append(PageBreak())

        current_site = article["site"]

        site_label = current_site.replace("https://www.", "").replace("/", "").split(".")[0].capitalize()

        story.append(Paragraph(site_label, style_site))

        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2C3E50"), spaceAfter=12))



    story.append(Paragraph(article["title"], style_title))

    story.append(Paragraph(article["url"], style_url))



    for line in article.get("clean_content", "").split("\n"):

        line = line.strip()

        if line:

            story.append(Paragraph(line, style_body))



    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD"), spaceAfter=6))



doc.build(story)

os.remove("newsletters.json")

print("PDF saved to articles_clean.pdf")
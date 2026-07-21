import json
from openai import OpenAI
from datetime import date
today = date.today().strftime("%B %d, %Y")

# ── Config ─────────────────────────────────────────────────────────────────────
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

DOER_MODEL   = "llama3.1:8b"   # classifies the article
CRITIC_MODEL = "qwen3.5:9b"    # validates the classification
MAX_ROUNDS   = 3               # max retries per article before giving up
# ──────────────────────────────────────────────────────────────────────────────

ALLOWED = [
    "Financial", "corporate", "regulation", "sanction",
    "residential", "non-residential", "technology", "events", "others"
]

CATEGORIES_DESCRIPTION = (
    "Financial    → about money, markets, economy (not a specific company)\n"
    "corporate    → about what a specific company does\n"
    "regulation   → about laws, rules, compliance\n"
    "sanction     → about penalties, fines, enforcement actions\n"
    "residential  → construction of homes, apartments, housing\n"
    "non-residential → construction of offices, warehouses, infrastructure\n"
    "technology   → about a product, tool, or technology\n"
    "events       → special or extraordinary events\n"
    "others       → anything that doesn't fit the above"
)

DOER_SYSTEM = (
    "You are a master classifier for a construction news dashboard. "
    "You must assign each article to EXACTLY one category from this list: "
    + ", ".join(ALLOWED) + ".\n\n"
    "Category definitions:\n" + CATEGORIES_DESCRIPTION + "\n\n"
    "Rules:\n"
    "- NEVER create new categories.\n"
    "- Reply with ONE word only — the category name, nothing else."
)

CRITIC_SYSTEM = (
    "You are a strict quality reviewer for a construction news classifier. "
    "You will be given an article title, its summary, and the category it was assigned.\n\n"
    "Category definitions:\n" + CATEGORIES_DESCRIPTION + "\n\n"
    "Your job:\n"
    "1. Check if the assigned category is the best fit.\n"
    "2. If YES → reply with exactly: APPROVED\n"
    "3. If NO  → reply with one short sentence explaining why it's wrong, "
    "then on a new line write: SUGGEST: <correct_category>\n"
    "   The correct category must be one of: " + ", ".join(ALLOWED) + ".\n"
    "Be strict but fair. Only approve if the category genuinely makes sense."
)


def doer_classify(title: str, summary: str, feedback: str = None) -> str:
    """Doer: classify the article, optionally incorporating critic feedback."""
    if feedback:
        user_msg = (
            f"Title: {title}\nSummary: {summary}\n\n"
            f"Your previous classification was rejected. Critic's feedback:\n{feedback}\n\n"
            f"Reconsider and reply with one word only — the correct category."
        )
    else:
        user_msg = f"Title: {title}\nSummary: {summary}\n\nCategory:"

    response = client.chat.completions.create(
        model=DOER_MODEL,
        messages=[
            {"role": "system", "content": DOER_SYSTEM},
            {"role": "user",   "content": user_msg}
        ],
        temperature=0.0,
        max_tokens=20,
    )
    raw = response.choices[0].message.content.strip()
    for word in ALLOWED:
        if word.lower() in raw.lower():
            return word
    return None  # couldn't parse a valid category


def critic_review(title: str, summary: str, category: str) -> str:
    """Critic: validate the doer's classification. Returns 'APPROVED' or critique."""
    user_msg = (
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Assigned category: {category}"
    )
    response = client.chat.completions.create(
        model=CRITIC_MODEL,
        messages=[
            {"role": "system", "content": CRITIC_SYSTEM},
            {"role": "user",   "content": user_msg}
        ],
        temperature=0.0,
        max_tokens=500,
        extra_body={"think": False},  # disable thinking mode, saves tokens
    )
    return response.choices[0].message.content.strip()


def extract_critic_suggestion(verdict: str) -> str:
    """Parse the critic's suggested category from its feedback, if present."""
    for line in verdict.splitlines():
        if line.upper().startswith("SUGGEST:"):
            suggested = line.split(":", 1)[1].strip()
            for word in ALLOWED:
                if word.lower() in suggested.lower():
                    return word
    return None


def classify_with_review(title: str, summary: str) -> tuple[str, int]:
    """
    Run the critic-actor loop for a single article.
    Returns (final_category, rounds_taken).
    """
    feedback      = None
    last_category = None

    for round_num in range(1, MAX_ROUNDS + 1):
        # ── Doer classifies ────────────────────────────────────────────────
        category = doer_classify(title, summary, feedback)
        if not category:
            print(f"  ⚠  Round {round_num}: Doer returned unparseable output, retrying…")
            continue

        last_category = category

        # ── Critic reviews ─────────────────────────────────────────────────
        verdict = critic_review(title, summary, category)

        if verdict.strip().upper().startswith("APPROVED"):
            return category, round_num

        # Critic rejected — pass full critique back to doer
        first_line = verdict.splitlines()[0] if verdict.splitlines() else "(no response)"
        print(f"  ↺  Round {round_num}: [{category}] rejected → {first_line}")
        feedback = verdict

        # If critic explicitly suggested a category, the doer will see it in feedback
        # But also use it as a fallback if we hit max rounds
        suggestion = extract_critic_suggestion(verdict)
        if suggestion:
            last_category = suggestion

    # Max rounds hit — use last known best guess
    print(f"  ⚠  Max rounds reached. Using best guess: [{last_category}]")
    return last_category or "others", MAX_ROUNDS


# ── Load, Process, Save ────────────────────────────────────────────────────────
with open("newsletter.json", "r", encoding="utf-8") as file:
    articles = json.load(file)

print(f"Classifying {len(articles)} articles with {DOER_MODEL} (doer) + {CRITIC_MODEL} (critic)…\n")

for i, article in enumerate(articles, 1):
    title   = article.get("title", "")
    summary = article.get("summary", "")

    category, rounds = classify_with_review(title, summary)
    article["category"] = category

    rounds_label = f"{rounds}r" if rounds > 1 else "✓"
    print(f"[{rounds_label}] [{category}] {title[:60]}…")

with open("articles_classified.json", "w", encoding="utf-8") as file:
    json.dump(articles, file, indent=2, ensure_ascii=False)

print("\n--- Processing Complete: 'articles_classified.json' is ready. ---\n")


# ── PDF Generation (unchanged) ────────────────────────────────────────────────
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

style_toc_title = ParagraphStyle("toc_title", fontSize=24, fontName="Helvetica-Bold", textColor=colors.HexColor("#2C3E50"), spaceAfter=16)
style_toc_link  = ParagraphStyle("toc_link",  fontSize=13, fontName="Helvetica",      textColor=colors.HexColor("#2980B9"), spaceAfter=10)
style_cat       = ParagraphStyle("cat",       fontSize=18, fontName="Helvetica-Bold", textColor=colors.HexColor("#2C3E50"), spaceAfter=8, spaceBefore=10)
style_title     = ParagraphStyle("title",     fontSize=12, fontName="Helvetica-Bold", textColor=colors.HexColor("#1A1A1A"), spaceAfter=4, spaceBefore=12)
style_url       = ParagraphStyle("url",       fontSize=8,  fontName="Helvetica-Oblique", textColor=colors.HexColor("#7F8C8D"), spaceAfter=4)
style_summary   = ParagraphStyle("summary",   fontSize=10, fontName="Helvetica",      textColor=colors.HexColor("#333333"), spaceAfter=4, leading=16)
style_back      = ParagraphStyle("back",      fontSize=9,  fontName="Helvetica-Oblique", textColor=colors.HexColor("#2980B9"), spaceAfter=12, spaceBefore=10)

sites     = list(dict.fromkeys(a["site"].replace("https://www.", "").replace("/", "").split(".")[0].capitalize() for a in articles if "site" in a))
title_text = " | ".join(sites)
file_name  = title_text.replace(" | ", "") + " " + today + ".pdf"

doc   = SimpleDocTemplate(file_name, pagesize=letter,
                          leftMargin=inch, rightMargin=inch,
                          topMargin=inch,  bottomMargin=inch)
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
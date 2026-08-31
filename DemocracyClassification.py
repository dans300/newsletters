import re
import time
from collections import Counter




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
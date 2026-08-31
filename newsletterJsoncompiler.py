"""Merge several article JSON files into one.

Keeps only title, url and summary. Skips articles whose URL already appeared.
"""

import json
from pathlib import Path

INPUT_DIR = Path("jsons")                    # folder holding your .json files
OUTPUT_FILE = Path("ALLnewsletter.json")      # where the merged result goes
FIELDS = ("title", "url", "summary")


def iter_articles(data):
    """Yield article dicts, whether the file is a flat list or grouped by category."""
    if isinstance(data, list):
        yield from data
    elif isinstance(data, dict):
        for group in data.values():
            if isinstance(group, list):
                yield from group


def main():
    merged = []
    seen_urls = set()

    for path in sorted(INPUT_DIR.glob("*.json")):
        if path.resolve() == OUTPUT_FILE.resolve():
            continue  # don't re-read a previous run's output

        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        kept = skipped = 0
        for article in iter_articles(data):
            if not isinstance(article, dict):
                continue
            url = article.get("url")
            if url and url in seen_urls:
                skipped += 1
                continue
            if url:
                seen_urls.add(url)
            merged.append({key: article.get(key) for key in FIELDS})
            kept += 1

        print(f"{path.name}: +{kept} kept, {skipped} duplicates skipped")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n{len(merged)} articles written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
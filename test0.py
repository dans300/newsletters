from firecrawl import Firecrawl

firecrawl = Firecrawl(api_key="fc-3840d2d759ba4fc780bdbe2cf53ddfa5")
# Scrape a website:
doc = firecrawl.scrape("https://batiactu.dev", formats=["markdown", "html"])
print(doc)
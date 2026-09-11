import requests
import feedparser
from firecrawl import Firecrawl






app = Firecrawl(api_key="fc-5be3e611cd87485e9e703556a4522f78")


your_sites_list = [
    {"name": "Security and sales", "feed_url": "http://feeds.feedburner.com/SecuritySalesIntegration", "needs_firecrawl": False} 
]


    #{"rss": True,"name": "Batiactu", "feed_url": "https://www.batiactu.com/accueil.rss", "needs_firecrawl": False} 36/36
    #{"rss": True,"name": "LeMoniteur", "feed_url": "https://www.lemoniteur.fr/arc/outboundfeeds/rss/", "needs_firecrawl": False} ,46/46
    #{"rss": True,"name": "FIEC", "feed_url": "https://us14.campaign-archive.com/feed?u=f8bcf676bb27fc2419df09e98&id=c744bdaafe", "needs_firecrawl": False} , 10/10 pero mete todas las ns au passé
    #{"rss": True,"name": "Bauinfoconsult", "feed_url": "https://bauinfoconsult.de/feed/", "needs_firecrawl": False} 12/12
    #{"rss": True,"name": "Security and sales", "feed_url": "http://feeds.feedburner.com/SecuritySalesIntegration", "needs_firecrawl": False} 12/12
    #{"rss": True,"name": "GEB", "feed_url": "https://www.geb-info.de/rss_feed/geb-rss-feed-meldungen", "needs_firecrawl": False} 20/20
    #{"rss": True,"name": "Glaswelt", "feed_url": "https://www.glaswelt.de/rss_feed/gw-rss-feed-meldungen", "needs_firecrawl": False} 20/20
    #{"rss": True,"name": "Haustec", "feed_url": "https://www.haustec.de/rss/heizung", "needs_firecrawl": False} 30/30
    #{"rss": True,"name": "EBC", "feed_url": "https://us11.campaign-archive.com/feed?u=3c690b345db3823f0db0cac0f&id=bfc8c22a7a", "needs_firecrawl": False} 10/10
    #{"rss": True,"name": "kunststoff", "feed_url": "https://www.kunststoffweb.de/rss/", "needs_firecrawl": False} 7/7
    #{"rss": True,"name": "avproGlobal", "feed_url": "https://www.avproglobal.com/blogs/news/tagged/avpro-global.atom", "needs_firecrawl": False}30/30
    #{"rss": True,"name": "WindowVision", "feed_url": "https://www.wf-vision.com/feed/", "needs_firecrawl": True} 10/10
        

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






for site in your_sites_list:
    articles = get_articles_from_rss(site["feed_url"], site["needs_firecrawl"])
    print(" "+site["name"], len(articles))
    for a in articles:
        print(f" TEST {a.get('title', 'No Title')} — {a.get('url', 'No URL')}")




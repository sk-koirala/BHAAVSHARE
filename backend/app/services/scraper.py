"""
BhaavShare news & social scraper.

Pulls from:
  • 15+ Nepali/English RSS feeds (finance + general)
  • Reddit (r/NepalStock, r/Nepal, r/investing, r/stocks, r/NEPSE) via public JSON
  • Curated Nepali finance portals (ShareHub, MeroLagani, Clickmandu, Nepali Times)
  • Fallback mock data so UI never looks empty

Every item carries:
    source, source_type (rss | reddit | mock), category, language, published_at
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import random
import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 BhaavShareBot/1.0"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, application/json, */*",
}

# ============================================================
# RSS SOURCES — 15+ Nepali & English finance/market outlets
# ============================================================
RSS_SOURCES = [
    # --- Dedicated Nepali finance / NEPSE outlets ---
    {"url": "https://www.sharesansar.com/rss",                         "name": "ShareSansar",       "lang": "en", "focus": "finance"},
    {"url": "https://merolagani.com/Feed.aspx",                        "name": "MeroLagani",        "lang": "en", "focus": "finance"},
    {"url": "https://nepsealpha.com/feed",                             "name": "NepseAlpha",        "lang": "en", "focus": "finance"},
    {"url": "https://www.nepalstock.com.np/rss",                       "name": "NEPSE Official",    "lang": "en", "focus": "finance"},
    {"url": "https://www.ekagaj.com/feed",                             "name": "Ekagaj",            "lang": "ne", "focus": "finance"},
    {"url": "https://arthasarokar.com/feed",                           "name": "ArthaSarokar",      "lang": "ne", "focus": "finance"},
    {"url": "https://arthakabar.com/feed",                             "name": "ArthaKabar",        "lang": "ne", "focus": "finance"},
    {"url": "https://bizmandu.com/feed",                               "name": "Bizmandu",          "lang": "ne", "focus": "finance"},
    {"url": "https://clickmandu.com/feed",                             "name": "Clickmandu",        "lang": "ne", "focus": "finance"},
    {"url": "https://nepalnewsbank.com/feed",                          "name": "NepalNewsBank",     "lang": "ne", "focus": "finance"},
    {"url": "https://www.onlinekhabar.com/content/arthik/feed",        "name": "OnlineKhabar Arthik", "lang": "ne", "focus": "finance"},
    {"url": "https://bizpati.com/feed",                                "name": "BizPati",           "lang": "ne", "focus": "finance"},
    {"url": "https://www.karobardaily.com/feed",                       "name": "Karobar Daily",     "lang": "ne", "focus": "finance"},
    {"url": "https://nepalipaisa.com/feed",                            "name": "NepaliPaisa",       "lang": "ne", "focus": "finance"},
    {"url": "https://www.newbusinessage.com/feed",                     "name": "New Business Age",  "lang": "en", "focus": "finance"},

    # --- Nepali general outlets (finance-filtered) ---
    {"url": "https://ratopati.com/feed",                               "name": "RatoPati",          "lang": "ne", "focus": "general"},
    {"url": "https://www.setopati.com/feed",                           "name": "Setopati",          "lang": "ne", "focus": "general"},
    {"url": "https://khabarhub.com/feed/",                             "name": "KhabarHub",         "lang": "ne", "focus": "general"},

    # --- English general outlets (finance-filtered) ---
    {"url": "https://kathmandupost.com/feed",                          "name": "Kathmandu Post",    "lang": "en", "focus": "general"},
    {"url": "https://myrepublica.nagariknetwork.com/feed",             "name": "Republica",         "lang": "en", "focus": "general"},
    {"url": "https://english.onlinekhabar.com/feed",                   "name": "OnlineKhabar EN",   "lang": "en", "focus": "general"},
    {"url": "https://thehimalayantimes.com/feed",                      "name": "Himalayan Times",   "lang": "en", "focus": "general"},
    {"url": "https://www.nepalitimes.com/feed",                        "name": "Nepali Times",      "lang": "en", "focus": "general"},

    # --- Global markets (for macro / sentiment context) ---
    {"url": "https://www.investing.com/rss/news_25.rss",               "name": "Investing.com",     "lang": "en", "focus": "finance"},
    {"url": "https://feeds.marketwatch.com/marketwatch/topstories/",   "name": "MarketWatch",       "lang": "en", "focus": "finance"},
    {"url": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "name": "WSJ Markets",   "lang": "en", "focus": "finance"},
    {"url": "https://www.ft.com/?format=rss",                          "name": "Financial Times",   "lang": "en", "focus": "finance"},
    {"url": "https://finance.yahoo.com/news/rssindex",                 "name": "Yahoo Finance",     "lang": "en", "focus": "finance"},
    {"url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",    "name": "CNBC Markets",      "lang": "en", "focus": "finance"},
    {"url": "https://www.reutersagency.com/feed/?best-topics=business-finance", "name": "Reuters Finance", "lang": "en", "focus": "finance"},
]

# ============================================================
# REDDIT SOURCES — Public JSON API, no auth needed
# ============================================================
REDDIT_SUBREDDITS = [
    {"name": "NepalStock",     "lang": "en", "focus": "finance"},
    {"name": "NEPSE",          "lang": "en", "focus": "finance"},
    {"name": "Nepal",          "lang": "en", "focus": "general"},
    {"name": "nepali",         "lang": "en", "focus": "general"},
    {"name": "investing",      "lang": "en", "focus": "finance"},
    {"name": "stocks",         "lang": "en", "focus": "finance"},
    {"name": "StockMarket",    "lang": "en", "focus": "finance"},
    {"name": "IndiaInvestments", "lang": "en", "focus": "finance"},
    {"name": "wallstreetbets", "lang": "en", "focus": "finance"},
    {"name": "SecurityAnalysis", "lang": "en", "focus": "finance"},
    {"name": "ValueInvesting", "lang": "en", "focus": "finance"},
    {"name": "financialindependence", "lang": "en", "focus": "finance"},
]

# ============================================================
# Finance keyword filters
# ============================================================
FINANCE_KEYWORDS_EN = [
    "nepse", "stock", "share", "market", "bank", "investment", "ipo", "dividend",
    "trading", "bull", "bear", "index", "nrb", "rastra bank", "monetary", "fiscal",
    "insurance", "hydropower", "finance", "mutual fund", "bonus", "agm", "quarter",
    "profit", "loss", "revenue", "earnings", "capital", "debenture", "sebon",
    "broker", "portfolio", "liquidity", "interest rate", "inflation", "gdp",
    "remittance", "export", "import", "trade deficit", "economic", "budget",
    "microfinance", "cooperatives", "loan", "credit", "deposit", "equity",
    "merger", "acquisition", "earning", "rally", "crash", "correction",
]

FINANCE_KEYWORDS_NE = [
    "नेप्से", "शेयर", "बजार", "बैंक", "लगानी", "आईपीओ", "लाभांश",
    "कारोबार", "सूचकांक", "राष्ट्र बैंक", "मौद्रिक", "बीमा", "जलविद्युत",
    "वित्त", "नाफा", "घाटा", "आम्दानी", "पूँजी", "ऋणपत्र", "सेबोन",
    "ब्रोकर", "तरलता", "ब्याजदर", "मुद्रास्फीति", "बजेट", "अर्थतन्त्र",
    "रेमिट्यान्स", "निर्यात", "आयात", "व्यापार", "ऋण", "निक्षेप",
    "सहकारी", "लघुवित्त", "खुद सम्पत्ति", "परिसूचक",
]


def is_finance_related(title: str, summary: str, source_focus: str) -> bool:
    """Filter articles to keep only finance-relevant ones."""
    if source_focus == "finance":
        return True
    combined = (title + " " + summary).lower()
    for kw in FINANCE_KEYWORDS_EN:
        if kw in combined:
            return True
    for kw in FINANCE_KEYWORDS_NE:
        if kw in combined:
            return True
    return False


def classify_category(title: str, summary: str) -> str:
    """Classify into a human-readable category badge."""
    text = (title + " " + summary).lower()
    if any(w in text for w in ["ipo", "आईपीओ", "public offering", "fpo"]):
        return "IPO"
    if any(w in text for w in ["dividend", "लाभांश", "bonus", "बोनस"]):
        return "Dividend"
    if any(w in text for w in ["bank", "nrb", "रास्त्र", "loan", "deposit", "निक्षेप", "ऋण"]):
        return "Banking"
    if any(w in text for w in ["hydro", "जलविद्युत", "hydropower"]):
        return "Hydropower"
    if any(w in text for w in ["insurance", "बीमा"]):
        return "Insurance"
    if any(w in text for w in ["budget", "बजेट", "fiscal", "economy", "अर्थतन्त्र", "gdp"]):
        return "Economy"
    if any(w in text for w in ["nepse", "नेप्से", "index", "सूचकांक", "market", "बजार"]):
        return "Market"
    return "General"


def clean_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:500] if len(clean) > 500 else clean


# ============================================================
# RSS fetcher
# ============================================================
def fetch_rss_news(source: dict, limit: int = 15) -> List[Dict]:
    url = source["url"]
    source_name = source["name"]
    language = source["lang"]
    focus = source["focus"]

    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        if not feed.entries:
            logger.warning(f"No entries from {source_name}")
            return []

        items = []
        for entry in feed.entries[:limit]:
            title = (entry.get("title") or "").strip()
            summary = clean_html(entry.get("summary", ""))
            link = entry.get("link", "")

            if not title or not link:
                continue
            if not is_finance_related(title, summary, focus):
                continue

            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                except Exception:
                    pass

            items.append({
                "title": title,
                "url": link,
                "summary": summary,
                "source": source_name,
                "source_type": "rss",
                "category": classify_category(title, summary),
                "language": language,
                "published_at": pub_date,
            })

        logger.info(f"[RSS] {source_name}: {len(items)} items")
        return items

    except Exception as e:
        logger.error(f"RSS fetch failed for {source_name}: {e}")
        return []


# ============================================================
# Reddit fetcher — public JSON API
# ============================================================
def fetch_reddit_posts(sub: dict, limit: int = 15) -> List[Dict]:
    """Fetch top posts from a subreddit via Reddit's public JSON endpoint."""
    name = sub["name"]
    try:
        url = f"https://www.reddit.com/r/{name}/hot.json?limit={limit}"
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            logger.warning(f"[Reddit] r/{name} → HTTP {r.status_code}")
            return []

        payload = r.json()
        children = payload.get("data", {}).get("children", [])
        items = []

        for ch in children:
            d = ch.get("data", {})
            title = (d.get("title") or "").strip()
            selftext = clean_html(d.get("selftext") or "")
            permalink = d.get("permalink", "")
            if not title or not permalink:
                continue
            if d.get("stickied"):
                continue
            if not is_finance_related(title, selftext, sub["focus"]):
                continue

            created = d.get("created_utc")
            pub_date = (
                datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                if created else None
            )
            score = d.get("score", 0)
            comments = d.get("num_comments", 0)
            summary = (
                selftext[:400]
                if selftext
                else f"{score} upvotes • {comments} comments on r/{name}"
            )

            items.append({
                "title": title,
                "url": f"https://www.reddit.com{permalink}",
                "summary": summary,
                "source": f"r/{name}",
                "source_type": "reddit",
                "category": classify_category(title, selftext),
                "language": sub["lang"],
                "published_at": pub_date,
            })

        logger.info(f"[Reddit] r/{name}: {len(items)} items")
        return items
    except Exception as e:
        logger.error(f"Reddit fetch failed for r/{name}: {e}")
        return []


# ============================================================
# HackerNews — Algolia search API for finance/market discussions
# ============================================================
HN_QUERIES = ["NEPSE", "stock market", "dividend", "IPO", "central bank", "monetary policy"]


def fetch_hackernews(query: str, limit: int = 10) -> List[Dict]:
    try:
        url = f"https://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story&hitsPerPage={limit}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return []
        hits = r.json().get("hits", [])
        items = []
        for h in hits:
            title = (h.get("title") or h.get("story_title") or "").strip()
            link = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            summary = f"{h.get('points', 0)} points · {h.get('num_comments', 0)} comments on HackerNews"
            if not title:
                continue
            if not is_finance_related(title, summary, "finance"):
                continue
            items.append({
                "title": title,
                "url": link,
                "summary": summary,
                "source": "HackerNews",
                "source_type": "social",
                "category": classify_category(title, summary),
                "language": "en",
                "published_at": h.get("created_at"),
            })
        logger.info(f"[HN] '{query}': {len(items)} items")
        return items
    except Exception as e:
        logger.error(f"HN fetch failed for '{query}': {e}")
        return []


# ============================================================
# Aggregator
# ============================================================
def scrape_all_news() -> List[Dict]:
    """Scrape RSS + Reddit + HackerNews and return deduped, categorized news."""
    all_items: List[Dict] = []

    for source in RSS_SOURCES:
        all_items.extend(fetch_rss_news(source, limit=12))

    for sub in REDDIT_SUBREDDITS:
        all_items.extend(fetch_reddit_posts(sub, limit=10))

    for q in HN_QUERIES:
        all_items.extend(fetch_hackernews(q, limit=6))

    # Dedupe by URL
    seen = set()
    unique = []
    for item in all_items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    rss_count = sum(1 for i in unique if i.get("source_type") == "rss")
    reddit_count = sum(1 for i in unique if i.get("source_type") == "reddit")
    logger.info(
        f"[Scrape] {len(unique)} unique — "
        f"{rss_count} RSS from {len({i['source'] for i in unique if i['source_type']=='rss'})} sources, "
        f"{reddit_count} Reddit posts"
    )

    if not unique:
        logger.warning("All scrapers failed — falling back to mock data.")
        return generate_mock_news()

    return unique


# ============================================================
# MeroLagani live price scrape (best-effort)
# ============================================================
def scrape_nepse_prices():
    try:
        response = requests.get(
            "https://merolagani.com/LatestMarket.aspx",
            headers=HEADERS,
            timeout=15,
        )
        if response.status_code != 200:
            raise Exception(f"Status {response.status_code}")

        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", {"class": "table table-hover live-trading sortable"})
        if not table:
            raise Exception("Price table not found")

        rows = table.find("tbody").find_all("tr")
        prices = []
        for row in rows[:30]:
            cols = row.find_all("td")
            if len(cols) >= 6:
                try:
                    prices.append({
                        "symbol": cols[0].text.strip(),
                        "close_price": float(cols[1].text.strip().replace(",", "")),
                        "volume": float(cols[5].text.strip().replace(",", "")),
                        "turnover": 0.0,
                    })
                except ValueError:
                    continue
        return prices
    except Exception as e:
        logger.warning(f"Live price scrape failed: {e}. Using mock data.")
        return generate_mock_prices()


# ============================================================
# Fallback mocks
# ============================================================
def generate_mock_news():
    now = datetime.now(timezone.utc).isoformat()
    base = [
        ("NEPSE index gains 40 points as banking sector leads rally", "The benchmark NEPSE index surged 40 points today driven by heavy buying in commercial banks.", "ShareSansar", "en", "Market"),
        ("नेप्से परिसूचकमा ३५ अंकको वृद्धि, कारोबार रकम ५ अर्ब नाघ्यो", "आज शेयर बजारमा ३५ अंकको सुधार भएको छ।", "ArthaSarokar", "ne", "Market"),
        ("NRB announces new monetary policy: Interest rates expected to drop", "Nepal Rastra Bank signals easing in its mid-term review.", "Kathmandu Post", "en", "Banking"),
        ("NABIL Bank reports 15% growth in quarterly profits", "Nabil Bank Limited posted strong Q3 results with net profit reaching NPR 2.1 billion.", "MeroLagani", "en", "Banking"),
        ("सेबोनले आईपीओ अनुमति दियो: तीन कम्पनी सूचीकरणमा", "सेबोनले तीन नयाँ कम्पनीलाई आईपीओ जारी गर्न अनुमति प्रदान गरेको छ।", "OnlineKhabar Arthik", "ne", "IPO"),
        ("Hydropower stocks surge as monsoon forecast shows above-normal rainfall", "Investors are bullish on hydropower companies with favorable monsoon predictions.", "Bizmandu", "en", "Hydropower"),
        ("Discussion: Best banking stocks for 2026 accumulation", "Community discussing long-term picks across Nepali commercial banks.", "r/NepalStock", "en", "Banking"),
        ("Insurance sector faces regulatory overhaul from NRB directives", "New NRB directives may reshape the insurance landscape in Nepal.", "Republica", "en", "Insurance"),
        ("बैंकहरूको खुद नाफामा कमी, ब्याजदरमा कटौतीको असर", "केन्द्रीय बैंकले ब्याजदर घटाएपछि बैंकहरूको नाफामा प्रभाव परेको छ।", "RatoPati", "ne", "Banking"),
        ("Global markets rally on tech earnings beat", "US and Asian indices up as major tech giants report strong quarterly numbers.", "MarketWatch", "en", "Market"),
    ]
    return [
        {
            "title": t,
            "url": f"https://bhaavshare.local/mock/{i}",
            "summary": s,
            "source": src,
            "source_type": "reddit" if src.startswith("r/") else "rss",
            "category": cat,
            "language": lang,
            "published_at": now,
        }
        for i, (t, s, src, lang, cat) in enumerate(base)
    ]


def generate_mock_prices():
    symbols = ["NABIL", "NICA", "GBIME", "EBL", "HBL", "SCB", "NMB", "SANIMA", "UPPER", "API", "HIDCL", "NIFRA"]
    return [
        {
            "symbol": sym,
            "close_price": round(random.uniform(200, 2000), 2),
            "volume": round(random.uniform(1000, 50000), 2),
            "turnover": round(random.uniform(100000, 5000000), 2),
        }
        for sym in symbols
    ]

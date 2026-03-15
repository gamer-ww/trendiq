import os
import json
import requests
from datetime import datetime, timedelta
from pytrends.request import TrendReq
import google.generativeai as genai
from supabase import create_client

# ── Environment Variables (GitHub Secrets se aayenge) ──
SUPABASE_URL   = os.environ['SUPABASE_URL']
SUPABASE_KEY   = os.environ['SUPABASE_KEY']
YOUTUBE_KEY    = os.environ['YOUTUBE_API_KEY']
NEWS_KEY       = os.environ['NEWS_API_KEY']
GEMINI_KEY     = os.environ['GEMINI_API_KEY']
RAPIDAPI_KEY   = os.environ.get('RAPIDAPI_KEY', '')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)

# ── Topics jo track karne hain ──
TOPICS = [
    {"query": "LPG gas price India",        "category": "incidents",  "hashtag": "lpgpricehike"},
    {"query": "RBI interest rate India",    "category": "finance",    "hashtag": "rbipolicy"},
    {"query": "Bitcoin India price",        "category": "finance",    "hashtag": "bitcoinindia"},
    {"query": "AI India technology",        "category": "tech",       "hashtag": "aiindia"},
    {"query": "India Pakistan geopolitics", "category": "incidents",  "hashtag": "indiapakistan"},
    {"query": "Sensex Nifty stock market",  "category": "finance",    "hashtag": "stockmarket"},
    {"query": "India startup funding 2025", "category": "startups",   "hashtag": "startupindia"},
    {"query": "BRICS India geopolitics",    "category": "politics",   "hashtag": "brics"},
    {"query": "India economy GDP",          "category": "business",   "hashtag": "indianeconomy"},
    {"query": "Modi government policy",     "category": "politics",   "hashtag": "indiagovernment"},
    {"query": "petrol diesel price India",  "category": "incidents",  "hashtag": "petrolindia"},
    {"query": "Adani Ambani business news", "category": "business",   "hashtag": "indiabusiness"},
]

# ── 1. YouTube se trending videos fetch karo ──
def fetch_youtube(topic_query):
    print(f"  YouTube: {topic_query}")
    since = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet", "q": topic_query, "type": "video",
        "order": "viewCount", "publishedAfter": since,
        "regionCode": "IN", "maxResults": 10, "key": YOUTUBE_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        items = data.get('items', [])
        return {"video_count": len(items), "top_title": items[0]['snippet']['title'] if items else ""}
    except Exception as e:
        print(f"    YouTube error: {e}")
        return {"video_count": 0, "top_title": ""}

# ── 2. Google Trends se trend score lo ──
def fetch_google_trends(topic_query):
    print(f"  Google Trends: {topic_query}")
    try:
        pt = TrendReq(hl='en-IN', tz=330, timeout=(10, 25))
        pt.build_payload([topic_query], timeframe='now 1-d', geo='IN')
        df = pt.interest_over_time()
        if not df.empty and topic_query in df.columns:
            return int(df[topic_query].mean())
    except Exception as e:
        print(f"    Trends error: {e}")
    return 50

# ── 3. NewsAPI se news lo ──
def fetch_news(topic_query):
    print(f"  News: {topic_query}")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": topic_query, "language": "en",
        "sortBy": "publishedAt", "pageSize": 5, "apiKey": NEWS_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        articles = r.json().get('articles', [])
        sources = list(set([a['source']['name'] for a in articles[:3]]))
        return {"count": len(articles), "sources": sources}
    except Exception as e:
        print(f"    News error: {e}")
        return {"count": 0, "sources": []}

# ── 4. Instagram hashtag data (RapidAPI) ──
def fetch_instagram(hashtag):
    print(f"  Instagram: #{hashtag}")
    try:
        import instaloader
        L = instaloader.Instaloader()
        posts = instaloader.Hashtag.from_name(L.context, hashtag)
        count = posts.mediacount
        return {"reel_count": count, "views": count * 400}
    except Exception as e:
        print(f"    Instagram error: {e}")
        return {"reel_count": 0, "views": 0}

# ── 5. Gemini AI se analysis ──
def analyze_with_gemini(all_data):
    print("Gemini AI analysis ho rahi hai...")
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""
You are an AI content strategy assistant for Indian YouTube & Instagram creators.

Here is real trending data from India right now:
{json.dumps(all_data, indent=2, ensure_ascii=False)}

Your job:
1. Analyze which topics are most trending RIGHT NOW in India
2. Fact-check each topic (verified/partial/misleading) based on if it sounds like real news
3. Give creator recommendations

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "topics": [
    {{
      "title": "topic name in Hinglish (short, catchy)",
      "category": "tech/finance/politics/incidents/business/startups",
      "trend_score": 85,
      "fact_status": "verified",
      "youtube_videos": 45000,
      "youtube_views": "890M",
      "ig_hashtag": "#example",
      "ig_reels": 8000,
      "ig_views": "980K",
      "cross_platform": true,
      "since": "2 din se",
      "sources": "Times of India, NDTV",
      "yt_score": 85,
      "ig_score": 74
    }}
  ],
  "recommendations": [
    {{
      "title": "Video title idea in Hinglish",
      "score": 93,
      "reason": "reason in Hinglish",
      "platform": "both"
    }}
  ],
  "trending_audios": [
    {{
      "name": "audio name",
      "usage": "500K reels",
      "match": "kab use karo"
    }}
  ],
  "stats": {{
    "total_topics": 12,
    "verified_count": 8,
    "total_views": "8.2B",
    "top_category": "Finance"
  }}
}}

Make it realistic for India 2025. Topics should be in Hinglish. Max 10 topics.
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean up markdown if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Gemini error: {e}")
        return {"topics": [], "recommendations": [], "trending_audios": [], "stats": {}}

# ── 6. Supabase mein save karo ──
def save_to_supabase(analysis):
    print("Supabase mein save ho raha hai...")
    record = {
        "fetched_at": datetime.utcnow().isoformat(),
        "topics": analysis.get('topics', []),
        "recommendations": analysis.get('recommendations', []),
        "trending_audios": analysis.get('trending_audios', []),
        "stats": analysis.get('stats', {})
    }
    supabase.table('trendiq_data').insert(record).execute()
    print("Save ho gaya!")

# ── Main Function ──
def main():
    print("=" * 50)
    print(f"TrendIQ Fetch Start: {datetime.utcnow()}")
    print("=" * 50)

    all_raw_data = []

    for topic in TOPICS:
        print(f"\nTopic: {topic['query']}")
        yt_data   = fetch_youtube(topic['query'])
        gt_score  = fetch_google_trends(topic['query'])
        news_data = fetch_news(topic['query'])
        ig_data   = fetch_instagram(topic['hashtag'])

        all_raw_data.append({
            "topic":          topic['query'],
            "category":       topic['category'],
            "hashtag":        topic['hashtag'],
            "google_score":   gt_score,
            "yt_videos":      yt_data['video_count'],
            "yt_top_title":   yt_data['top_title'],
            "news_count":     news_data['count'],
            "news_sources":   news_data['sources'],
            "ig_reels":       ig_data['reel_count'],
            "ig_views":       ig_data['views'],
        })

    analysis = analyze_with_gemini(all_raw_data)
    save_to_supabase(analysis)

    print("\n" + "=" * 50)
    print("TrendIQ Fetch Complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()

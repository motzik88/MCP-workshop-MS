from typing import Optional
import httpx
import feedparser
from fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("ynet_feed")

FEED_URL = "https://www.ynet.co.il/Integration/StoryRss2.xml"  # Ynet main news RSS

async def fetch_rss(url: str) -> str | None:
    """Fetch raw RSS feed content asynchronously."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                print(f"❌ HTTP error: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
    return None

@mcp.tool()
async def get_headlines_from_ynet(limit: int = 5) -> str:
    """Fetch latest headlines from ynet.co.il

    Args:
        limit: Number of feed items to return (default 5)
    """
    raw_feed = await fetch_rss(FEED_URL)
    if not raw_feed:
        return "⚠️ Failed to fetch the RSS feed."

    feed = feedparser.parse(raw_feed)
    if not feed.entries:
        return "ℹ️ No entries found in the feed."

    entries = []
    for entry in feed.entries[:limit]:
        formatted = f"""
📰 {entry.title}
📅 {entry.get('published', 'No date')}
🔗 {entry.link}
""".strip()
        entries.append(formatted)

    return "\n\n---\n\n".join(entries)
# Run the server
if __name__ == "__main__":
    mcp.run(transport="stdio")

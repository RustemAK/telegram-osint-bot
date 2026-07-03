"""Web, social & knowledge sources.

Covers GitHub, GitLab, Wikipedia, Hacker News (Algolia), Reddit and NewsAPI.
The keyless variants (Wikipedia, HN, Reddit public JSON, unauthenticated
GitHub search at a low rate) always work; keyed variants add depth.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from bot.api.http_client import get_json
from bot.config import get_settings


async def github_user(username: str) -> dict[str, Any]:
    """Public GitHub profile lookup (token optional, raises rate limit)."""
    settings = get_settings()
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    data = await get_json(
        f"https://api.github.com/users/{quote(username)}", headers=headers
    )
    if not isinstance(data, dict) or data.get("message") == "Not Found":
        return {"skipped": "no GitHub user"}
    return {
        "name": data.get("name"),
        "company": data.get("company"),
        "location": data.get("location"),
        "bio": data.get("bio"),
        "public_repos": data.get("public_repos"),
        "followers": data.get("followers"),
        "created_at": data.get("created_at"),
        "profile": data.get("html_url"),
    }


async def github_search_code(query: str) -> dict[str, Any]:
    """Search public GitHub repositories mentioning a query term."""
    settings = get_settings()
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    data = await get_json(
        "https://api.github.com/search/repositories",
        params={"q": query, "per_page": 5, "sort": "stars"},
        headers=headers,
    )
    if not isinstance(data, dict) or "items" not in data:
        return {"skipped": "no GitHub results"}
    return {
        "total": data.get("total_count"),
        "top_repos": [
            {"name": r.get("full_name"), "stars": r.get("stargazers_count")}
            for r in data.get("items", [])[:5]
        ],
    }


async def gitlab_user(username: str) -> dict[str, Any]:
    """Public GitLab user lookup (token optional)."""
    settings = get_settings()
    headers = {}
    if settings.gitlab_token:
        headers["PRIVATE-TOKEN"] = settings.gitlab_token
    data = await get_json(
        "https://gitlab.com/api/v4/users",
        params={"username": username},
        headers=headers or None,
    )
    if not isinstance(data, list) or not data:
        return {"skipped": "no GitLab user"}
    user = data[0]
    return {
        "name": user.get("name"),
        "state": user.get("state"),
        "profile": user.get("web_url"),
        "created_at": user.get("created_at"),
    }


async def wikipedia_summary(term: str) -> dict[str, Any]:
    """Wikipedia REST summary for a term / company / person (keyless)."""
    data = await get_json(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(term)}"
    )
    if not isinstance(data, dict) or data.get("type", "").endswith("not_found"):
        return {"skipped": "no Wikipedia article"}
    return {
        "title": data.get("title"),
        "description": data.get("description"),
        "extract": (data.get("extract") or "")[:600],
        "url": (data.get("content_urls", {}).get("desktop", {}) or {}).get("page"),
    }


async def hackernews(term: str) -> dict[str, Any]:
    """Search Hacker News via the Algolia API (keyless)."""
    data = await get_json(
        "https://hn.algolia.com/api/v1/search",
        params={"query": term, "tags": "story", "hitsPerPage": 5},
    )
    if not isinstance(data, dict) or "hits" not in data:
        return {"skipped": "no HN results"}
    return {
        "hits": [
            {"title": h.get("title"), "url": h.get("url"), "points": h.get("points")}
            for h in data.get("hits", [])[:5]
            if h.get("title")
        ]
    }


async def reddit_search(term: str) -> dict[str, Any]:
    """Search Reddit's public JSON endpoint (keyless)."""
    data = await get_json(
        "https://www.reddit.com/search.json",
        params={"q": term, "limit": 5, "sort": "relevance"},
    )
    if not isinstance(data, dict) or "data" not in data:
        return {"skipped": "no Reddit results"}
    children = data["data"].get("children", [])
    return {
        "posts": [
            {
                "title": c.get("data", {}).get("title"),
                "subreddit": c.get("data", {}).get("subreddit"),
                "score": c.get("data", {}).get("score"),
            }
            for c in children[:5]
        ]
    }


async def news(term: str) -> dict[str, Any]:
    """Recent news headlines via NewsAPI (requires NEWSAPI_KEY)."""
    settings = get_settings()
    if not settings.newsapi_key:
        return {"skipped": "no NEWSAPI_KEY"}
    data = await get_json(
        "https://newsapi.org/v2/everything",
        params={"q": term, "pageSize": 5, "sortBy": "publishedAt", "language": "en"},
        headers={"X-Api-Key": settings.newsapi_key},
    )
    if not isinstance(data, dict) or data.get("status") != "ok":
        return {"skipped": "no news"}
    return {
        "articles": [
            {"title": a.get("title"), "source": a.get("source", {}).get("name")}
            for a in data.get("articles", [])[:5]
        ]
    }


async def hibp_breaches(email: str) -> dict[str, Any]:
    """Have I Been Pwned breach check (requires HIBP_API_KEY).

    LEGAL NOTE: HIBP should only be used to check email addresses you own or
    are authorised to check. This is surfaced to the user in the UI.
    """
    settings = get_settings()
    if not settings.hibp_api_key:
        return {"skipped": "no HIBP_API_KEY"}
    data = await get_json(
        f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email)}",
        params={"truncateResponse": "true"},
        headers={"hibp-api-key": settings.hibp_api_key, "User-Agent": "OSINT-Bot"},
    )
    if not isinstance(data, list):
        return {"breaches": [], "note": "no breaches found or not authorised"}
    return {"breaches": [b.get("Name") for b in data if isinstance(b, dict)]}

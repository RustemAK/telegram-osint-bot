"""IP intelligence sources.

Combines keyless geolocation (ip-api.com, ipinfo.io free tier) with optional
key-based reputation sources (AbuseIPDB, GreyNoise, Shodan). Sources without a
configured key are skipped gracefully.
"""

from __future__ import annotations

from typing import Any

from bot.api.http_client import get_json
from bot.config import get_settings


async def ip_api(ip: str) -> dict[str, Any]:
    """Free geolocation & ASN data from ip-api.com (no key required)."""
    data = await get_json(
        f"http://ip-api.com/json/{ip}",
        params={
            "fields": "status,country,regionName,city,isp,org,as,lat,lon,timezone,reverse"
        },
    )
    if not isinstance(data, dict) or data.get("status") != "success":
        return {"skipped": "no geo data"}
    return {
        "country": data.get("country"),
        "region": data.get("regionName"),
        "city": data.get("city"),
        "isp": data.get("isp"),
        "org": data.get("org"),
        "asn": data.get("as"),
        "timezone": data.get("timezone"),
        "coordinates": f"{data.get('lat')}, {data.get('lon')}",
        "reverse": data.get("reverse"),
    }


async def ipinfo(ip: str) -> dict[str, Any]:
    """ipinfo.io lookup — richer with a token, limited but usable without one."""
    settings = get_settings()
    headers = {}
    if settings.ipinfo_token:
        headers["Authorization"] = f"Bearer {settings.ipinfo_token}"
    data = await get_json(f"https://ipinfo.io/{ip}/json", headers=headers or None)
    if not isinstance(data, dict) or "error" in data:
        return {"skipped": "no ipinfo data"}
    return {
        "hostname": data.get("hostname"),
        "org": data.get("org"),
        "city": data.get("city"),
        "region": data.get("region"),
        "country": data.get("country"),
        "location": data.get("loc"),
    }


async def abuseipdb(ip: str) -> dict[str, Any]:
    """AbuseIPDB reputation check (requires ABUSEIPDB_API_KEY)."""
    settings = get_settings()
    if not settings.abuseipdb_api_key:
        return {"skipped": "no ABUSEIPDB_API_KEY"}
    data = await get_json(
        "https://api.abuseipdb.com/api/v2/check",
        params={"ipAddress": ip, "maxAgeInDays": 90},
        headers={"Key": settings.abuseipdb_api_key, "Accept": "application/json"},
    )
    if not isinstance(data, dict) or "data" not in data:
        return {"skipped": "no AbuseIPDB data"}
    d = data["data"]
    return {
        "abuse_confidence": d.get("abuseConfidenceScore"),
        "total_reports": d.get("totalReports"),
        "country": d.get("countryCode"),
        "isp": d.get("isp"),
        "domain": d.get("domain"),
        "is_tor": d.get("isTor"),
    }


async def greynoise(ip: str) -> dict[str, Any]:
    """GreyNoise community context (requires GREYNOISE_API_KEY)."""
    settings = get_settings()
    if not settings.greynoise_api_key:
        return {"skipped": "no GREYNOISE_API_KEY"}
    data = await get_json(
        f"https://api.greynoise.io/v3/community/{ip}",
        headers={"key": settings.greynoise_api_key, "Accept": "application/json"},
    )
    if not isinstance(data, dict):
        return {"skipped": "no GreyNoise data"}
    return {
        "noise": data.get("noise"),
        "riot": data.get("riot"),
        "classification": data.get("classification"),
        "name": data.get("name"),
        "last_seen": data.get("last_seen"),
    }


async def shodan_host(ip: str) -> dict[str, Any]:
    """Shodan host information (requires SHODAN_API_KEY)."""
    settings = get_settings()
    if not settings.shodan_api_key:
        return {"skipped": "no SHODAN_API_KEY"}
    data = await get_json(
        f"https://api.shodan.io/shodan/host/{ip}",
        params={"key": settings.shodan_api_key},
    )
    if not isinstance(data, dict):
        return {"skipped": "no Shodan data"}
    return {
        "ports": data.get("ports", []),
        "hostnames": data.get("hostnames", []),
        "os": data.get("os"),
        "org": data.get("org"),
        "isp": data.get("isp"),
        "tags": data.get("tags", []),
        "vulns": list(data.get("vulns", []))[:20],
    }

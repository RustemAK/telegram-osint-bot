"""Domain / threat-intelligence sources.

Includes VirusTotal, SecurityTrails and Censys — all optional (key-gated).
"""

from __future__ import annotations

import base64
from typing import Any

from bot.api.http_client import get_json
from bot.config import get_settings


async def virustotal_domain(domain: str) -> dict[str, Any]:
    """VirusTotal v3 domain report (requires VIRUSTOTAL_API_KEY)."""
    settings = get_settings()
    if not settings.virustotal_api_key:
        return {"skipped": "no VIRUSTOTAL_API_KEY"}
    data = await get_json(
        f"https://www.virustotal.com/api/v3/domains/{domain}",
        headers={"x-apikey": settings.virustotal_api_key},
    )
    if not isinstance(data, dict) or "data" not in data:
        return {"skipped": "no VirusTotal data"}
    attrs = data["data"].get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    return {
        "reputation": attrs.get("reputation"),
        "malicious": stats.get("malicious"),
        "suspicious": stats.get("suspicious"),
        "harmless": stats.get("harmless"),
        "registrar": attrs.get("registrar"),
    }


async def virustotal_ip(ip: str) -> dict[str, Any]:
    """VirusTotal v3 IP report (requires VIRUSTOTAL_API_KEY)."""
    settings = get_settings()
    if not settings.virustotal_api_key:
        return {"skipped": "no VIRUSTOTAL_API_KEY"}
    data = await get_json(
        f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
        headers={"x-apikey": settings.virustotal_api_key},
    )
    if not isinstance(data, dict) or "data" not in data:
        return {"skipped": "no VirusTotal data"}
    attrs = data["data"].get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    return {
        "reputation": attrs.get("reputation"),
        "malicious": stats.get("malicious"),
        "suspicious": stats.get("suspicious"),
        "asn": attrs.get("asn"),
        "as_owner": attrs.get("as_owner"),
        "country": attrs.get("country"),
    }


async def virustotal_hash(file_hash: str) -> dict[str, Any]:
    """VirusTotal v3 file report by hash (requires VIRUSTOTAL_API_KEY)."""
    settings = get_settings()
    if not settings.virustotal_api_key:
        return {"skipped": "no VIRUSTOTAL_API_KEY"}
    data = await get_json(
        f"https://www.virustotal.com/api/v3/files/{file_hash}",
        headers={"x-apikey": settings.virustotal_api_key},
    )
    if not isinstance(data, dict) or "data" not in data:
        return {"skipped": "no VirusTotal data"}
    attrs = data["data"].get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    return {
        "meaningful_name": attrs.get("meaningful_name"),
        "type_description": attrs.get("type_description"),
        "size": attrs.get("size"),
        "malicious": stats.get("malicious"),
        "undetected": stats.get("undetected"),
        "sha256": attrs.get("sha256"),
    }


async def virustotal_url(url: str) -> dict[str, Any]:
    """VirusTotal v3 URL report (requires VIRUSTOTAL_API_KEY)."""
    settings = get_settings()
    if not settings.virustotal_api_key:
        return {"skipped": "no VIRUSTOTAL_API_KEY"}
    # VT expects the URL id as base64 (no padding).
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    data = await get_json(
        f"https://www.virustotal.com/api/v3/urls/{url_id}",
        headers={"x-apikey": settings.virustotal_api_key},
    )
    if not isinstance(data, dict) or "data" not in data:
        return {"skipped": "no VirusTotal data"}
    attrs = data["data"].get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    return {
        "malicious": stats.get("malicious"),
        "suspicious": stats.get("suspicious"),
        "harmless": stats.get("harmless"),
        "final_url": attrs.get("last_final_url"),
    }


async def securitytrails_domain(domain: str) -> dict[str, Any]:
    """SecurityTrails domain details (requires SECURITYTRAILS_API_KEY)."""
    settings = get_settings()
    if not settings.securitytrails_api_key:
        return {"skipped": "no SECURITYTRAILS_API_KEY"}
    data = await get_json(
        f"https://api.securitytrails.com/v1/domain/{domain}",
        headers={"APIKEY": settings.securitytrails_api_key},
    )
    if not isinstance(data, dict):
        return {"skipped": "no SecurityTrails data"}
    return {
        "hostname": data.get("hostname"),
        "alexa_rank": data.get("alexa_rank"),
        "apex_domain": data.get("apex_domain"),
        "current_dns": list((data.get("current_dns") or {}).keys()),
    }


async def censys_host(ip: str) -> dict[str, Any]:
    """Censys host view (requires CENSYS_API_ID + CENSYS_API_SECRET)."""
    settings = get_settings()
    if not (settings.censys_api_id and settings.censys_api_secret):
        return {"skipped": "no Censys credentials"}
    token = base64.b64encode(
        f"{settings.censys_api_id}:{settings.censys_api_secret}".encode()
    ).decode()
    data = await get_json(
        f"https://search.censys.io/api/v2/hosts/{ip}",
        headers={"Authorization": f"Basic {token}"},
    )
    if not isinstance(data, dict) or "result" not in data:
        return {"skipped": "no Censys data"}
    result = data["result"]
    return {
        "services": [
            f"{s.get('port')}/{s.get('service_name')}"
            for s in result.get("services", [])
        ],
        "location": result.get("location", {}).get("country"),
        "autonomous_system": result.get("autonomous_system", {}).get("name"),
    }

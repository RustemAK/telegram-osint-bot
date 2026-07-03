"""Certificate Transparency lookups via crt.sh (keyless).

crt.sh exposes a JSON endpoint listing logged TLS certificates for a domain,
which is a rich source of subdomains and issuance history.
"""

from __future__ import annotations

from typing import Any

from bot.api.http_client import get_json


async def crtsh(domain: str, limit: int = 25) -> dict[str, Any]:
    """Return recent certificates and discovered subdomains for a domain."""
    data = await get_json(
        "https://crt.sh/", params={"q": domain, "output": "json"}
    )
    if not isinstance(data, list) or not data:
        return {"skipped": "no CT logs"}

    subdomains: set[str] = set()
    certs: list[dict[str, Any]] = []

    for entry in data[: limit * 4]:
        if not isinstance(entry, dict):
            continue
        name_value = entry.get("name_value", "")
        for name in str(name_value).splitlines():
            name = name.strip().lstrip("*.")
            if name.endswith(domain):
                subdomains.add(name)
        if len(certs) < limit:
            certs.append(
                {
                    "issuer": entry.get("issuer_name"),
                    "not_before": entry.get("not_before"),
                    "not_after": entry.get("not_after"),
                }
            )

    return {
        "subdomains": sorted(subdomains)[:50],
        "subdomain_count": len(subdomains),
        "recent_certs": certs,
    }

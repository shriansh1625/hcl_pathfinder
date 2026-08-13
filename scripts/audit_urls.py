"""Live URL forensic check. Network is optional; unit tests do not import this."""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request

from app.ontology.load import ResourceSpec
from app.services.catalog.audit import UrlClass, classify_url


def probe_url(url: str, timeout: float = 8.0) -> tuple[bool, int | None, str]:
    ctx = ssl.create_default_context()
    headers = {"User-Agent": "PathFinderCatalogAudit/2.1"}
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
                code = getattr(response, "status", None) or response.getcode()
                return True, int(code), method
        except urllib.error.HTTPError as exc:
            if exc.code in {405, 403, 401} and method == "HEAD":
                continue
            if 200 <= exc.code < 400:
                return True, exc.code, method
            return False, exc.code, method
        except Exception:
            if method == "HEAD":
                continue
            return False, None, method
    return False, None, "GET"


def classify_live(resource: ResourceSpec) -> dict:
    static = classify_url(resource)
    payload = {
        "slug": resource.slug,
        "url": resource.url,
        "url_status": resource.url_status,
        "format_valid": static.format_valid,
        "accessible": None,
        "http_status": None,
        "classification": static.classification,
    }
    if not resource.url:
        payload["classification"] = "UNAVAILABLE_BY_POLICY"
        return payload
    if not static.format_valid:
        payload["classification"] = "URL_FORMAT_INVALID"
        return payload
    ok, code, _method = probe_url(resource.url)
    payload["accessible"] = ok
    payload["http_status"] = code
    if ok:
        payload["classification"] = "URL_ACCESSIBLE"
        if resource.url_status == "verified":
            payload["classification"] = "URL_VERIFIED_RESOURCE"
    else:
        payload["classification"] = "URL_FORMAT_VALID_NOT_CONFIRMED_ACCESSIBLE"
    return payload

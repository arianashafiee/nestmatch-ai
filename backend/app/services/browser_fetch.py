"""Browser-like HTTP fetch for sites that block plain httpx (Zillow, etc.)."""

from typing import Optional
from urllib.parse import urljoin

from app.services.search_fetcher import BROWSER_HEADERS, FetchResult, SITE_REFERERS

# PerimeterX on Zillow rejects Sec-Fetch-* and chrome impersonation from datacenter IPs.
ZILLOW_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

TRULIA_HEADERS = ZILLOW_HEADERS

SITE_IMPERSONATE = {
    "zillow.com": "safari17_0",
    "trulia.com": "safari17_0",
    "realtor.com": "chrome131",
    "apartments.com": "chrome131",
}

SITE_HEADERS = {
    "zillow.com": ZILLOW_HEADERS,
    "trulia.com": TRULIA_HEADERS,
}


def fetch_with_browser(
    url: str,
    site: str = "",
    params: Optional[dict] = None,
    timeout: float = 20.0,
    min_html_length: int = 2000,
) -> FetchResult:
    """Fetch a page using TLS/browser impersonation when curl_cffi is available."""
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        from app.services.search_fetcher import fetch_search_page

        return fetch_search_page(
            url,
            site=site,
            params=params,
            timeout=timeout,
            min_html_length=min_html_length,
        )

    headers = dict(SITE_HEADERS.get(site, BROWSER_HEADERS))
    referer = SITE_REFERERS.get(site)
    if referer and site not in SITE_HEADERS:
        headers["Referer"] = referer

    impersonate = SITE_IMPERSONATE.get(site, "chrome131")

    try:
        response = curl_requests.get(
            url,
            params=params or {},
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            impersonate=impersonate,
        )
        html = response.text
        final_url = str(response.url)
        if response.status_code >= 400:
            return FetchResult(
                html=html,
                url=final_url,
                status_code=response.status_code,
                ok=False,
                error=f"{site or 'site'} returned {response.status_code}",
            )
        if len(html) < min_html_length:
            return FetchResult(
                html=html,
                url=final_url,
                status_code=response.status_code,
                ok=False,
                error=f"{site or 'site'} returned a blocked or empty page",
            )
        return FetchResult(
            html=html,
            url=final_url,
            status_code=response.status_code,
            ok=True,
        )
    except Exception as exc:
        return FetchResult(
            html="",
            url=urljoin(url, ""),
            status_code=0,
            ok=False,
            error=str(exc),
        )

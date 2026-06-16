"""Shared HTTP fetch helper for rental site search pages."""

from dataclasses import dataclass
from typing import Optional

import httpx

from app.services.listing_fetcher import BROWSER_HEADERS

SITE_REFERERS = {
    "apartments.com": "https://www.apartments.com/",
    "rent.com": "https://www.rent.com/",
    "zillow.com": "https://www.zillow.com/",
    "realtor.com": "https://www.realtor.com/",
    "craigslist": "https://www.craigslist.org/",
    "apartmentguide": "https://www.apartmentguide.com/",
}


@dataclass
class FetchResult:
    html: str
    url: str
    status_code: int
    ok: bool
    error: Optional[str] = None


def fetch_search_page(
    url: str,
    site: str = "",
    params: Optional[dict] = None,
    timeout: float = 20.0,
    min_html_length: int = 2000,
) -> FetchResult:
    """Fetch a search results page with site-appropriate headers."""
    if site in ("zillow.com",):
        from app.services.browser_fetch import fetch_with_browser

        return fetch_with_browser(
            url,
            site=site,
            params=params,
            timeout=timeout,
            min_html_length=min_html_length,
        )

    headers = dict(BROWSER_HEADERS)
    referer = SITE_REFERERS.get(site)
    if referer:
        headers["Referer"] = referer

    try:
        with httpx.Client(
            headers=headers, timeout=timeout, follow_redirects=True
        ) as client:
            response = client.get(url, params=params or {})
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
            url=url,
            status_code=0,
            ok=False,
            error=str(exc),
        )

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("marketmind.retrieve")

MAX_RESPONSE_BYTES = 1_000_000
MAX_TEXT_CHARS = 20_000
REQUEST_TIMEOUT = (10, 25)
MAX_REDIRECTS = 3


class RetrieveArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_public_url(cls, value: HttpUrl) -> HttpUrl:
        parsed = urlparse(str(value))

        if parsed.scheme != "https":
            raise ValueError("Only HTTPS URLs are allowed.")

        if parsed.username or parsed.password:
            raise ValueError("URLs containing credentials are not allowed.")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("URL must contain a hostname.")

        if hostname.lower() in {"localhost", "localhost.localdomain"}:
            raise ValueError("Local addresses are not allowed.")

        # Reject literal IPs unless they are globally routable.
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            ip = None

        if ip is not None and not ip.is_global:
            raise ValueError("Non-public IP addresses are not allowed.")

        # Reject hostnames that resolve to private, loopback, link-local,
        # multicast, reserved, or otherwise non-global addresses.
        try:
            addresses = socket.getaddrinfo(
                hostname, 443, type=socket.SOCK_STREAM
            )
        except socket.gaierror as error:
            raise ValueError("Hostname could not be resolved.") from error

        if not addresses:
            raise ValueError("Hostname did not resolve to an address.")

        for address in addresses:
            resolved_ip = ipaddress.ip_address(address[4][0])
            if not resolved_ip.is_global:
                raise ValueError(
                    "URL resolves to a non-public network address."
                )

        return value


def _validate_redirect_target(url: str) -> str:
    """Validate a redirect destination before making a request to it."""
    validated = RetrieveArgs(url=url)
    return str(validated.url)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=1,
        status=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def retrieve_document(url: str) -> dict:
    args = RetrieveArgs(url=url)
    current_url = str(args.url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; MarketMindAI/1.0; "
            "+https://example.org/research-agent)"
        ),
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
    }

    try:
        # Validate each redirect destination before requesting it. This avoids
        # blindly following redirects to localhost/private network addresses.
        with _session() as session:
            response = None
            for redirect_count in range(MAX_REDIRECTS + 1):
                response = session.get(
                    current_url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    stream=True,
                    allow_redirects=False,
                )

                if response.status_code not in {301, 302, 303, 307, 308}:
                    break

                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise RuntimeError(
                        "The website returned a redirect without a destination."
                    )
                if redirect_count >= MAX_REDIRECTS:
                    raise RuntimeError(
                        f"The website exceeded the {MAX_REDIRECTS}-redirect limit."
                    )

                next_url = requests.compat.urljoin(current_url, location)
                current_url = _validate_redirect_target(next_url)

            if response is None:
                raise RuntimeError("No response was received from the website.")

            with response:
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")
                if not any(
                    kind in content_type.lower()
                    for kind in ("text/html", "application/xhtml+xml")
                ):
                    raise ValueError(
                        "The URL did not return an HTML document "
                        f"(content type: {content_type or 'missing'})."
                    )

                declared_size = response.headers.get("Content-Length")
                if declared_size:
                    try:
                        if int(declared_size) > MAX_RESPONSE_BYTES:
                            raise ValueError(
                                "The webpage exceeds the 1 MB size limit."
                            )
                    except ValueError as error:
                        if "size limit" in str(error):
                            raise
                        # Ignore malformed Content-Length; enforce the streamed limit.

                chunks = []
                total_bytes = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    total_bytes += len(chunk)
                    if total_bytes > MAX_RESPONSE_BYTES:
                        raise ValueError(
                            "The webpage exceeds the 1 MB size limit."
                        )
                    chunks.append(chunk)

                html = b"".join(chunks)

        soup = BeautifulSoup(html, "html.parser")

        for element in soup(
            ["script", "style", "nav", "footer", "header", "noscript"]
        ):
            element.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text = " ".join(soup.get_text(" ", strip=True).split())
        truncated = len(text) > MAX_TEXT_CHARS
        text = text[:MAX_TEXT_CHARS]

        if not text:
            raise ValueError("No readable text was found on the webpage.")

        result = {
            "url": current_url,
            "title": title,
            "text": text,
            "character_count": len(text),
            "truncated": truncated,
            "source_kind": "retrieved_document",
        }

        logger.info(
            "Document retrieved; host=%s characters=%s truncated=%s",
            urlparse(current_url).hostname,
            len(text),
            truncated,
        )
        return result

    except (requests.Timeout, requests.ConnectionError) as error:
        logger.warning(
            "Document retrieval network failure; host=%s error_type=%s",
            urlparse(current_url).hostname,
            type(error).__name__,
        )
        raise RuntimeError(
            "The website could not be reached before the timeout. "
            "Retry later or use another credible source."
        ) from error
    except requests.HTTPError as error:
        status = (
            error.response.status_code
            if error.response is not None
            else "unknown"
        )
        logger.warning(
            "Document retrieval HTTP failure; host=%s status=%s",
            urlparse(current_url).hostname,
            status,
        )
        raise RuntimeError(
            f"The website returned HTTP status {status}. "
            "Try another credible source or retry later."
        ) from error
    except requests.RequestException as error:
        logger.warning(
            "Document retrieval request failure; host=%s error_type=%s",
            urlparse(current_url).hostname,
            type(error).__name__,
        )
        raise RuntimeError(
            "The request failed while retrieving this webpage. "
            "Try another credible source or retry later."
        ) from error

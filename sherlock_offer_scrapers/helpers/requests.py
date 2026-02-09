from typing import List, Optional
import os
import base64
import random

import requests
import structlog


logger = structlog.get_logger()

_proxy_creds = {
    "username": os.environ.get("PROXY_USERNAME", ""),
    "password": os.environ.get("PROXY_PASSWORD", ""),
}

# Proxy IPs loaded from environment (comma-separated) or empty list
_proxy_ips = [ip.strip() for ip in os.environ.get("PROXY_IPS", "").split(",") if ip.strip()]

def _get_random_proxy_config():
    """Get a random proxy configuration using one of the available IPs"""
    random_ip = random.choice(_proxy_ips)
    return {
        "http": f'http://{_proxy_creds["username"]}:{_proxy_creds["password"]}@{random_ip}:60000',
        "https": f'http://{_proxy_creds["username"]}:{_proxy_creds["password"]}@{random_ip}:60000',
    }

# Replace the country-specific proxy config with a function that returns a random proxy
_proxy_config = {
    "DE": _get_random_proxy_config,
    "UK": _get_random_proxy_config,
    "SE": _get_random_proxy_config,
}

_proxy_header = {
    "Proxy-Authorization": base64.b64encode(
        f'Basic {_proxy_creds["username"]}:{_proxy_creds["password"]}'.encode("ascii")
    )
}

_default_user_agents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
]


class SessionWithLogger(requests.Session):
    def get(self, url, **kwargs) -> requests.Response:  # type: ignore
        response = super().get(url, **kwargs)
        _log_request(url, response, **kwargs)
        return response

    def post(self, url, **kwargs) -> requests.Response:  # type: ignore
        response = super().post(url, **kwargs)
        _log_request(url, response, **kwargs)
        return response


def _log_request(url, response: requests.Response, **kwargs):
    logger.info(
        "make-request",
        request_type=response.request.method,
        request_url=url,
        request_headers=response.request.headers,
        request_proxy=response.request.headers.get("Proxy-Authorization"),
        response_status_code=response.status_code,
        response_body_size_bytes=len(response.content),
        country=kwargs.get("offer_source_country"),
    )


def get(
    url: str,
    headers: dict = None,
    cookies: dict = None,
    proxy_country: str = None,
    offer_source_country: str = None,
    timeout: Optional[int] = 600,
) -> requests.Response:
    """Make a GET request with some default headers and optional proxy.

    Supported proxy_country: ["SE", "DE", "UK"]
    """
    if headers is None:
        headers = _get_default_headers()

    # Apply proxy if needed
    proxy_config = None
    if proxy_country is not None:
        # Call the function to get a random proxy configuration
        proxy_config = _proxy_config[proxy_country]()
        headers.update(_proxy_header)

    response = requests.get(
        url, headers=headers, proxies=proxy_config, cookies=cookies, timeout=timeout
    )

    # TODO: Try to use the _log_request() function
    logger.info(
        "make-request",
        request_url=url,
        request_headers=headers,
        request_proxy=proxy_config,
        response_status_code=response.status_code,
        response_body_size_bytes=len(response.content),
        country=offer_source_country,
    )

    if os.getenv("PANPRICES_ENVIRONMENT") == "local":
        with open("test.html", "wb") as f:
            f.write(response.content)

    return response


def _get_default_headers():
    user_agent = random.choice(_default_user_agents)
    return {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate, br",
    }

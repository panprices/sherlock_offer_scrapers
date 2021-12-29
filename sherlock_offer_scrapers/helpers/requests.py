from typing import List
import os
import base64
import random

import requests
import structlog


logger = structlog.get_logger()

_proxy_creds = {"username": "panprices", "password": "BB4NC4WQmx"}
_proxy_config = {
    "DE": {
        "http": f'http://{_proxy_creds["username"]}:{_proxy_creds["password"]}@panprices.oxylabs.io:60003',
        "https": f'http://{_proxy_creds["username"]}:{_proxy_creds["password"]}@panprices.oxylabs.io:60003',
    },
    "UK": {
        "http": f'http://{_proxy_creds["username"]}:{_proxy_creds["password"]}@panprices.oxylabs.io:60001',
        "https": f'http://{_proxy_creds["username"]}:{_proxy_creds["password"]}@panprices.oxylabs.io:60001',
    },
    "SE": {
        "http": f'http://{_proxy_creds["username"]}:{_proxy_creds["password"]}@panprices.oxylabs.io:60002',
        "https": f'http://{_proxy_creds["username"]}:{_proxy_creds["password"]}@panprices.oxylabs.io:60002',
    },
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


def get(
    url: str,
    headers: dict = None,
    cookies: dict = None,
    proxy_country: str = None,
) -> requests.Response:
    """Make a GET request with some default headers and optional proxy.

    Supported proxy_country: ["SE", "DE", "UK"]
    """
    if headers is None:
        headers = _get_default_headers()

    # Apply proxy if needed
    proxy_config = None
    if proxy_country is not None:
        proxy_config = _proxy_config[proxy_country]
        headers.update(_proxy_header)

    response = requests.get(url, headers=headers, proxies=proxy_config, cookies=cookies)

    logger.info(
        "make-request",
        request_url=url,
        request_headers=headers,
        request_proxy=proxy_config,
        response_status_code=response.status_code,
        response_body_size_bytes=len(response.content),
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

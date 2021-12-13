import logging
from typing import List
import requests
import base64
import random


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


def get(url: str, headers: dict = None, proxy_country: str = None) -> requests.Response:
    """Make a GET request with some default headers and optional proxy.

    Supported proxy_country: ["SE", "DE", "GB"]
    """
    all_headers = _get_default_headers()
    if headers is not None:
        all_headers.update(headers)

    # Apply proxy if needed
    proxy_config = None
    if proxy_country is not None:
        proxy_config = _proxy_config[proxy_country]
        all_headers.update(_proxy_header)

    response = requests.get(url, headers=all_headers, proxies=proxy_config)

    if response.status_code != 200:
        logging.error(f"Status code: {response.status_code} when requesting to {url}")

    return response


def _get_default_headers():
    user_agent = random.choice(_default_user_agents)
    return {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate, br",
    }

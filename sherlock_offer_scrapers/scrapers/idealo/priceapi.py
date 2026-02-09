import os
from typing import List, Tuple

import requests

BASE_URL = "https://api.priceapi.com/v2/jobs"
PRICEAPI_API_KEY = os.environ.get("PRICEAPI_API_KEY")


def create_job(
    country: str, source: str, topic: str, key: str, values: List[str]
) -> str:
    """Create a new job on PriceAPI."""
    url = BASE_URL
    data = {
        "token": PRICEAPI_API_KEY,
        "country": country,
        "source": source,
        "topic": topic,
        "key": key,
        "values": "\n".join(values),
        "max_pages": 1,
    }
    response = requests.post(url, data=data)

    if response.status_code != 200:
        _raise_exception("Error when creating a new job on PriceAPI", response)

    content = response.json()
    return content["job_id"]


def job_status(job_id: str) -> str:
    """Check the status of a PriceAPI job.

    Possible job status are: `['new', 'working', 'finishing', 'finished',
    'cancelled']`. For more information please visit https://readme.priceapi.com/reference#v2-get-job-status.
    """
    url = f"{BASE_URL}/{job_id}?token={PRICEAPI_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        if response.status_code == 500:
            _raise_exception(f"Error from PriceAPI server", response)
        else:
            _raise_exception(f"Error when checking for job {job_id}", response)

    content = response.json()
    return content["status"]


def job_completed(job_id: str) -> Tuple[bool, str]:
    status = job_status(job_id)
    completed = status in ["finished", "cancelled"]
    return (completed, status)


def get_result(job_id: str) -> dict:
    """Get the result of a job after it has finished."""
    url = f"{BASE_URL}/{job_id}/download?token={PRICEAPI_API_KEY}"
    response = requests.get(url)

    if response.status_code != 200:
        if response.status_code == 500:
            _raise_exception(f"Error from PriceAPI server", response)
        else:
            _raise_exception(f"Error when downloading result of job {job_id}", response)

    return response.json()


def _raise_exception(message: str, response: requests.Response) -> None:
    raise Exception(
        f"{message}\n"
        + f"Status code: {response.status_code}\n"
        + f"Response: {response.json()}"
    )

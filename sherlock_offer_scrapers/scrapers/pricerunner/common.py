import random
import time
import requests

from . import user_agents


BASE_URL = {
    "SE": "https://www.pricerunner.se",
    "DK": "https://www.pricerunner.dk",
}


def create_session(country="SE"):
    headers = _get_headers(country)
    session = requests.Session()
    session.headers.update(headers)
    return session


def _get_headers(country):
    return {
        "Content-Type": "application/json;charset=utf-8",
        # Random generated user agents
        "User-Agent": user_agents.choose_random(),
        "Authority": get_header_authority(country),
    }


def get_header_authority(country: str) -> str:
    return f"www.pricerunner.{country.lower()}"


def _make_request(url, session):
    response = session.get(url)

    # Check if we wasn't able to acces the content because Pricerunner blocker our IP
    if response.status_code == 403:
        # click the "I am not the robot button"
        session.post("https://www.pricerunner.se/public/access/v1", data={})
        # in the button implementation, they wait for 0.25 second, so do we
        time.sleep(0.25)
        # fetch the data api again

        response = session.get(url)
        # check 403 again
        if response.status_code == 403:
            print("They still block us")
            raise Exception(
                "Status code was 403 Forbidden. Pricerunner has probably blocked our IP adress."
            )
        else:
            print("I am not a robot")
    # Check if we wasn't able to acces the content because Pricerunner blocker our IP
    if response.status_code == 410:
        print("<Response 410>: the target resource is no longer available. Url:", url)

    return response


def pause_execution_random(min_sec=1, max_sec=300):
    rand_duration = random.randint(min_sec, max_sec)
    print("Pause for " + str(rand_duration) + "s")
    time.sleep(rand_duration)

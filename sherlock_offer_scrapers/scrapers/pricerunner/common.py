import random
import time
import requests


BASE_URL = {
    "SE": "https://www.pricerunner.se",
    "DK": "https://www.pricerunner.dk",
}


def _make_request(url, session, retries=0):
    # max_retries is not defined",
    max_retries = 1
    try:
        response = session.get(url)
    except requests.exceptions.Timeout:
        print("Got a timeout on url " + url)
        if retries >= max_retries:
            raise e
        retries += 1
        return _make_request(url, session, retries)
    except requests.exceptions.RequestException as e:
        print(
            "There was an error with getting product offers for "
            + url
            + " on Pricerunner: "
            + str(e)
        )
        raise e
    # Check if we wasn't able to acces the content because Pricerunner blocker our IP
    if response.status_code == 403:
        # click the "I am not the robot button"
        session.post("https://www.pricerunner.se/public/access/v1", data={})
        # in the button implementation, they wait for 0.25 second, so do we
        time.sleep(0.25)
        # fetch the data api again
        try:
            response = session.get(url)
        except requests.exceptions.Timeout:
            print("Got a timeout on url " + url)
            if retries >= max_retries:
                raise e
            retries += 1
            return _make_request(url, session, retries)
        except requests.exceptions.RequestException as e:
            print(
                "There was an error with getting product offers for "
                + url
                + " on Pricerunner: "
                + str(e)
            )
            raise e
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
        print("<Response 410>: the target resource is no longer available")

    return response


def pause_execution_random(min_sec=1, max_sec=300):
    rand_duration = random.randint(min_sec, max_sec)
    print("Pause for " + str(rand_duration) + "s")
    time.sleep(rand_duration)

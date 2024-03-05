import requests
import json


def get_oneday():
    url = "https://aa.usno.navy.mil/api/rstt/oneday"
    params = {"date": "2024-03-05", "coords": "38.889444,-77.035278", "tz": -5}
    request = requests.get(url, params=params)

    if not request.status_code == 200:
        raise RuntimeError()

    return request.content


def parse_oneday(content):
    data = json.loads(content)

    # confirm that the date is what we would expect
    # content['properties']['data']['year'], 'month', 'day'

    phenomena = data["properties"]["data"]["moondata"]
    times = {x["phen"]: x["time"] for x in phenomena}

    return times

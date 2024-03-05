import requests
import json
import datetime


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

    # also closest phase, current phase

    return times


def get_celnav():
    url = "https://aa.usno.navy.mil/api/celnav"
    params = {"date": "2024-03-05", "time": "08:30", "coords": "38.89,-77.03"}
    request = requests.get(url, params=params)

    if not request.status_code == 200:
        raise RuntimeError()

    return request.content


def parse_celnav(content):
    data = json.loads(content)

    # check the day, month, etc.
    # data['properties']['day']

    moon = [
        x for x in data["properties"]["data"] if "object" in x and x["object"] == "Moon"
    ][0]

    # results are in UTC
    assert data["properties"]["tz"] == 0

    return {
        "azimuth": moon["almanac_data"]["zn"],
        "altitude": moon["almanac_data"]["hc"],
        "illumination": data["properties"]["moon_illum"],
        "phase": data["properties"]["moon_phase"],
    }


def get_phases():
    url = "https://aa.usno.navy.mil/api/moon/phases/year"
    params = {"year": "2024"}
    request = requests.get(url, params=params)

    if not request.status_code == 200:
        raise RuntimeError()

    return request.content


def parse_phases(content):
    data = json.loads(content)
    phases = data["phasedata"]
    assert len(phases) == data["numphases"]
    # check year
    # assert phases[0]['year'] ==
    return [parse_phase(x) for x in phases]


def parse_phase(x):
    time_parts = x["time"].split(":")
    assert len(time_parts) == 2
    hour, minute = time_parts
    return {
        "phase": x["phase"],
        "date": datetime.datetime(
            x["year"], x["month"], x["day"], int(hour), int(minute)
        ),
    }

import requests
import json
import datetime
import polars as pl
import pymongo
import multiprocessing

"""Lat/long for Washington, DC"""
coords_dc = "38.889444,-77.035278"


def now() -> datetime.datetime:
    """Current time in UTC"""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=0)))


def ymd(x: datetime.datetime) -> str:
    """Format datetime as YYYY-MM-DD"""
    return x.strftime("%Y-%m-%d")


def hm(x: datetime.datetime) -> str:
    """Format datetime as HH:MM"""
    return x.strftime("%H:%M")


def get_usno(url, params):
    request = requests.get(url, params=params)
    request.raise_for_status()

    return json.loads(request.content)


def get_oneday(date=ymd(now()), coords=coords_dc, tz=-5):
    url = "https://aa.usno.navy.mil/api/rstt/oneday"
    params = {"date": date, "coords": coords, "tz": tz}
    return get_usno(url, params)


def parse_oneday(data):
    # confirm that the date is what we would expect
    # content['properties']['data']['year'], 'month', 'day'
    phenomena = data["properties"]["data"]["moondata"]
    assert type(phenomena) == list
    assert type(phenomena[0]) == dict
    times = {x["phen"]: x["time"] for x in phenomena}

    # also closest phase, current phase
    phase = data["properties"]["data"]["curphase"]

    fracillum = data["properties"]["data"]["fracillum"]
    assert fracillum[-1] == "%"
    illumination = int(fracillum[0:-1])

    return times | {"phase": phase, "illumination": illumination}


def get_celnav(
    date=ymd(now()),
    time=hm(now()),
    coords=coords_dc,
):
    url = "https://aa.usno.navy.mil/api/celnav"
    params = {"date": date, "time": time, "coords": coords}
    return get_usno(url, params)


def parse_celnav(data):
    # check the day, month, etc.
    # data['properties']['day']

    objects = data["properties"]["data"]
    object_names = [x["object"] for x in objects]

    if "Moon" not in object_names:
        return None

    moon = [x for x in objects if x["object"] == "Moon"][0]

    # results are in UTC
    assert data["properties"]["tz"] == 0

    return {
        "azimuth": moon["almanac_data"]["zn"],
        "altitude": moon["almanac_data"]["hc"],
        "illumination": data["properties"]["moon_illum"],
        "phase": data["properties"]["moon_phase"],
    }


def get_phases(year=now().year):
    url = "https://aa.usno.navy.mil/api/moon/phases/year"
    params = {"year": str(year)}
    return get_usno(url, params)


def parse_phases(data):
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


def cache_oneday_year(year=now().year):
    """
    Cache one year's worth of oneday data
    """
    client = pymongo.MongoClient()
    db = client.moonbox_db
    collection = db["oneday"]

    dates = (
        pl.select(pl.date_range(pl.date(year, 1, 1), pl.date(year, 12, 31)))
        .to_series()
        .to_list()
    )

    for date in dates:
        if collection.find_one({"date": date.isoformat()}) is None:
            print(date)
            result = get_oneday(date.isoformat())
            record = {"date": date.isoformat(), "result": result}
            collection.insert_one(record)


def get_oneday_year(year=now().year):
    """
    Get one year's wroth of oneday data, from the cache
    """
    client = pymongo.MongoClient()
    db = client.moonbox_db
    collection = db["oneday"]

    dates = (
        pl.select(pl.date_range(pl.date(year, 1, 1), pl.date(year, 12, 31)))
        .to_series()
        .to_list()
    )

    results = [collection.find_one({"date": date.isoformat()}) for date in dates]
    data = [
        {"date": date} | parse_oneday(x["result"]) for date, x in zip(dates, results)
    ]

    return data

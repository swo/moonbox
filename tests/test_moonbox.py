import pytest
import moonbox
import datetime
import json


@pytest.mark.slow
def test_get_oneday():
    data = moonbox.get_oneday()
    moonbox.parse_oneday(data)


def test_parse_oneday():
    content = {
        "apiversion": "4.0.1",
        "geometry": {"coordinates": [-77.035278, 38.889444], "type": "Point"},
        "properties": {
            "data": {
                "closestphase": {
                    "day": 3,
                    "month": 3,
                    "phase": "Last Quarter",
                    "time": "10:23",
                    "year": 2024,
                },
                "curphase": "Waning Crescent",
                "day": 5,
                "day_of_week": "Tuesday",
                "fracillum": "29%",
                "isdst": False,
                "label": None,
                "month": 3,
                "moondata": [
                    {"phen": "Rise", "time": "03:27"},
                    {"phen": "Upper Transit", "time": "07:53"},
                    {"phen": "Set", "time": "12:21"},
                ],
                "sundata": [
                    {"phen": "Begin Civil Twilight", "time": "06:07"},
                    {"phen": "Rise", "time": "06:34"},
                    {"phen": "Upper Transit", "time": "12:19"},
                    {"phen": "Set", "time": "18:06"},
                    {"phen": "End Civil Twilight", "time": "18:32"},
                ],
                "tz": -5.0,
                "year": 2024,
            }
        },
        "type": "Feature",
    }
    data = moonbox.parse_oneday(content)
    assert data == {
        "Rise": "03:27",
        "Upper Transit": "07:53",
        "Set": "12:21",
        "illumination": 29,
        "phase": "Waning Crescent",
    }


@pytest.mark.slow
def test_get_celnav():
    data = moonbox.get_celnav()
    moonbox.parse_celnav(data)


@pytest.mark.slow()
def test_get_celnav_no_moon():
    """When the moon is not up, no celnav data"""
    data = moonbox.get_celnav(date="2024-03-07", time="3:40")
    assert moonbox.parse_celnav(data) is None


def test_parse_celnav():
    with open("tests/data/celnav.json") as f:
        data = json.load(f)

    data = moonbox.parse_celnav(data)
    assert data == {
        "altitude": 0.570058,
        "azimuth": 128.290209,
        "illumination": 32,
        "phase": "Waning Crescent",
    }


@pytest.mark.slow
def test_get_phases():
    data = moonbox.get_phases()
    moonbox.parse_phases(data)


def test_parse_phases():
    with open("tests/data/phases.json") as f:
        data = json.load(f)

    data = moonbox.parse_phases(data)
    assert data[3] == {
        "date": datetime.datetime(2024, 1, 25, 17, 54),
        "phase": "Full Moon",
    }

import requests
import pytest
import moonbox
import datetime
import json
import sqlite3


class MockRequest:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self.content


class MockSession:
    def __init__(self, mock_data_path="tests/data/mock.db", verbose=True):
        self.mock_data_path = mock_data_path
        self.con = sqlite3.connect(self.mock_data_path)
        self.cur = self.con.cursor()
        self.db_name = "mock"

        self.initialize_db()

        self.verbose = verbose

    def initialize_db(self):
        results = self.cur.execute("SELECT name FROM sqlite_master").fetchall()
        if len(results) == 0:
            self.cur.execute(f"CREATE TABLE {self.db_name} (key TEXT, datum TEXT)")
        elif len(results) == 1 and results[0][0] == self.db_name:
            pass
        else:
            raise RuntimeError

    def get(self, url, params):
        key = self.cache_key(url, params)

        results = self.cur.execute(
            "SELECT datum FROM mock WHERE key=?", (key,)
        ).fetchall()
        if len(results) == 0:
            # get the data from the server
            if self.verbose:
                print(f"Requesting '{url}' with {params}")

            request = requests.get(url, params=params)
            request.raise_for_status()
            datum = request.json()

            # insert into the database
            self.cur.execute("INSERT INTO mock VALUES (?, ?)", (key, json.dumps(datum)))
            self.con.commit()

            return MockRequest(datum)
        elif len(results) == 1:
            datum = json.loads(results[0][0])
            return MockRequest(datum)
        else:
            raise RuntimeError

    @staticmethod
    def cache_key(url: str, params: dict):
        return str((url, tuple(sorted(params.items()))))


@pytest.fixture
def mock_session():
    return MockSession()


@pytest.mark.slow
def test_get_oneday(mock_session):
    data = moonbox.get_oneday(date="2024-11-30", session=mock_session)
    current = moonbox.parse_oneday(data)
    assert current == {
        "Rise": "06:41",
        "Set": "16:04",
        "Upper Transit": "11:25",
        "illumination": 0,
        "phase": "New Moon",
    }


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
def test_get_celnav(mock_session):
    data = moonbox.get_celnav(date="2024-11-30", time="11:30", session=mock_session)
    current = moonbox.parse_celnav(data)
    assert current == {
        "altitude": -1.713053,
        "azimuth": 120.129609,
        "illumination": 1,
        "phase": "Waning Crescent",
    }


@pytest.mark.slow()
def test_get_celnav_no_moon(mock_session):
    """When the moon is not up, no celnav data"""
    data = moonbox.get_celnav(date="2024-03-07", time="3:40", session=mock_session)
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
def test_get_phases_raw(mock_session):
    data = moonbox._get_phases_raw(year=2025, session=mock_session)
    assert set(data.keys()).issuperset({"phasedata", "year"})
    assert data["year"] == 2025
    assert data["phasedata"][0] == {
        "day": 6,
        "month": 1,
        "phase": "First Quarter",
        "time": "23:56",
        "year": 2025,
    }


def test_parse_phases():
    with open("tests/data/phases.json") as f:
        data = json.load(f)

    data = moonbox._parse_phases(data)
    assert data[3] == {
        "datetime": datetime.datetime(2024, 1, 25, 17, 54),
        "phase": "Full Moon",
    }


def test_date_range():
    start = datetime.date(2024, 1, 1)
    end = datetime.date(2024, 1, 10)
    dates = moonbox.date_range(start, end)
    assert len(dates) == 10
    assert dates[0] == start
    assert dates[-1] == end
    assert isinstance(dates[0], datetime.date)
    assert dates[0].isoformat() == "2024-01-01"


@pytest.mark.slow
def test_calendar(mock_session):
    c = moonbox.calendar(2024, session=mock_session)

    assert c[0] == {
        "Rise": "22:28",
        "Set": "11:00",
        "Upper Transit": "04:19",
        "date": datetime.date(2024, 1, 1),
        "illumination": 72,
        "lunar_day": 20,
        "lunar_month": 0,
        "phase": "Waning Gibbous",
    }

    # should cover the whole year
    assert c[-1]["date"] == datetime.date(2024, 12, 31)
    assert len(c) == 366

    # all lunar months (except the first and last, which are
    # cross-year partial months) should have 29 or 30 days
    lunar_months = set([x["lunar_month"] for x in c])
    good_months = [x for x in lunar_months if x not in [0, max(lunar_months)]]

    for month in good_months:
        assert len([x for x in c if x["lunar_month"] == month]) in [29, 30]

import requests
import datetime
import matplotlib.axes
import matplotlib.patches as mpatches
import re

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


def get_usno(url, params, session: requests.Session):
    request = session.get(url, params=params)
    request.raise_for_status()
    return request.json()


def get_oneday(date: str, session: requests.Session, coords=coords_dc, tz=-5):
    url = "https://aa.usno.navy.mil/api/rstt/oneday"
    # date should be in ISO format
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", date)
    params = {"date": date, "coords": coords, "tz": tz}
    return get_usno(url, params, session)


def parse_oneday(data):
    # confirm that the date is what we would expect
    # content['properties']['data']['year'], 'month', 'day'
    phenomena = data["properties"]["data"]["moondata"]
    assert isinstance(phenomena, list)
    assert isinstance(phenomena[0], dict)
    times = {x["phen"]: x["time"] for x in phenomena}

    # also closest phase, current phase
    phase = data["properties"]["data"]["curphase"]

    fracillum = data["properties"]["data"]["fracillum"]
    assert fracillum[-1] == "%"
    illumination = int(fracillum[0:-1])

    return times | {"phase": phase, "illumination": illumination}


def get_celnav(date: str, time: str, session: requests.Session, coords=coords_dc):
    url = "https://aa.usno.navy.mil/api/celnav"
    params = {"date": date, "time": time, "coords": coords}
    return get_usno(url, params, session)


def parse_celnav(data):
    # check the day, month, etc.

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


def get_phases(year: int = now().year, session: requests.Session = None) -> list:
    return _parse_phases(_get_phases_raw(year, session))


def _get_phases_raw(year: int, session: requests.Session) -> dict:
    url = "https://aa.usno.navy.mil/api/moon/phases/year"
    params = {"year": str(year)}
    return get_usno(url, params, session)


def _parse_phases(data: dict) -> list:
    phases = data["phasedata"]
    assert len(phases) == data["numphases"]
    return [_parse_phase(x) for x in phases]


def _parse_phase(x: dict) -> dict:
    time_parts = x["time"].split(":")
    assert len(time_parts) == 2
    hour, minute = time_parts
    return {
        "phase": x["phase"],
        "datetime": datetime.datetime(
            x["year"], x["month"], x["day"], int(hour), int(minute)
        ),
    }


def draw_moon(
    axes: matplotlib.axes.Axes,
    x: float,
    y: float,
    radius: float,
    f: float,
    direction: str,
    light: str = "white",
    dark: str = "black",
    eps: float = 1.25e-2,
) -> None:
    """Draw a moon in arbitrary phase

    Note that, mathematically:
    - total area: pi*R^2
    - foreground: 0.5*pi*R^2 + 0.5*pi*R*r = 0.5*pi*R^2*(1+r/R)
    - f = 0.5*(1+r/R)
    - R*(2*f-1)=r

    Args:
        axes (matplotlib.Axes): plot axes
        x (float): x-coordinate of center
        y (float): y-coordinate of center
        radius (float): radius of moon
        f (float): fractional illumination
        direction (str): one of "waxing", "first", "waning", or "third"
        light (str): color of light pars of moon
        dark (str): color of dark parts of moon
        eps (float): fractional size reduction of "bottom" circle
    """

    if f == 0.0:
        back_color = dark
        half_side = None
        half_color = None
        ellipse_color = None
    elif direction == "waxing" and 0.0 < f < 0.5:
        back_color = light
        half_side = "left"
        half_color = dark
        ellipse_color = dark
    elif direction in ["waxing", "first"] and f == 0.5:
        back_color = light
        half_side = "left"
        half_color = dark
        ellipse_color = None
    elif direction == "waxing" and 0.5 < f < 1.0:
        back_color = dark
        half_side = "right"
        half_color = light
        ellipse_color = light
    elif f == 1.0:
        back_color = light
        half_side = None
        half_color = None
        ellipse_color = None
    elif direction == "waning" and 0.5 < f < 1.0:
        back_color = dark
        half_side = "left"
        half_color = light
        ellipse_color = light
    elif direction in ["waning", "third"] and f == 0.5:
        back_color = dark
        half_side = "left"
        half_color = light
        ellipse_color = None
    elif direction == "waning" and 0.0 < f < 0.5:
        back_color = light
        half_side = "right"
        half_color = dark
        ellipse_color = dark
    else:
        raise RuntimeError(f"bad values: f={f} direction={direction}")

    center = (x, y)
    back = mpatches.Circle(center, radius * (1.0 - eps), color=back_color)
    axes.add_artist(back)

    if half_side == "left":
        half = mpatches.Wedge(center, radius, 90, 270, color=half_color)
        axes.add_artist(half)
    elif half_side == "right":
        half = mpatches.Wedge(center, radius, 270, 90, color=half_color)
        axes.add_artist(half)
    elif half_side is None:
        pass
    else:
        raise ValueError(f"bad half: {half}")

    if ellipse_color is not None:
        ellipse = mpatches.Ellipse(
            center, 2 * radius * (2 * f - 1), 2 * radius, color=ellipse_color
        )
        axes.add_artist(ellipse)

    return None


def calendar(year: int, session: requests.Session):
    # get all of this year's new moons, plus the last of last year
    # and the first of next year
    new_moons = (
        [_get_new_moons(year - 1, session)[-1]]
        + _get_new_moons(year, session)
        + [_get_new_moons(year + 1, session)[0]]
    )

    # get all the dates from the first to the last new moon
    all_dates = date_range(
        new_moons[0]["datetime"].date(), new_moons[-1]["datetime"].date()
    )

    # get the celnav data for each date
    data = {
        date: parse_oneday(get_oneday(date.isoformat(), session=session))
        for date in all_dates
    }

    # reorganize data into a list, with information about lunar month and day
    lunar_month = None
    lunar_day = None
    calendar = []
    for date in all_dates:
        datum = data[date]
        if lunar_month is None:
            lunar_month = 0
            lunar_day = 0
        elif datum["phase"] == "New Moon":
            lunar_month += 1
            lunar_day = 0
        else:
            lunar_day += 1

        if date.year == year:
            new_datum = datum | {
                "date": date,
                "lunar_month": lunar_month,
                "lunar_day": lunar_day,
            }
            calendar.append(new_datum)

    return calendar


def _get_new_moons(year: int, session: requests.Session):
    return [x for x in get_phases(year, session) if x["phase"] == "New Moon"]


def date_range(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    return [start + datetime.timedelta(days=x) for x in range((end - start).days + 1)]

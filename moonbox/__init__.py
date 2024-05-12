import requests
import json
import datetime
import matplotlib.patches as mpatches

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


def get_usno(url, params, session=None):
    if session is None:
        request = requests.get(url, params=params)
    else:
        request = session.get(url, params=params)

    request.raise_for_status()

    return json.loads(request.content)


def get_oneday(date=ymd(now()), coords=coords_dc, tz=-5, session=None):
    url = "https://aa.usno.navy.mil/api/rstt/oneday"
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


def get_celnav(date=ymd(now()), time=hm(now()), coords=coords_dc, session=None):
    url = "https://aa.usno.navy.mil/api/celnav"
    params = {"date": date, "time": time, "coords": coords}
    return get_usno(url, params, session)


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


def get_phases(year=now().year, session=None):
    url = "https://aa.usno.navy.mil/api/moon/phases/year"
    params = {"year": str(year)}
    return get_usno(url, params, session)


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


def draw_moon(axes, f, direction, light="white", dark="black", eps=1.25e-2):
    """Draw a moon in arbitrary phase

    Note that, mathematically:
    - total area: pi*R^2
    - foreground: 0.5*pi*R^2 + 0.5*pi*R*r = 0.5*pi*R^2*(1+r/R)
    - f = 0.5*(1+r/R)
    - R*(2*f-1)=r

    Args:
        axes (matplotlib.Axes): plot axes
        f (float): fractional illumination
        direction (str): one of "waxing", "first", "waning", or "third"
        light (str): color of light pars of moon
        dark (str): color of dark parts of moon
        eps (float): fractional size reduction of "bottom" circle
    """
    center = (0, 0)
    radius = 0.9

    axes.set(aspect=1, xlim=(-1.0, 1.0), ylim=(-1.0, 1.0))
    axes.set_axis_off()

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

    back = mpatches.Circle(center, radius * (1.0 - eps), ec="none")
    back.set(color=back_color)
    axes.add_artist(back)

    if half_side == "left":
        half = mpatches.Wedge(center, radius, 90, 270, ec="none")
        half.set(color=half_color)
        axes.add_artist(half)
    elif half_side == "right":
        half = mpatches.Wedge(center, radius, 270, 90, ec="none")
        half.set(color=half_color)
        axes.add_artist(half)
    elif half_side is None:
        pass
    else:
        raise ValueError(f"bad half: {half}")

    if ellipse_color is not None:
        artist = mpatches.Ellipse(center, 2 * radius * (2 * f - 1), 2 * radius)
        artist.set(color=ellipse_color)
        axes.add_artist(artist)

    return None

import requests

def get_oneday():
    url = "https://aa.usno.navy.mil/api/rstt/oneday"
    params = {
        "date": "2024-03-05",
        "coords": "38.889444,-77.035278",
        "tz": -5
    }
    r = requests.get(url, params=params)
    return r
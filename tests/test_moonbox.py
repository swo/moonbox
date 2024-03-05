import moonbox
import json

def test_parse_oneday():
    content = """
        {"apiversion": "4.0.1", "geometry": {"coordinates": [-77.035278, 38.889444],
        "type": "Point"}, "properties": {"data": {"closestphase": {"day": 3,
        "month": 3, "phase": "Last Quarter", "time": "10:23", "year": 2024},
        "curphase": "Waning Crescent", "day": 5, "day_of_week": "Tuesday",
        "fracillum": "29%", "isdst": false, "label": null, "month": 3, "moondata":
        [{"phen": "Rise", "time": "03:27"}, {"phen": "Upper Transit", "time": "07:53"},
        {"phen": "Set", "time": "12:21"}], "sundata": [{"phen": "Begin Civil Twilight",
        "time": "06:07"}, {"phen": "Rise", "time": "06:34"}, {"phen": "Upper Transit",
        "time": "12:19"}, {"phen": "Set", "time": "18:06"}, {"phen":
        "End Civil Twilight", "time": "18:32"}], "tz": -5.0, "year": 2024}}, "type": "Feature"}"""
    json.loads(content)
    data = moonbox.parse_oneday(content)
    assert data == {'Rise': '03:27', 'Upper Transit': '07:53', 'Set': '12:21'}
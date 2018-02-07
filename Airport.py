from LatLon import LatLon


class Airport(object):

    def __init__(self, code, name, city, state, lat, lon, alt):
        self.code = code
        self.name = name
        self.city = city
        self.state = state
        self.centerLatLon = LatLon(lat, lon)
        self.alt = alt
        self.runways = []

    def addRunway(self, runway):
        self.runways.append(runway)

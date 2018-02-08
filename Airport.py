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

    def __str__(self):
        return (
            '<Airport(code={self.code}, name={self.name}, city={self.name}, '
            'state{self.state}, center={self.centerLatLon}, altitude={self.alt})>'.format(self=self)
        )

    def __repr__(self):
        return str(self)

    def addRunway(self, runway):
        self.runways.append(runway)

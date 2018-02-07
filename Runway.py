from LatLon import LatLon


class Runway(object):

    def __init__(self, airportCode, alt, runwayCode, magHdg, trueHdg, lat, lon):
        self.airportCode = airportCode
        self.alt = alt
        self.runwayCode = runwayCode
        self.magHeading = magHdg
        self.trueHeading = trueHdg
        self.centerLatLon = LatLon(lat, lon)

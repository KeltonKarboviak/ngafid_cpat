from LatLon import LatLon


class Runway(object):

    def __init__(self, airportCode, alt, runwayCode, magHdg, trueHdg, lat, lon):
        self.airportCode = airportCode
        self.alt = alt
        self.runwayCode = runwayCode
        self.magHeading = magHdg
        self.trueHeading = trueHdg
        self.centerLatLon = LatLon(lat, lon)

    def __str__(self):
        return (
            '<Runway(airport={self.airportCode}, runway={self.runwayCode}, '
            'center={self.centerLatLon}, altitude={self.alt}, '
            'mag_hdg={self.magHeading}, true_hdg={self.trueHeading})>'.format(self=self)
        )

    def __repr__(self):
        return str(self)

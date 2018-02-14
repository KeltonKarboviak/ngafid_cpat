# -*- coding: utf-8 -*-

from latlon import LatLon


class Runway(object):

    def __init__(
        self,
        airport_code: str,
        alt: float,
        runway_code: str,
        mag_hdg: float,
        true_hdg: float,
        lat: float,
        lon: float
    ):
        self.airportCode = airport_code
        self.alt = alt
        self.runwayCode = runway_code
        self.magHeading = float(mag_hdg)
        self.trueHeading = float(true_hdg)
        self.centerLatLon = LatLon(float(lat), float(lon))

    def __str__(self) -> str:
        return (
            '<Runway(airport={self.airportCode}, runway={self.runwayCode}, '
            'center={self.centerLatLon}, altitude={self.alt}, '
            'mag_hdg={self.magHeading}, true_hdg={self.trueHeading})>'.format(
                self=self)
        )

    def __repr__(self):
        return str(self)

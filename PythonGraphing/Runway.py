class Runway:
    airportCode, runwayCode = '', ''
    alt, magHeading, trueHeading, centerLat, centerLon = 0.0, 0.0, 0.0, 0.0, 0.0

    def __init__(self, airportCode, alt, runwayCode, magHdg, trueHdg, centerLat, centerLon):
        self.airportCode = airportCode
        self.alt = alt
        self.runwayCode = runwayCode
        self.magHeading = magHdg
        self.trueHeading = trueHdg
        self.centerLat = centerLat
        self.centerLon = centerLon
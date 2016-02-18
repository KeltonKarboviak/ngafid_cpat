class Runway:
    airport_code, runway_code = '', ''
    alt, magHeading, trueHeading, centerLat, centerLon = 0.0, 0.0, 0.0, 0.0, 0.0

    def __init__(self, airport_code, alt, runway_code, magHdg, trueHdg, centerLat, centerLon):
        self.airport_code = airport_code
        self.alt = alt
        self.runway_code = runway_code
        self.magHeading = magHdg
        self.trueHeading = trueHdg
        self.centerLat = centerLat
        self.centerLon = centerLon
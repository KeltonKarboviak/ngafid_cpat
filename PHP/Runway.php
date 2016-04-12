<?php

require 'LatLon.php';

class Runway
{
        private $airportCode = "";
        private $runwayCode = "";
        private $alt = 0.0;
        private $magHeading = 0.0;
        private $trueHeading = 0.0;
        private $centerLatLon = NULL;

        function Runway($airportCode, $alt, $runwayCode, $magHeading, $trueHeading, $lat, $lon)
        {
            $this->airportCode = $airportCode;
            $this->alt = $alt;
            $this->runwayCode = $runwayCode;
            $this->magHeading = $magHeading;
            $this->trueHeading = $trueHeading;
            $this->centerLatLon = LatLon($lat, $lon);
        }
}

?>

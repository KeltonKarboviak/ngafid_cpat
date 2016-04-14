<?php

require 'LatLon.php';

class Runway
{
        public $airportCode = "";
        public $runwayCode = "";
        public $alt = 0.0;
        public $magHeading = 0.0;
        public $trueHeading = 0.0;
        public $centerLatLon = NULL;

        function Runway($airportCode, $alt, $runwayCode, $magHeading, $trueHeading, $lat, $lon)
        {
            $this->airportCode = $airportCode;
            $this->alt = $alt;
            $this->runwayCode = $runwayCode;
            $this->magHeading = $magHeading;
            $this->trueHeading = $trueHeading;
            $this->centerLatLon = new LatLon($lat, $lon);
        }
}

?>
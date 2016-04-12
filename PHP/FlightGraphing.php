<?php

#import matplotlib.patches as mpatches
#import matplotlib.pyplot as plt

class FlightGraphing
{
    function FlightGraphing($ch, $folder)
    {
        $this->choices = $ch;
        $this->folder = $folder;
    }

    function graph($flightID, $p, $a)
    {
        $this->makeGraph($flightID, $p, $a);
    }

    function makeGraph($flightID, $p, $a)
    {

    }

}

?>

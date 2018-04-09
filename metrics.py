#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import namedtuple
from typing import Union

import numpy as np


class Range(namedtuple('Range', ['low', 'high'])):
    __slots__ = ()

    def contains_inclusive(self, value: Union[int, float]) -> bool:
        return self.low <= value < self.high

    def contains_exclusive(self, value: Union[int, float]) -> bool:
        return self.low < value < self.high

    def contains_left_inclusive(self, value: Union[int, float]) -> bool:
        return self.low <= value < self.high

    def contains_right_inclusive(self, value: Union[int, float]) -> bool:
        return self.low < value <= self.high


metrics = {
    'ias': {
        'mid': Range(61, 66),
        'low': {
            1: Range(-np.inf, 61),
            2: Range(-np.inf, 61),
        },
        'high': {
            1: Range(66, 71),
            2: Range(71, np.inf),
        }
    },
    'vsi': {
        'mid': Range(-800, -500),
        'low': {
            1: Range(-1000, -800),
            2: Range(-np.inf, -1000),
        },
        'high': {
            1: Range(-500, -250),
            2: Range(-250, np.inf),
        }
    },
    'ctr': {
        'mid': Range(-40, 40),
        'low': {
            1: Range(-50, -40),
            2: Range(-np.inf, -50),
        },
        'high': {
            1: Range(40, 50),
            2: Range(50, np.inf)
        }
    },
    'hdg': {
        'mid': Range(-15, 15),
        'low': {
            1: Range(-20, -15),
            2: Range(-np.inf, -20)
        },
        'high': {
            1: Range(15, 20),
            2: Range(20, np.inf)
        }
    }
}


def get_risk_level(param: str, value: Union[int, float]) -> int:
    if param not in metrics:
        raise ValueError()

    p = metrics[param]
    mid, low, high = p['mid'], p['low'], p['high']

    if low[2].contains_left_inclusive(value) or high[2].contains_right_inclusive(value):
        return 2
    if low[1].contains_left_inclusive(value) or high[1].contains_right_inclusive(value):
        return 1

    # It must be in the safe range so we'll return a Risk Level 0
    return 0

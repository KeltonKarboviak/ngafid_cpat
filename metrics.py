#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import namedtuple

import numpy as np


class Range(namedtuple('Range', ['low', 'high'])):
    __slots__ = ()

    def contains(self, value):
        return self.low <= value <= self.high


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
    }
}


def get_risk_level(param, value):
    if param not in metrics:
        raise ValueError()

    p = metrics[param]
    mid, low, high = p['mid'], p['low'], p['high']

    if low[2].contains(value) or high[2].contains(value):
        return 2
    if low[1].contains(value) or high[1].contains(value):
        return 1
    if mid.contains(value):
        return 0

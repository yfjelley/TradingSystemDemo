#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 30 12:58:15 2018

@author: fw
"""

import json
from pprint import pprint


json_file = '/Users/fw/Trading/projects/xman/configuration/changeling_config.json'
with open(json_file) as f:
    data = json.load(f)

pprint(data)
#With data, you can now also find values like so:

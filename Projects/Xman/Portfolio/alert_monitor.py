import datetime as dt
import os
import sys
import pandas as pd
import numpy as np
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst'))
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/*'))
from cmx_alert.outright_alert import portfolio_alert


if __name__ == '__main__':
    if '/Users/fw' in os.getcwd():
        config_folder = '/Users/fw/Trading/projects/xman/configuration'
    else:
        config_folder = '/home/frankwang_trading/projects/xman/configuration'
    xman_alert = portfolio_alert(config_folder)
    xman_alert.run()
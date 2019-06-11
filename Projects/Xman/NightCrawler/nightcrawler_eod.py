import os
import sys
import pandas as pd
import pathlib
cmx_rootpath = pathlib.Path(os.getcwd()).parents[2]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/cmx_analysis'))
from eod import outright_eod as eod

context = 'nightcrawler'
# start = dt.date(2018,8,7)
# end  = dt.date(2018,8,9)
start = None
end = None
save_folder = os.path.join(str(os.getcwd()), 'production/livesim')
myeod = eod(context.lower(), start, end, save_folder)
myeod.run()
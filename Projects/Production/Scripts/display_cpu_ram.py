import os
import sys
import pathlib
cmx_rootpath = pathlib.Path(os.getcwd()).parents[2]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst'))
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/*'))
import cmx_util.system_monitor as cmx_sys
import time
import datetime as dt

while 1:
	ts      = dt.datetime.utcnow()
	cpu_pct = cmx_sys.get_cpu_pct()
	ram_pct = cmx_sys.get_ram_pct()
	print('{}\n CPU: {}% | RAM: {}%'.format(ts, cpu_pct, ram_pct))
	time.sleep(1)
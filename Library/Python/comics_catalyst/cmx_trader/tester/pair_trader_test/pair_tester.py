import os
import sys
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst'))
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/*'))
from cmx_trader.pair_trader import pair_trader

# To disable catalyst log:
# os.environ['CATALYST_LOG_LEVEL'] = '13' #CRITICAL = 15,ERROR = 14,WARNING = 13,NOTICE = 12,INFO = 11,DEBUG = 10,TRACE = 9
# Windows: use cmd and set env variable. instruction below
# http://www.dowdandassociates.com/blog/content/howto-set-an-environment-variable-in-windows-command-line-and-registry/

if os.path.exists('c:'):
    root_disk = 'c:'  
elif os.path.exists('/Users/fw/Trading/projects/xman'):
    root_disk = '/Users/fw/Trading/projects/xman'
else:
    root_disk = '/home/frankwang_trading'

if __name__ == '__main__':
    json_file = 'dash_eth_config.json'
    ptrader = pair_trader(json_file)
    ptrader.run()
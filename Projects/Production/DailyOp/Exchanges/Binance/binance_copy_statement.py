import os 
import sys
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/cmx_analysis'))
from exchange_statements import binance_file_manager

if __name__ == '__main__':
	bfm = binance_file_manager()
	saved_path = bfm.update()
	if saved_path:
		print('saved binance exchange statement to {}'.format(saved_path))
	else:
		print('failed to save binance exchange statement')
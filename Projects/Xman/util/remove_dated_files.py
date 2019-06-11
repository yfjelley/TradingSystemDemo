import os
import datetime as dt

root_folder = r'/home/frankwang_trading/comics_data'
keep_tdelta = dt.timedelta(days = 10)

def remove_files(folder, keep_tdelta, contain_words = None):
	now = dt.datetime.now()
	for f in os.listdir(folder):
		if contain_words is not None:
			if contain_words not in f:
				continue
		mtime = dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(folder, f)))
		if now - mtime > keep_tdelta:
			try:
				os.remove(os.path.join(folder, f))
				print('removed {}'.format(f))
			except:
				pass

print('removing dated files...')
for namespace in os.listdir(root_folder):
	log_folder = os.path.join(root_folder, '{}/log'.format(namespace))
	print('scanning {}....'.format(log_folder))
	remove_files(log_folder, keep_tdelta, 'log')


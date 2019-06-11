import os 
import datetime as dt



def getfiles(dirpath):
	a = [s for s in os.listdir(dirpath)
		 if os.path.isfile(os.path.join(dirpath, s))]
	a.sort(key=lambda s: os.path.getmtime(os.path.join(dirpath, s)))
	return a


context_list = ['cannonball', 'cecilia', 'colossus', 'husk', 'nightcrawler', 'polaris', 'sunfire']
context_list += ['{}-sim'.format(x) for x in context_list]



start = dt.date(2018,8,1)
end = dt.date(2018,11,5)
shift = -1 * dt.timedelta(days = 1)

for context in context_list:
	folder_list = [
				  '/Users/fw/Trading/projects/xman/comics_data/{}/trade'.format(context), 
				  '/Users/fw/Trading/projects/xman/comics_data/{}/snapshot'.format(context)
				  ]
	for folder in folder_list:
		if not os.path.exists(folder):
			continue
		for f in getfiles(folder):
			tmp_strblock = f.split('.')
			post_fix = '.'.join(tmp_strblock[1:])
			tmp_strblock = tmp_strblock[0].split('_')
			pre_fix = '_'.join(tmp_strblock[:-1])
			dstr = tmp_strblock[-1]
			try:
				fdate = dt.datetime.strptime(dstr, '%Y-%m-%d').date()
				if fdate >= start and fdate <= end:
					new_file = '{}_{}.{}'.format(pre_fix, fdate + shift, post_fix)
					os.rename(os.path.join(folder, f), os.path.join(folder, new_file))
				print(new_file)
			except:
				continue
	

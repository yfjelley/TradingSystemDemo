import datetime as dt
import numpy as np
import logging

def get_tdelta_from_str(mystr: str):
	# mystr in the format of : '7D', '1T'
	if 'D' in mystr:
		days = int(mystr.split('D')[0])
		return dt.timedelta(days = days)
	if 'H' in mystr:
		hours = int(mystr.split('H')[0])
		return dt.timedelta(hours = hours)
	if 'T' in mystr:
		minutes = int(mystr.split('T')[0])
		return dt.timedelta(minutes = minutes)
	return None

def get_legel_bar_info(context = None, **kwargs):
	binance_bars = ['1T', '3T', '5T', '15T', '30T', \
					'1H', '2H', '4H', '6H', '8H', '12H', \
					'1D', '3D', '1W', '1M']
	hitbtc_bars  = ['1T', '3T', '5T', '15T', '30T', \
					'1H', '4H', \
					'1D', '1W', '1M']
	# if len(kwargs) == 4:
	orig_barsize  = kwargs['barsize'] if 'barsize' in kwargs else None
	orig_barcount = kwargs['barcount'] if 'barcount' in kwargs else None
	limit         = kwargs['limit'] if 'limit' in kwargs else None
	exchange      = kwargs['exchange'] if 'exchange' in kwargs else 'binance'

	if orig_barsize	is not None and orig_barcount is not None and limit is not None:
		if 'mode' not in kwargs	or kwargs['mode'] == 'backtest':
			return {'barsize': orig_barsize, 'barcount': orig_barcount}
	else:
		if context is not None:
			orig_barsize  = context.signal_candle_size
			orig_barcount = context.signal_window
			limit         = context.signal_hist_rate_limit
			exchange      = context.exchange
			if context.global_mode == 'backtest':
				return {'barsize': orig_barsize, 'barcount': orig_barcount}
		else:
			return None

	tdelta = get_tdelta_from_str(orig_barsize) * orig_barcount
	total_minutes = int(tdelta.total_seconds() / 60)

	if exchange	== 'binance':
		for exch_bar in binance_bars:
			exch_tdelta = get_tdelta_from_str(exch_bar)
			new_barcount = tdelta / exch_tdelta
			if new_barcount <= limit:
				return{'barsize': exch_bar, 'barcount': int(np.ceil(new_barcount))}
	if exchange	== 'hitbtc':
		for exch_bar in hitbtc_bars:
			exch_tdelta = get_tdelta_from_str(exch_bar)
			new_barcount = tdelta / exch_tdelta
			if new_barcount <= limit:
				return{'barsize': exch_bar, 'barcount': int(np.ceil(new_barcount))}
	return None


import sys
import requests
import time
import datetime as dt
import pytz

# API
URL_COIN_LIST = 'https://www.cryptocompare.com/api/data/coinlist/'
URL_PRICE = 'https://min-api.cryptocompare.com/data/pricemulti?fsyms={}&tsyms={}&api_key=99d6944e766d2ca46b81dd212c780b2e8f870579295f0c6c3e5e81b439c45ccc'
URL_PRICE_MULTI = 'https://min-api.cryptocompare.com/data/pricemulti?fsyms={}&tsyms={}&api_key=99d6944e766d2ca46b81dd212c780b2e8f870579295f0c6c3e5e81b439c45ccc'
URL_PRICE_MULTI_FULL = 'https://min-api.cryptocompare.com/data/pricemultifull?fsyms={}&tsyms={}&api_key=99d6944e766d2ca46b81dd212c780b2e8f870579295f0c6c3e5e81b439c45ccc'
URL_HIST_PRICE = 'https://min-api.cryptocompare.com/data/pricehistorical?fsym={}&tsyms={}&ts={}&e={}&api_key=99d6944e766d2ca46b81dd212c780b2e8f870579295f0c6c3e5e81b439c45ccc'
URL_HIST_PRICE_DAY = 'https://min-api.cryptocompare.com/data/histoday?fsym={}&tsym={}&api_key=99d6944e766d2ca46b81dd212c780b2e8f870579295f0c6c3e5e81b439c45ccc'
URL_HIST_PRICE_HOUR = 'https://min-api.cryptocompare.com/data/histohour?fsym={}&tsym={}&api_key=99d6944e766d2ca46b81dd212c780b2e8f870579295f0c6c3e5e81b439c45ccc'
URL_AVG = 'https://min-api.cryptocompare.com/data/generateAvg?fsym={}&tsym={}&e={}&api_key=99d6944e766d2ca46b81dd212c780b2e8f870579295f0c6c3e5e81b439c45ccc'
URL_EXCHANGES = 'https://www.cryptocompare.com/api/data/exchanges'

URL_HIST_DAY_CUSTOM = 'https://min-api.cryptocompare.com/data/histoday?fsym={}&tsym={}&e={}&aggregate={}&limit={}&toTs={}'
URL_HIST_HOUR_CUSTOM = 'https://min-api.cryptocompare.com/data/histohour?fsym={}&tsym={}&e={}&aggregate={}&limit={}&toTs={}'
URL_HIST_MINUTE_CUSTOM = 'https://min-api.cryptocompare.com/data/histominute?fsym={}&tsym={}&e={}&aggregate={}&limit={}&toTs={}'

# FIELDS
PRICE = 'PRICE'
HIGH = 'HIGH24HOUR'
LOW = 'LOW24HOUR'
VOLUME = 'VOLUME24HOUR'
CHANGE = 'CHANGE24HOUR'
CHANGE_PERCENT = 'CHANGEPCT24HOUR'
MARKETCAP = 'MKTCAP'

# DEFAULTS
CURR = 'EUR'

###############################################################################

def query_cryptocompare(url,errorCheck=True):
    try:
        response = requests.get(url).json()
    except Exception as e:
        print('Error getting coin information. %s' % str(e))
        return None
    if errorCheck and (response.get('Response') == 'Error'):
        if 'e param is not valid the market does not exist for this coin pair' not in response.get('Message'):
            print('[ERROR] %s' % response.get('Message'))
        return None
    return response

def format_parameter(parameter):
    if isinstance(parameter, list):
        return ','.join(parameter)
    else:
        return parameter

###############################################################################

def get_coin_list(format=False):
    response = query_cryptocompare(URL_COIN_LIST, False)['Data']
    if format:
        return list(response.keys())
    else:
        return response

# TODO: add option to filter json response according to a list of fields
def get_price(coin, curr=CURR, full=False):
    if full:
        return query_cryptocompare(URL_PRICE_MULTI_FULL.format(format_parameter(coin),
            format_parameter(curr)))
    if isinstance(coin, list):
        return query_cryptocompare(URL_PRICE_MULTI.format(format_parameter(coin),
            format_parameter(curr)))
    else:
        return query_cryptocompare(URL_PRICE.format(coin, format_parameter(curr)))

def get_historical_price(coin, curr=CURR, timestamp=time.time(), exchange='CCCAGG'):
    if isinstance(timestamp, dt.datetime):
        timestamp = time.mktime(timestamp.timetuple())
    return query_cryptocompare(URL_HIST_PRICE.format(coin, format_parameter(curr),
        int(timestamp), format_parameter(exchange)))

def get_historical_price_day(coin, curr=CURR):
    return query_cryptocompare(URL_HIST_PRICE_DAY.format(coin, format_parameter(curr)))

def get_historical_price_hour(coin, curr=CURR):
    return query_cryptocompare(URL_HIST_PRICE_HOUR.format(coin, format_parameter(curr)))

def get_avg(coin, curr=CURR, exchange='CCCAGG'):
    response = query_cryptocompare(URL_AVG.format(coin, curr, format_parameter(exchange)))
    if response: 
        return response['RAW']

def get_exchanges():
    response = query_cryptocompare(URL_EXCHANGES)
    if response:
        return response['Data']

def get_hist_customized(bartype, base, quote, start, end, exchange = 'CCCAGG', aggregate = 1):
    # start and end times are in UTC
    if not start.tzinfo:
        utc_start = pytz.utc.localize(start)
    else:
        utc_start = start
    
    if not end.tzinfo:
        utc_end   = pytz.utc.localize(end)
    else:
        utc_end = end
    if utc_end < utc_start:
        return None
    tdelta = utc_end - utc_start
    # unix_end = int(time.mktime(utc_end.timetuple())) # This convert local time to unitx time
    utc_epoch = dt.datetime(1970, 1, 1, tzinfo = pytz.utc)
    unix_end = int((utc_end - utc_epoch).total_seconds())
    
    if bartype == 'daily' or bartype == 'day':
        bar_num = int(tdelta.days)
        return query_cryptocompare(URL_HIST_DAY_CUSTOM.format(base.upper(), quote.upper(), exchange.upper(), aggregate, bar_num, unix_end))
    if bartype == 'hourly' or bartype == 'hour':
        bar_num = int(tdelta.total_seconds() / 3600)
        return query_cryptocompare(URL_HIST_HOUR_CUSTOM.format(base.upper(), quote.upper(), exchange.upper(), aggregate, bar_num, unix_end))
    if bartype == 'minute':
        bar_num = int(tdelta.total_seconds() / 60)
        return query_cryptocompare(URL_HIST_MINUTE_CUSTOM.format(base.upper(), quote.upper(), exchange.upper(), aggregate, bar_num, unix_end))

def get_hist_daily(base, quote, start, end, exchange = 'CCCAGG', aggregate = 1):
    return get_hist_customized('daily', base, quote, start, end, exchange, aggregate)
# print(get_hist_daily('BTC', 'USD', dt.date(2018,7,1), dt.date(2018,7,10)))
# print(get_hist_daily('BTC', 'USDT', dt.date(2018,7,1), dt.date(2018,7,10)))
# print(get_hist_daily('BTC', 'BTC', dt.date(2018,7,1), dt.date(2018,7,10)))

def _get_hist_hourly_single_attempt(base, quote, start, end, exchange = 'CCCAGG', aggregate = 1):
    return get_hist_customized('hourly', base, quote, start, end, exchange, aggregate)

def _get_hist_minute_single_attempt(base, quote, start, end, exchange = 'CCCAGG', aggregate = 1):
    return get_hist_customized('minute', base, quote, start, end, exchange, aggregate)

def _get_hist_by_bartype(base, quote, start, end, exchange = 'CCCAGG', aggregate = 1, bartype = 'hour'):
    if not isinstance(start, dt.datetime):
        utc_start = dt.datetime.combine(start, dt.time(0,0))
    else:
        utc_start = start
    # utc_start = pytz.utc.localize(utc_start)
    
    if not isinstance(end, dt.datetime):
        utc_end = dt.datetime.combine(end, dt.time(0,0))
    else:
        utc_end = end
    # utc_end = pytz.utc.localize(utc_end)
        

    if bartype == 'hourly' or bartype == 'hour':
        bar_duration = dt.timedelta(hours = 1)
        bar_func = _get_hist_hourly_single_attempt
    elif bartype == 'minute':
        bar_duration = dt.timedelta(minutes = 1)
        bar_func = _get_hist_minute_single_attempt
        
    cur_end = utc_end
    raw_data = bar_func(base, quote, utc_start, cur_end, exchange, aggregate)
    if raw_data is None:
        return None
    return_start = dt.datetime.utcfromtimestamp(raw_data['Data'][0]['time'])
    data_list = raw_data['Data']
    while return_start > utc_start:
        # print(return_start)
        cur_end = return_start - bar_duration
        raw_data = bar_func(base, quote, utc_start, cur_end, exchange, aggregate)
        if raw_data is None:
            # data download is not completed
            return None
        return_start = dt.datetime.utcfromtimestamp(raw_data['Data'][0]['time'])
        data_list = raw_data['Data'] + data_list # append to the head
    raw_data['Data'] = data_list
    return raw_data

def get_hist_hourly(base, quote, start, end, exchange = 'CCCAGG', aggregate = 1):
    return _get_hist_by_bartype(base, quote, start, end, exchange = exchange, aggregate = 1, bartype = 'hour')

def get_hist_minute(base, quote, start, end, exchange = 'CCCAGG', aggregate = 1):
    return _get_hist_by_bartype(base, quote, start, end, exchange = exchange, aggregate = 1, bartype = 'minute')

# print(get_hist_hourly('BTC', 'USD', dt.date(2018,7,1), dt.date(2018,7,10)))
# print(get_hist_hourly('BTC', 'USD', dt.date(2017,7,1), dt.date(2018,7,10)))


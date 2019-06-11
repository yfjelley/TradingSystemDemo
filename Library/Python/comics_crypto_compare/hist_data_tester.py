import hist_data
import datetime as dt
import matplotlib.pyplot as plt
from mpl_finance import candlestick_ohlc
import matplotlib.dates as mdates





# coin_df = hist_data.get_coin_df()
# print(coin_df)

###############
# hourly data #
###############
# hourly = hist_data.get_hourly_df('dash', 'eth', dt.datetime(2018, 10, 30, 17, 0), dt.datetime(2018,10,31, 4,0,0), exchange = 'binance')
# hourly = hist_data.get_hourly_df('dash', 'eth', dt.datetime(2018, 11, 2, 0, 0), dt.datetime(2018,11,5, 0,0,0), exchange = 'binance')
# print(hourly.head())
# print(hourly.tail())
# print(hourly)
# print(hourly.close)
# fig, ax = plt.subplots()
# candlestick_ohlc(ax, zip(mdates.date2num(hourly.index), hourly['open'],hourly['high'],hourly['low'],hourly['close']), width=0.02)

##############
# daily data #
##############
# daily = hist_data.get_daily_df('dash', 'eth', dt.datetime(2018,10,20), dt.datetime(2018, 11, 5), exchange = 'binance')
# print(daily)
# fig, ax = plt.subplots()
# candlestick_ohlc(ax, zip(mdates.date2num(daily.index), daily['open'], daily['high'], daily['low'], daily['close']), width=0.4)

###############
# minute data #
###############
minute = hist_data.get_minute_df('dash', 'eth', dt.datetime(2018,11,4, 2, 0), dt.datetime(2018, 11, 4, 5, 0), exchange = 'binance')
print(minute)
fig, ax = plt.subplots()
candlestick_ohlc(ax, zip(mdates.date2num(minute.index), minute['open'], minute['high'], minute['low'], minute['close']), width=0.002)

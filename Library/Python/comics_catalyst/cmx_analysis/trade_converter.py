import os
import numpy as np
import datetime as dt
import pandas as pd
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
import sys
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_crypto_compare'))
import hist_data

class single_product_trade_converter:
    # trade_df format: 
    # Index: datetime
    # Columns: 
    # mkt_price, pnl, position, fee, fill_price, cost_basis, realized, unrealized, net
    # pnl, realized, unrealized are gross
    # all pnl related terms are in quote currency
    def __init__(self, exchange, symbol, init_pos, init_cost_basis, trade_df):
        self.exchange = exchange
        self.symbol = symbol
        self.sym_info = self._format_symbol(symbol)
        self.base_coin = self.sym_info['base']
        self.quote_coin = self.sym_info['quote']
        self.init_pos = init_pos
        self.init_cost_basis = init_cost_basis
        self.trade_df = trade_df
        self.ref_price_map = {}

    def _format_symbol(self, symbol):
        if '/' in symbol:
            coin_list = symbol.split('/')
        elif '.' in symbol:
            coin_list = symbol.split('.')
        elif '_' in symbol:
            coin_list = symbol.split('_')
        elif '-' in symbol:
            coin_list = symbol.split('-')
        else:
            return {
                    'binance'  : symbol.upper(), 
                    'dot'      : symbol.lower(), 
                    'underline': symbol.lower(), 
                    'base'     : symbol, 
                    'quote'    : symbol
                    }
        binance_symbol = '{}{}'.format(coin_list[0].upper(), coin_list[1].upper())
        dot_symbol     = '{}.{}'.format(coin_list[0].lower(), coin_list[1].lower())
        under_symbol   = '{}_{}'.format(coin_list[0].lower(), coin_list[1].lower())
        return {
                'binance'  : binance_symbol, 
                'dot'      : dot_symbol, 
                'underline': under_symbol,
                'base'     : coin_list[0].lower(), 
                'quote'    : coin_list[1].lower()
                }

    def _convert_by_time(self, t0, tn, price_df = None, ts_interval = dt.timedelta(minutes = 1)):
        if price_df is None or len(price_df) == 0:
            price_df = None
            if ts_interval.total_seconds() < 3600:
                price_df = self.get_cc_minute_data(
                                                   self.symbol, 
                                                   t0 - dt.timedelta(minutes = 10), 
                                                   tn + dt.timedelta(minutes = 10)
                                                   )
                if price_df is not None:
                    price_df = price_df[['close']]
                # minute data is only available for past 7 days
            if price_df is None:
                price_df = self.get_cc_hourly_data(
                                                   self.symbol, 
                                                   t0 - dt.timedelta(hours = 1), 
                                                   tn + dt.timedelta(hours = 1)
                                                   )[['close']]
        else:
            price_df = price_df[(price_df.index >= t0) & (price_df.index <= tn)]
            
        pos = self.init_pos
        fee = 0
        cost_basis = self.init_cost_basis if not np.isnan(self.init_cost_basis) else 0
        realized = 0
        ts_array = np.arange(t0, tn, ts_interval)
        result_df = pd.DataFrame(
                                 columns = ['pnl', 'position', 'fee', 'fill_price', 'cost_basis', 'realized', 'unrealized'], 
                                 index = ts_array
                                )
        price_df.columns = ['mkt_price']
        result_df = pd.concat([price_df, result_df], axis = 1)
        result_df.fillna(method = 'ffill', inplace = True)
        result_df.fillna(method = 'bfill', inplace = True)
        result_df = result_df[(result_df.index >= t0) & (result_df.index <= tn)]

        if self.trade_df is None:
            pnl = (result_df['mkt_price'] - cost_basis) * pos
            result_df['position'] = pos
            result_df['fee'] = fee
            # result_df['fill_price'] = np.nan
            result_df['cost_basis'] = cost_basis
            result_df['realized'] = 0
            result_df['unrealized'] = pnl
            result_df['pnl'] = pnl
            return result_df

        trade_df = self.trade_df[(self.trade_df.index >= t0) & (self.trade_df.index <= tn)].dropna()
        if len(trade_df) == 0:
            pnl = (result_df['mkt_price'] - cost_basis) * pos
            result_df['position'] = pos
            result_df['fee'] = fee
            # result_df['fill_price'] = np.nan
            result_df['cost_basis'] = cost_basis
            result_df['realized'] = 0
            result_df['unrealized'] = pnl
            result_df['pnl'] = pnl
            return result_df
        result_df = result_df[['mkt_price', 'pnl', 'position', 'fee', 'fill_price', 'cost_basis', 'realized', 'unrealized']]

        trd_idx = 0
        for i in range(len(result_df)):
            if trd_idx >= len(trade_df):
                trd_ts = result_df.index[-1] + dt.timedelta(days = 1)
            else:
                trd_ts = trade_df.index[trd_idx]
                # reset ref prices if eod changes
                if trd_idx > 0:
                    pre_trd_ts = trade_df.index[trd_idx - 1]
                    if pre_trd_ts.date() != trd_ts.date():
                        self.ref_price_map = {} 

            prc_ts = result_df.index[i]
            price = result_df['mkt_price'][i]
            fill_price = np.nan
            while trd_ts <= prc_ts:
                # update position, cost_basis, fee, pnl
                fee_native = trade_df['fee'][trd_idx]
                fee_coin = trade_df['fee_coin'][trd_idx]
                fee += self._convert_fee(fee_native, fee_coin, prc_ts)
                fill_price = trade_df['price'][trd_idx]
                amount = trade_df['amount'][trd_idx]
                if amount * pos > 0:
                    # adding positions, realized doesn't change
                    cost_basis = (cost_basis * pos + fill_price * amount) / (pos + amount)
                else:
                    if abs(amount) <= abs(pos):
                        # reduced but not flipped, cost_basis doesn't change
                        realized += (fill_price - cost_basis) * amount * (-1)
                    else:
                        # previous position flattened and flipped, all changed
                        realized += (fill_price - cost_basis) * pos
                        cost_basis = fill_price
                pos += amount
                trd_idx += 1
                if trd_idx >= len(trade_df):
                    break
                trd_ts = trade_df.index[trd_idx]
            unrealized = (price - cost_basis) * pos
            pnl = realized + unrealized
            result_df.iloc[i, 1] = pnl
            result_df.iloc[i, 2] = pos
            result_df.iloc[i, 3] = fee
            result_df.iloc[i, 4] = fill_price
            result_df.iloc[i, 5] = cost_basis
            result_df.iloc[i, 6] = realized
            result_df.iloc[i, 7] = unrealized
            
        return result_df

    def convert_by_minute(self, t0, tn, price_df = None):
        return self._convert_by_time(t0, tn, price_df = price_df)

    def convert_by_hour(self, t0, tn, price_df = None):
        return self._convert_by_time(t0, tn, price_df, dt.timedelta(hours = 1))

    def get_cc_minute_data(self, symbol, start, end):
        minute_data = self._get_cc_data_by_exchange(self.exchange, symbol, start, end, hist_data.get_minute_df)
        if minute_data is None:
                minute_data = self._get_cc_data_by_exchange('CCCAGG', symbol, start, end, hist_data.get_minute_df)
        return minute_data

    def get_cc_hourly_data(self, symbol, start, end):
        hourly_data = self._get_cc_data_by_exchange(self.exchange, symbol, start, end, hist_data.get_hourly_df)
        if hourly_data is None:
                hourly_data = self._get_cc_data_by_exchange('CCCAGG', symbol, start, end, hist_data.get_hourly_df)
        return hourly_data
    
    def _get_cc_data_by_exchange(self, exchange, symbol, start, end, func = hist_data.get_hourly_df):
        sym_info = self._format_symbol(symbol)
        if (sym_info['base'] == 'usdt') \
        or (sym_info['base'] == 'btc' and sym_info['quote'] not in ['usdt']) \
        or (sym_info['base'] == 'eth' and sym_info['quote'] not in ['usdt', 'btc']) \
        or (sym_info['base'] == 'bnb' and sym_info['quote'] not in ['usdt', 'btc', 'eth']):
            hourly_data = 1 / func(
                                    sym_info['quote'].upper(), 
                                    sym_info['base'].upper(), 
                                    start, 
                                    end,
                                    exchange = exchange
                                    )
        else:
            hourly_data = func(
                                sym_info['base'].upper(), 
                                sym_info['quote'].upper(), 
                                start, 
                                end,
                                exchange = exchange
                                )
        return hourly_data

    def _convert_fee(self, native_fee, fee_coin, ts):
        # quote eod price:
        if fee_coin == self.quote_coin:
            return native_fee

        symbol = '{}_{}'.format(fee_coin, self.quote_coin)
        convert_factor = self.ref_price_map.get(symbol)
        if convert_factor:
            return native_fee * convert_factor

        hourly_data = self.get_cc_hourly_data(symbol, ts - dt.timedelta(hours = 1), ts + dt.timedelta(hours = 1))
        if hourly_data is not None and abs((hourly_data.index[-1] - ts).total_seconds()) <= 3600:
            convert_factor = hourly_data['close'][-1]
            self.ref_price_map[symbol] = convert_factor
        else:
            convert_factor = np.nan
            print('[WARNING] failed to download cc price for {} at {}'.format(symbol, ts))
        return native_fee * convert_factor
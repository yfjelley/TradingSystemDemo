import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
sys.path.append(os.path.join(cmx_rootpath,'Library/Python/comics_crypto_compare'))
sys.path.append(os.path.join(cmx_rootpath,'Library/Python/comics_crypto_compare/*'))
import hist_data
import matplotlib.pyplot as plt
import ccxt
import json
import shutil
import pytz

class binance_file_manager:
    def __init__(self):
        if os.path.exists('/Users/fw/Downloads'):
            self.exchange = 'binance'
            self.download_folder = '/Users/fw/Downloads'
            self.download_file   = None
            self.statement_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/exchanges/{}'.format(self.exchange)
            self.statement_prefix = '{}_trade_history'.format(self.exchange)
            self.statement_file   = '{}.csv'.format(self.statement_prefix)
            self.statement_df = self._read_csv(self.statement_folder, self.statement_file)
            self.eod_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/exchange_eod/{}_eod'.format(self.exchange)
        else:
            # TODO: add destination for Linux / Win system
            pass

    def _read_csv(self, folder, file):
        if folder is None or file is None:
            return None
        if not os.path.exists(os.path.join(folder, file)):
            return None
        df = pd.read_csv(os.path.join(folder, file), header = 0, index_col = 0, parse_dates = True)
        df = df[df.index < df.index[-1]]
        return df

    def _get_recent_file(self, folder, keyword = '', keywords = []):
        if not folder or not os.path.exists(folder):
            return None
        latest_ts = -1
        latest_file = None
        for f in os.listdir(folder):
            if keyword not in f:
                continue
            all_keys_found = True
            for kw in keywords:
                if not all_keys_found:
                    continue
                if kw not in f:
                    all_keys_found = False
            if not all_keys_found:
                continue
            mtime = os.path.getmtime(os.path.join(folder, f))
            if mtime > latest_ts:
                latest_ts = mtime
                latest_file = f
        return latest_file
    
    def get_latest_download(self):
        self.download_file = self._get_recent_file(self.download_folder, keywords = ['TradeHistory', 'xlsx'])
        if self.download_file:
            return os.path.join(self.download_folder, self.download_file)
        else:
            return None

    def _convert_ticker(self, ticker):
        bc = ''
        qc = ''
        lower_ticker = ticker.lower()
        if lower_ticker[-4:] == 'usdt':
            bc = lower_ticker[:-4]
            qc = 'usdt'
        else:
            bc = lower_ticker[:-3]
            qc = lower_ticker[-3:]
        return '{}_{}'.format(bc, qc)

    def read_excel(self, f, t0 = None, tn = None):
        dtype_map = {'Price': np.float64, 'Amount': np.float64, 'Total': np.float64, 'Fee': np.float64}
        df = pd.read_excel(f, sheet_name = 0, header = 0, index_col = 0, converters = dtype_map)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace = True, ascending = True)
        if t0 is not None:
            df = df[df.index >= t0]
        if tn is not None:
            df = df[df.index <= tn]
        new_columns = []
        for c in df.columns:
            if c == 'Market':
                new_columns.append('ticker')
            elif c == 'Type':
                new_columns.append('side')
            elif c == 'Fee Coin':
                new_columns.append('fee_coin')
            elif c == 'Total':
                new_columns.append('value')
            else:
                new_columns.append(c.lower())
        df.columns = new_columns
        df = df[['ticker', 'side', 'price', 'amount', 'value', 'fee', 'fee_coin']]
        
        for i in range(len(df)):
            ticker = self._convert_ticker(df['ticker'][i])
            side = df['side'][i].lower()
            amount = float(df['amount'][i])
            amount *= 1 if side == 'buy' else -1
            fee_coin = df['fee_coin'][i].lower()
            # df.iloc[i]['ticker'] = ticker
            # df.iloc[i]['side'] = side
            # df.iloc[i]['amount'] = amount
            # df.iloc[i]['fee_coin'] = fee_coin
            df.iloc[i, [0, 1, 3, 6]] = [ticker, side, amount, fee_coin]
        return df
    
    def save_copy(self):
        from_path = self.get_latest_download()
        if not from_path:
            return None

        eod = dt.datetime.utcnow().date()
        to_file = '{}_{}.csv'.format(self.statement_prefix, eod)
        if self.statement_df is not None:
            df = self.read_excel(from_path, t0 = self.statement_df.index[-1] + dt.timedelta(seconds = 1e-3))
            self.statement_df = pd.concat([self.statement_df, df])
        else:
            df = self.read_excel(from_path)
            self.statement_df = df
        df.to_csv(os.path.join(self.statement_folder, to_file))
        self.statement_df.to_csv(os.path.join(self.statement_folder, self.statement_file))
        return os.path.join(self.statement_folder, to_file)

    def update(self):
        return self.save_copy()

# bfm = binance_file_manager()
# print(bfm.update())


class hitbtc_file_manager:
    def __init__(self):
        if os.path.exists('/Users/fw/Downloads'):
            self.exchange = 'hitbtc'
            self.download_folder = '/Users/fw/Downloads'
            self.download_file   = None
            self.statement_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/exchanges/{}'.format(self.exchange)
            self.statement_prefix = '{}_trade_history'.format(self.exchange)
            self.statement_file   = '{}.csv'.format(self.statement_prefix)
            self.statement_df = self._read_csv(self.statement_folder, self.statement_file)
            self.eod_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/exchange_eod/{}_eod'.format(self.exchange)
        else:
            pass

    def _read_csv(self, folder, file):
        if folder is None or file is None:
            return None
        if not os.path.exists(os.path.join(folder, file)):
            return None
        df = pd.read_csv(os.path.join(folder, file), header = 0, index_col = 0, parse_dates = True)
        df = df[df.index < df.index[-1]]
        return df

    def _get_recent_file(self, folder, keyword = '', keywords = []):
        if not folder or not os.path.exists(folder):
            return None
        latest_ts = -1
        latest_file = None
        for f in os.listdir(folder):
            if keyword not in f:
                continue
            all_keys_found = True
            for kw in keywords:
                if not all_keys_found:
                    continue
                if kw not in f:
                    all_keys_found = False
            if not all_keys_found:
                continue
            mtime = os.path.getmtime(os.path.join(folder, f))
            if mtime > latest_ts:
                latest_ts = mtime
                latest_file = f
        return latest_file
    
    def get_latest_download(self):
        self.download_file = self._get_recent_file(self.download_folder, keywords = ['trades', 'csv'])
        if self.download_file:
            return os.path.join(self.download_folder, self.download_file)
        else:
            return None

    def _convert_ticker(self, ticker):
        if '/' not in ticker:
            return None

        coins = ticker.split('/')
        bc = coins[0].lower()
        qc = coins[1].lower()
        return '{}_{}'.format(bc, qc)

    def read_csv(self, f, t0 = None, tn = None):
        # dtype_map = {'Price': np.float64, 'Quantity': np.float64, 'Total': np.float64, 'Fee': np.float64, 'Rebate': np.float64}
        # df = pd.read_csv(f, header = 0, index_col = 0, parse_dates = True, converters = dtype_map)
        # df.index = pd.to_datetime(df.index)
        df = pd.read_csv(f, header = 0, index_col = 0, parse_dates = True)
        df.sort_index(inplace = True, ascending = True)
        if t0 is not None:
            df = df[df.index >= t0]
        if tn is not None:
            df = df[df.index <= tn]

        tickers  = df['Instrument'].map(self._convert_ticker)
        sides    = df['Side']
        prices   = df['Price']
        amounts  = df['Quantity'] * sides.map(lambda x: 1 if x.lower() == 'buy' else -1)
        values   = amounts * prices
        fees     = df['Fee'] - df['Rebate']
        fee_coins= tickers.map(lambda x: x.split('_')[1])

        new_df = pd.DataFrame({
                               'ticker': tickers,
                               'side': sides,
                               'price': prices,
                               'amount': amounts,
                               'value': values,
                               'fee': fees,
                               'fee_coin': fee_coins
                             })
        return new_df
    
    def save_copy(self):
        from_path = self.get_latest_download()
        if not from_path:
            return None

        eod = dt.datetime.utcnow().date()
        to_file = '{}_{}.csv'.format(self.statement_prefix, eod)
        if self.statement_df is not None:
            df = self.read_csv(from_path, t0 = self.statement_df.index[-1] + dt.timedelta(seconds = 1e-3))
            self.statement_df = pd.concat([self.statement_df, df])
        else:
            df = self.read_csv(from_path)
            self.statement_df = df
        df.to_csv(os.path.join(self.statement_folder, to_file))
        self.statement_df.to_csv(os.path.join(self.statement_folder, self.statement_file))
        return os.path.join(self.statement_folder, to_file)

    def update(self):
        return self.save_copy()

# hfm = hitbtc_file_manager()
# print(hfm.update())

class huobipro_file_manager:
    def __init__(self):
        if os.path.exists('/Users/fw/Downloads'):
            self.exchange = 'huobipro'
            self.download_folder = '/Users/fw/Downloads'
            self.download_file   = None
            self.statement_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/exchanges/{}'.format(self.exchange)
            self.statement_prefix = '{}_trade_history'.format(self.exchange)
            self.statement_file   = '{}.csv'.format(self.statement_prefix)
            self.statement_df = self._read_old_csv(self.statement_folder, self.statement_file)
            self.eod_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/exchange_eod/{}_eod'.format(self.exchange)
        else:
            pass

    def _read_old_csv(self, folder, file):
        if folder is None or file is None:
            return None
        if not os.path.exists(os.path.join(folder, file)):
            return None
        df = pd.read_csv(os.path.join(folder, file), header = 0, index_col = 0, parse_dates = True)
        df = df[df.index < df.index[-1]]
        return df

    def _get_recent_file(self, folder, keyword = '', keywords = []):
        if not folder or not os.path.exists(folder):
            return None
        latest_ts = -1
        latest_file = None
        for f in os.listdir(folder):
            if keyword not in f:
                continue
            all_keys_found = True
            for kw in keywords:
                if not all_keys_found:
                    continue
                if kw not in f:
                    all_keys_found = False
            if not all_keys_found:
                continue
            mtime = os.path.getmtime(os.path.join(folder, f))
            if mtime > latest_ts:
                latest_ts = mtime
                latest_file = f
        return latest_file
    
    def get_latest_download(self):
        self.download_file = self._get_recent_file(self.download_folder, keywords = ['TransactionHistory-', 'csv'])
        if self.download_file:
            return os.path.join(self.download_folder, self.download_file)
        else:
            return None

    def _convert_ticker(self, ticker):
        if '/' not in ticker:
            return None

        coins = ticker.split('/')
        bc = coins[0].lower()
        qc = coins[1].lower()
        return '{}_{}'.format(bc, qc)

    def _get_fee_and_feecoin(self, fees):
        if fees is None:
            return None
        
        out_fees = []
        out_fcoins = []
        for i in range(len(fees)):
            coin = ''.join([x for x in fees[i] if x.isalpha()])
            out_fcoins.append(coin)
            fee = float(fees[i][:(-len(coin))])
            out_fees.append(fee)
        return {
                'fee': pd.Series(out_fees, index = fees.index),
                'fee_coin': pd.Series(out_fcoins, index = fees.index)
                }

    def _convert_timezone(self, naive_ts):
        singapore_tz = pytz.timezone('Asia/Singapore')
        utc_tz = pytz.utc
        out_ts = singapore_tz.localize(naive_ts).astimezone(utc_tz)
        out_ts = out_ts.replace(tzinfo = None)
        return out_ts

    def _read_new_csv(self, f, t0 = None, tn = None):
        # dtype_map = {'Price': np.float64, 'Quantity': np.float64, 'Total': np.float64, 'Fee': np.float64, 'Rebate': np.float64}
        # df = pd.read_csv(f, header = 0, index_col = 0, parse_dates = True, converters = dtype_map)
        # df.index = pd.to_datetime(df.index)
        df = pd.read_csv(f, header = 0, index_col = False, parse_dates = [0])
        df['Time'] = df['Time'].map(self._convert_timezone)
        df = df.set_index('Time')
        df.sort_index(inplace = True, ascending = True)
        if t0 is not None:
            df = df[df.index >= t0]
        if tn is not None:
            df = df[df.index <= tn]
        tickers  = df['Pair'].map(self._convert_ticker)
        sides    = df['Side']
        prices   = df['Price']
        amounts  = df['Amount'] * sides.map(lambda x: 1 if x.lower() == 'buy' else -1)
        values   = amounts * prices
        fee_dict = self._get_fee_and_feecoin(df['Fee'])
        fees     = fee_dict['fee']
        fee_coins= fee_dict['fee_coin']

        new_df = pd.DataFrame({
                               'ticker': tickers,
                               'side': sides,
                               'price': prices,
                               'amount': amounts,
                               'value': values,
                               'fee': fees,
                               'fee_coin': fee_coins
                             })
        return new_df
    
    def save_copy(self):
        from_path = self.get_latest_download()
        if not from_path:
            return None

        eod = dt.datetime.utcnow().date()
        to_file = '{}_{}.csv'.format(self.statement_prefix, eod)
        if self.statement_df is not None:
            df = self._read_new_csv(from_path, t0 = self.statement_df.index[-1] + dt.timedelta(seconds = 1e-3))
            self.statement_df = pd.concat([self.statement_df, df])
        else:
            df = self._read_new_csv(from_path)
            self.statement_df = df

        if not os.path.exists(self.statement_folder):
            os.makedirs(self.statement_folder)
        df.to_csv(os.path.join(self.statement_folder, to_file))
        self.statement_df.to_csv(os.path.join(self.statement_folder, self.statement_file))
        return os.path.join(self.statement_folder, to_file)

    def update(self):
        return self.save_copy()

hbpfm = huobipro_file_manager()
print(hbpfm.update())

                
class binance_statement:
    def __init__(self):
        self.exchange = 'binance'
        self.bfm = binance_file_manager()
        self.statement_pathfile = os.path.join(self.bfm.statement_folder, self.bfm.statement_file)
        self.statement_df = None
        if os.path.exists(self.statement_pathfile):
            self.statement_df = self.read_statement(self.statement_pathfile)
        self.output_folder = self.bfm.eod_folder

    def read_statement(self, f):
        df = None
        try:
            fn, fext = os.path.splitext(f)
            if fext == '.csv':
                df = pd.read_csv(f, header = 0, index_col = 0, parse_dates = True)
                df.sort_index(inplace = True, ascending = True)
            elif fext == 'xlsx':
                dtype_map = {'Price': np.float64, 'Amount': np.float64, 'Total': np.float64, 'Fee': np.float64}
                df = pd.read_excel(f, sheet_name = 0, header = 0, index_col = 0, converters = dtype_map)
                df.index = pd.to_datetime(df.index)
                df.sort_index(inplace = True, ascending = True)
            return df
        except Exception as e:
            print(e)
            return None

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

    def _get_pair_vs_common_coins(self, coin):
        common_coins = ['btc', 'eth', 'usdt']
        symbol_list = []
        for c in common_coins:
            symbol_list.append('{}.{}'.format(coin.lower(), c))
        return symbol_list

    def _get_cc_hourly_data(self, symbol, start, end):
        hourly_data = self._get_cc_hourly_data_by_exchange(self.exchange, symbol, start, end)
        if hourly_data is None:
                hourly_data = self._get_cc_hourly_data_by_exchange('CCCAGG', symbol, start, end)
        return hourly_data
    
    def _get_cc_hourly_data_by_exchange(self, exchange, symbol, start, end):
        symbol_dict = self._format_symbol(symbol)
        
        if (symbol_dict['base'] == 'usdt') \
        or (symbol_dict['base'] == 'btc' and symbol_dict['quote'] not in ['usdt']) \
        or (symbol_dict['base'] == 'eth' and symbol_dict['quote'] not in ['usdt', 'btc']) \
        or (symbol_dict['base'] == 'bnb' and symbol_dict['quote'] not in ['usdt', 'btc', 'eth']):
            hourly_data = 1 / hist_data.get_hourly_df(
                                                    symbol_dict['quote'].upper(), 
                                                    symbol_dict['base'].upper(), 
                                                    start, 
                                                    end,
                                                    exchange = exchange
                                                    )
        else:
            hourly_data = hist_data.get_hourly_df(
                                                symbol_dict['base'].upper(), 
                                                symbol_dict['quote'].upper(), 
                                                start, 
                                                end,
                                                exchange = exchange
                                                )
        return hourly_data
        

    def _get_conversion_prices(self, symbol_list, end_dt):
        result = {}
        for symbol in symbol_list:
            hourly_data = self._get_cc_hourly_data(symbol, end_dt - dt.timedelta(days = 2), end_dt + dt.timedelta(days = 1))
            if hourly_data is None or len(hourly_data) == 0:
                continue
            hourly_data = hourly_data[abs(hourly_data.index - end_dt) <= dt.timedelta(hours = 1)]
            if hourly_data is None or len(hourly_data) == 0:
                continue
            hourly_data = hourly_data[hourly_data.index <= end_dt]
            price = hourly_data['close'][-1]
            result[symbol] = price
        return result

    def mark_by_algo_df(self, algo_df):
        local_algo_df = algo_df.dropna().copy()
        start = local_algo_df.index[0]
        end   = local_algo_df.index[-1]
        init_pos   = local_algo_df['base_pos'][0]
        init_price = local_algo_df['last_sale_price'][0]
        symbol = local_algo_df['symbol'][0]
        symbol_dict = self._format_symbol(symbol)

        ref_symbols = self._get_pair_vs_common_coins(symbol_dict['quote']) \
                    + self._get_pair_vs_common_coins(symbol_dict['base']) \
                    + self._get_pair_vs_common_coins('bnb')
        ref_symbols = list(set(ref_symbols))
        ref_prices  = self._get_conversion_prices(ref_symbols, end - dt.timedelta(minutes = 1))
        local_state_df = self.statement_df[
                                           (self.statement_df.index >= start) & 
                                           (self.statement_df.index <= end) & 
                                           (self.statement_df['Market'] == symbol_dict['binance'])
                                           ].copy()
        state_pnl_df = pd.DataFrame({
                                      'amount'         : 0,
                                      'fill_price'     : init_price,
                                      'ave_fill_price' : init_price,
                                      'position'       : init_pos,
                                      'mkt_price'      : init_price,
                                      'pnl_btc'     : 0,
                                      'pnl_eth'     : 0,
                                      'pnl_usd'     : 0,
                                      'realized_pnl_btc'   : 0,
                                      'realized_pnl_eth'   : 0,
                                      'realized_pnl_usd'   : 0,
                                      'unrealized_pnl_btc' : 0,
                                      'unrealized_pnl_eth' : 0,
                                      'unrealized_pnl_usd' : 0,
                                      'fee_btc'     : 0,
                                      'fee_eth'     : 0,
                                      'fee_usd'     : 0,
                                      'traded_btc'  : 0,
                                      'traded_eth'  : 0,
                                      'traded_usd'  : 0
                                    }, index = [start - dt.timedelta(minutes = 1)])

        for i in range(len(local_state_df)):
            ts = local_state_df.index[i]
            amount = local_state_df['Amount'][i]
            if local_state_df['Type'][i] == 'SELL':
                amount *= -1
            pre_ave_price = state_pnl_df['ave_fill_price'][-1]
            fill_price     = local_state_df['Price'][i]
            pre_pos = state_pnl_df['position'][-1]
            cur_pos = pre_pos + amount
            pre_mkt_price = state_pnl_df['mkt_price'][-1]
            mkt_price     = local_algo_df[local_algo_df.index <= ts]['last_sale_price'][-1]
            if pre_pos == 0:
                # fill_price / mkt_price remains
                ave_fill_price = fill_price
                pnl_realized = 0
            elif pre_pos * amount >= 0:
                # adding positions
                ave_fill_price = (pre_pos * pre_ave_price + amount * fill_price) / (pre_pos + amount)
                pnl_realized = 0
            else:
                # reducing positions:
                if cur_pos == 0:
                    # flat
                    pnl_realized = amount * (pre_ave_price - fill_price)
                    ave_fill_price = np.nan
                elif cur_pos * pre_pos > 0:
                    # reduced but not flat
                    pnl_realized = amount * (pre_ave_price - fill_price)
                    ave_fill_price = pre_ave_price
                else:
                    # position flipped
                    ave_fill_price = fill_price
                    pnl_realized = pre_pos * (fill_price - pre_ave_price)
            pnl_unrealized = cur_pos * (mkt_price - ave_fill_price)
            realized_pnl_btc   = pnl_realized * ref_prices['{}.btc'.format(symbol_dict['quote'])] + state_pnl_df['realized_pnl_btc'][-1]
            realized_pnl_eth   = pnl_realized * ref_prices['{}.eth'.format(symbol_dict['quote'])] + state_pnl_df['realized_pnl_eth'][-1]
            realized_pnl_usd   = pnl_realized * ref_prices['{}.usdt'.format(symbol_dict['quote'])] + state_pnl_df['realized_pnl_usd'][-1]
            unrealized_pnl_btc = pnl_unrealized * ref_prices['{}.btc'.format(symbol_dict['quote'])]
            unrealized_pnl_eth = pnl_unrealized * ref_prices['{}.eth'.format(symbol_dict['quote'])]
            unrealized_pnl_usd = pnl_unrealized * ref_prices['{}.usdt'.format(symbol_dict['quote'])]
            pnl_btc = realized_pnl_btc + unrealized_pnl_btc
            pnl_eth = realized_pnl_eth + unrealized_pnl_eth
            pnl_usd = realized_pnl_usd + unrealized_pnl_usd
            fee_btc = local_state_df['Fee'][i] * ref_prices['{}.btc'.format(symbol_dict['quote'])] + state_pnl_df['fee_btc'][-1]
            fee_eth = local_state_df['Fee'][i] * ref_prices['{}.eth'.format(symbol_dict['quote'])] + state_pnl_df['fee_eth'][-1]
            fee_usd = local_state_df['Fee'][i] * ref_prices['{}.usdt'.format(symbol_dict['quote'])] + state_pnl_df['fee_usd'][-1]
            traded_btc = abs(amount) * ref_prices['{}.btc'.format(symbol_dict['base'])] + state_pnl_df['traded_btc'][-1]
            traded_eth = abs(amount) * ref_prices['{}.eth'.format(symbol_dict['base'])] + state_pnl_df['traded_eth'][-1]
            traded_usd = abs(amount) * ref_prices['{}.usdt'.format(symbol_dict['base'])] + state_pnl_df['traded_usd'][-1]
            while ts in state_pnl_df.index:
                ts += dt.timedelta(seconds = 0.0001)
            state_pnl_df.loc[ts] = {
                                'amount'         : amount,
                                'fill_price'     : fill_price,
                                'ave_fill_price' : ave_fill_price,
                                'position'       : cur_pos,
                                'mkt_price'      : mkt_price,
                                'pnl_btc'        : pnl_btc,
                                'pnl_eth'        : pnl_eth,
                                'pnl_usd'        : pnl_usd,
                                'realized_pnl_btc'   : realized_pnl_btc,
                                'realized_pnl_eth'   : realized_pnl_eth,
                                'realized_pnl_usd'   : realized_pnl_usd,
                                'unrealized_pnl_btc' : unrealized_pnl_btc,
                                'unrealized_pnl_eth' : unrealized_pnl_eth,
                                'unrealized_pnl_usd' : unrealized_pnl_usd,
                                'fee_btc'     : fee_btc,
                                'fee_eth'     : fee_eth,
                                'fee_usd'     : fee_usd,
                                'traded_btc'  : traded_btc,
                                'traded_eth'  : traded_eth,
                                'traded_usd'  : traded_usd
                                }

        if state_pnl_df.index[-1] < local_algo_df.index[-1]:
            ts = local_algo_df.index[-1]
            state_pnl_df.loc[ts] = state_pnl_df.iloc[-1]
            state_pnl_df['amount'].iloc[-1] = 0
            state_pnl_df['fill_price'].iloc[-1] = np.nan
            mkt_price = local_algo_df['last_sale_price'][-1]
            state_pnl_df['mkt_price'].iloc[-1] = mkt_price
            unrealized_pnl = state_pnl_df['position'][-1] * (mkt_price - state_pnl_df['ave_fill_price'][-1])
            state_pnl_df['unrealized_pnl_btc'].iloc[-1] = unrealized_pnl * ref_prices['{}.btc'.format(symbol_dict['quote'])]
            state_pnl_df['unrealized_pnl_eth'].iloc[-1] = unrealized_pnl * ref_prices['{}.eth'.format(symbol_dict['quote'])]
            state_pnl_df['unrealized_pnl_usd'].iloc[-1] = unrealized_pnl * ref_prices['{}.usdt'.format(symbol_dict['quote'])]
            state_pnl_df['pnl_btc'].iloc[-1] = state_pnl_df['realized_pnl_btc'][-1] + state_pnl_df['unrealized_pnl_btc'][-1]
            state_pnl_df['pnl_eth'].iloc[-1] = state_pnl_df['realized_pnl_eth'][-1] + state_pnl_df['unrealized_pnl_eth'][-1]
            state_pnl_df['pnl_usd'].iloc[-1] = state_pnl_df['realized_pnl_usd'][-1] + state_pnl_df['unrealized_pnl_usd'][-1]

        return state_pnl_df

    def _get_pre_position_from_statement_df(self, binance_symbol, end_dt):
        df = self.statement_df[self.statement_df['Market'] == binance_symbol]
        df = df[df.index <= end_dt]
        if len(df) == 0:
            return 0
        sell_amount = df[df['Type'] == 'SELL']['Amount'].sum()
        buy_amount  = df[df['Type'] == 'BUY']['Amount'].sum()
        position = buy_amount - sell_amount
        return position

    def _get_ave_fill_price_from_statement_df(self, binance_symbol, position, end_dt):
        if position == 0:
            return np.nan
        df = self.statement_df[self.statement_df['Market'] == binance_symbol]
        df = df[df.index <= end_dt]
        if len(df) == 0:
            raise Exception('wrong binance_statement_df')
        # go through df backward, calculate ave_fill_price till position
        agg_pos   = 0
        agg_value = 0
        residual_bought = 0
        residual_sold   = 0
        for i in range(len(df))[::-1]:
            amount = df['Amount'][i]
            if df['Type'][i] == 'SELL':
                amount *= -1
            agg_pos += amount

            price  = df['Price'][i]
            if position > 0:
                if residual_sold == 0:
                    if amount > 0:
                        if agg_pos >= position:
                            agg_value += (amount - (agg_pos - position)) * price
                            break
                        else:
                            agg_value += amount * price
                    elif amount < 0:
                        residual_sold += amount
                else: # residual_sold != 0
                    if amount > 0:
                        if amount + residual_sold >= 0:
                            agg_value += (amount + residual_sold) * price
                            residual_sold = 0
                        else:
                            residual_sold += amount
                    elif amount < 0:
                        residual_sold += amount
            else: # position < 0
                if residual_bought == 0:
                    if amount > 0:
                        residual_bought += amount
                    elif amount < 0:
                        if agg_pos <= position:
                            agg_value += (amount - (agg_pos - position)) * price
                            break
                        else:
                            agg_value += amount * price
                else: #residual_bought != 0
                    if amount > 0:
                        residual_bought += amount
                    elif amount < 0:
                        if amount + residual_bought <= 0:
                            agg_value += (amount + residual_bought) * price
                            residual_bought = 0
                        else:
                            residual_bought += amount
        if (position > 0 and position - agg_pos > 1e-6) \
        or (position < 0 and position - agg_pos < -1e-6):
            raise Exception('insufficient binance_statement_df')

        return agg_value / position

    def mark_by_cc_price(self, symbol, start, end, overwrite = False):
        symbol_dict = self._format_symbol(symbol)
        hourly_data = self._get_cc_hourly_data(symbol, start - dt.timedelta(hours = 3), end + dt.timedelta(hours = 3))
        if hourly_data is None or len(hourly_data) == 0:
            raise Exception('failed to get cc hourly data for date range {} ~ {}'.format(start, end))

        folder = os.path.join(self.output_folder, symbol_dict['dot'])
        if not os.path.exists(folder):
            os.makedirs(folder)
        pre_file = '{}_statement_{}.csv'.format(symbol_dict['dot'], (start - dt.timedelta(days = 1)).date())
        if os.path.exists(os.path.join(folder, pre_file)):
            pre_df = pd.read_csv(os.path.join(folder, pre_file), index_col = 0, header = 0, parse_dates = True)
            pre_pos = pre_df['position'][-1]
            pre_ave_price = pre_df['ave_fill_price'][-1]
            pre_mkt_price = pre_df['mkt_price'][-1]
            # fill_price = pre_mkt_price
            mkt_price = pre_mkt_price
        else:
            pre_end_ts = start
            pre_pos = self._get_pre_position_from_statement_df(symbol_dict['binance'], pre_end_ts)
            pre_ave_price = self._get_ave_fill_price_from_statement_df(symbol_dict['binance'], pre_pos, pre_end_ts)
            pre_mkt_price = hourly_data[hourly_data.index <= pre_end_ts]['close'][-1]
            mkt_price = pre_mkt_price
            # fill_price = np.nan

        state_pnl_df = pd.DataFrame({
                                      'amount'         : 0,
                                      'fill_price'     : np.nan,
                                      'ave_fill_price' : pre_ave_price,
                                      'position'       : pre_pos,
                                      'mkt_price'      : pre_mkt_price,
                                      'pnl_btc'        : 0,
                                      'pnl_eth'        : 0,
                                      'pnl_usd'        : 0,
                                      'net_btc'        : 0,
                                      'net_eth'        : 0,
                                      'net_usd'        : 0,
                                      'realized_pnl_btc'   : 0,
                                      'realized_pnl_eth'   : 0,
                                      'realized_pnl_usd'   : 0,
                                      'unrealized_pnl_btc' : 0,
                                      'unrealized_pnl_eth' : 0,
                                      'unrealized_pnl_usd' : 0,
                                      'fee_btc'     : 0,
                                      'fee_eth'     : 0,
                                      'fee_usd'     : 0,
                                      'traded_btc'  : 0,
                                      'traded_eth'  : 0,
                                      'traded_usd'  : 0
                                    }, index = [start])

        local_state_df = self.statement_df[
                                           (self.statement_df.index >= start) & 
                                           (self.statement_df.index <= end) &
                                           (self.statement_df['Market'] == symbol_dict['binance'])
                                           ].copy()
        ref_symbols = self._get_pair_vs_common_coins(symbol_dict['quote']) \
                    + self._get_pair_vs_common_coins(symbol_dict['base']) \
                    + self._get_pair_vs_common_coins('bnb')
        ref_symbols = list(set(ref_symbols))
        ref_prices  = self._get_conversion_prices(ref_symbols, dt.datetime.combine(start.date() + dt.timedelta(days = 1), dt.time(0,0)))
        for i in range(len(local_state_df)):
            ts = local_state_df.index[i]
            if i > 1:
                pre_ts = local_state_df.index[i-1]
                if ts.date() - pre_ts.date() > dt.timedelta(days = 0):
                    ref_prices  = self._get_conversion_prices(
                                                              ref_symbols, 
                                                              dt.datetime.combine(ts.date() + dt.timedelta(days = 1), dt.time(0,0))
                                                              )
            amount = local_state_df['Amount'][i]
            if local_state_df['Type'][i] == 'SELL':
                amount *= -1
            pre_ave_price = state_pnl_df['ave_fill_price'][-1]
            fill_price     = local_state_df['Price'][i]
            pre_pos = state_pnl_df['position'][-1]
            cur_pos = pre_pos + amount
            pre_mkt_price = state_pnl_df['mkt_price'][-1]
            # if fill_price > 0:
            #   mkt_price = fill_price
            # else:
            #   mkt_price = hourly_data[hourly_data.index <= ts]['close'][-1]
            mkt_price = hourly_data[hourly_data.index < ts + dt.timedelta(minutes = 30)]['close'][-1]

            if pre_pos == 0:
                # fill_price / mkt_price remains
                ave_fill_price = fill_price
                pnl_realized = 0
            elif pre_pos * amount >= 0:
                # adding positions
                ave_fill_price = (pre_pos * pre_ave_price + amount * fill_price) / (pre_pos + amount)
                pnl_realized = 0
            else:
                # reducing positions:
                if cur_pos == 0:
                    # flat
                    pnl_realized = amount * (pre_ave_price - fill_price)
                    ave_fill_price = np.nan
                elif cur_pos * pre_pos > 0:
                    # reduced but not flat
                    pnl_realized = amount * (pre_ave_price - fill_price)
                    ave_fill_price = pre_ave_price
                else:
                    # position flipped
                    ave_fill_price = fill_price
                    pnl_realized = pre_pos * (fill_price - pre_ave_price)
            pnl_unrealized = cur_pos * (mkt_price - ave_fill_price)
            if not pnl_unrealized or np.isnan(pnl_unrealized):
                pnl_unrealized = 0
            realized_pnl_btc   = pnl_realized * ref_prices['{}.btc'.format(symbol_dict['quote'])] + state_pnl_df['realized_pnl_btc'][-1]
            realized_pnl_eth   = pnl_realized * ref_prices['{}.eth'.format(symbol_dict['quote'])] + state_pnl_df['realized_pnl_eth'][-1]
            realized_pnl_usd   = pnl_realized * ref_prices['{}.usdt'.format(symbol_dict['quote'])] + state_pnl_df['realized_pnl_usd'][-1]
            unrealized_pnl_btc = pnl_unrealized * ref_prices['{}.btc'.format(symbol_dict['quote'])]
            unrealized_pnl_eth = pnl_unrealized * ref_prices['{}.eth'.format(symbol_dict['quote'])]
            unrealized_pnl_usd = pnl_unrealized * ref_prices['{}.usdt'.format(symbol_dict['quote'])]
            pnl_btc = realized_pnl_btc + unrealized_pnl_btc
            pnl_eth = realized_pnl_eth + unrealized_pnl_eth
            pnl_usd = realized_pnl_usd + unrealized_pnl_usd
            fee_btc = local_state_df['Fee'][i] * ref_prices['{}.btc'.format(local_state_df['Fee Coin'][i].lower())] + state_pnl_df['fee_btc'][-1]
            fee_eth = local_state_df['Fee'][i] * ref_prices['{}.eth'.format(local_state_df['Fee Coin'][i].lower())] + state_pnl_df['fee_eth'][-1]
            fee_usd = local_state_df['Fee'][i] * ref_prices['{}.usdt'.format(local_state_df['Fee Coin'][i].lower())] + state_pnl_df['fee_usd'][-1]
            traded_btc = abs(amount) * ref_prices['{}.btc'.format(symbol_dict['base'])] + state_pnl_df['traded_btc'][-1]
            traded_eth = abs(amount) * ref_prices['{}.eth'.format(symbol_dict['base'])] + state_pnl_df['traded_eth'][-1]
            traded_usd = abs(amount) * ref_prices['{}.usdt'.format(symbol_dict['base'])] + state_pnl_df['traded_usd'][-1]
            while ts in state_pnl_df.index:
                ts += dt.timedelta(seconds = 0.0001)
            state_pnl_df.loc[ts] = {
                                'amount'         : amount,
                                'fill_price'     : fill_price,
                                'ave_fill_price' : ave_fill_price,
                                'position'       : cur_pos,
                                'mkt_price'      : mkt_price,
                                'pnl_btc'        : pnl_btc,
                                'pnl_eth'        : pnl_eth,
                                'pnl_usd'        : pnl_usd,
                                'net_btc'        : pnl_btc - fee_btc,
                                'net_eth'        : pnl_eth - fee_eth,
                                'net_usd'        : pnl_usd - fee_usd,
                                'realized_pnl_btc'   : realized_pnl_btc,
                                'realized_pnl_eth'   : realized_pnl_eth,
                                'realized_pnl_usd'   : realized_pnl_usd,
                                'unrealized_pnl_btc' : unrealized_pnl_btc,
                                'unrealized_pnl_eth' : unrealized_pnl_eth,
                                'unrealized_pnl_usd' : unrealized_pnl_usd,
                                'fee_btc'     : fee_btc,
                                'fee_eth'     : fee_eth,
                                'fee_usd'     : fee_usd,
                                'traded_btc'  : traded_btc,
                                'traded_eth'  : traded_eth,
                                'traded_usd'  : traded_usd
                                }

        if state_pnl_df.index[-1] < end:
            ts = end
            state_pnl_df.loc[ts] = state_pnl_df.iloc[-1]
            state_pnl_df['amount'].iloc[-1] = 0
            state_pnl_df['fill_price'].iloc[-1] = np.nan
            # if fill_price > 0:
            #   mkt_price = fill_price
            # else:
            #   mkt_price = hourly_data[hourly_data.index <= ts]['close'][-1]
            mkt_price = hourly_data[hourly_data.index <= ts]['close'][-1]
            state_pnl_df['mkt_price'].iloc[-1] = mkt_price
            unrealized_pnl = state_pnl_df['position'][-1] * (mkt_price - state_pnl_df['ave_fill_price'][-1])
            state_pnl_df['unrealized_pnl_btc'].iloc[-1] = unrealized_pnl * ref_prices['{}.btc'.format(symbol_dict['quote'])]
            state_pnl_df['unrealized_pnl_eth'].iloc[-1] = unrealized_pnl * ref_prices['{}.eth'.format(symbol_dict['quote'])]
            state_pnl_df['unrealized_pnl_usd'].iloc[-1] = unrealized_pnl * ref_prices['{}.usdt'.format(symbol_dict['quote'])]
            state_pnl_df['pnl_btc'].iloc[-1] = state_pnl_df['realized_pnl_btc'][-1] + state_pnl_df['unrealized_pnl_btc'][-1]
            state_pnl_df['pnl_eth'].iloc[-1] = state_pnl_df['realized_pnl_eth'][-1] + state_pnl_df['unrealized_pnl_eth'][-1]
            state_pnl_df['pnl_usd'].iloc[-1] = state_pnl_df['realized_pnl_usd'][-1] + state_pnl_df['unrealized_pnl_usd'][-1]

        return state_pnl_df

    def save_daily(self, symbol, start_date, end_date, overwrite = False):
        symbol_dict = self._format_symbol(symbol)
        folder = os.path.join(self.output_folder, symbol_dict['dot'])
        eod = start_date
        summary_df = None
        while eod <= end_date:
            f = '{}_statement_{}.csv'.format(symbol_dict['dot'], eod)
            if os.path.exists(os.path.join(folder, f)) and not overwrite:
                df = pd.read_csv(os.path.join(folder, f), index_col = 0, header = 0, parse_dates = True)
            else:
                start = dt.datetime.combine(eod, dt.time(0,0))
                end   = start + dt.timedelta(days = 1) - dt.timedelta(seconds = 1)
                df = self.mark_by_cc_price(symbol, start, end)
                df.to_csv(os.path.join(folder, f))
            if summary_df is None:
                summary_df = pd.DataFrame([list(df.iloc[-1])], index = [eod], columns = df.columns)
            else:
                summary_df.loc[eod] = df.iloc[-1]
            summary_df.loc[eod]['amount'] = df['amount'].abs().sum()
            eod += dt.timedelta(days = 1)
        if summary_df is not None:
            summary_df['agg_pnl_btc'] = np.nan
            summary_df['agg_pnl_eth'] = np.nan
            summary_df['agg_pnl_usd'] = np.nan
            for i in range(len(summary_df)):
                summary_df['agg_pnl_btc'].iloc[i] = summary_df['realized_pnl_btc'][:i+1].sum() + summary_df['unrealized_pnl_btc'][i]
                summary_df['agg_pnl_eth'].iloc[i] = summary_df['realized_pnl_eth'][:i+1].sum() + summary_df['unrealized_pnl_eth'][i]
                summary_df['agg_pnl_usd'].iloc[i] = summary_df['realized_pnl_usd'][:i+1].sum() + summary_df['unrealized_pnl_usd'][i]
            summary_df['agg_net_btc'] = summary_df['agg_pnl_btc'] - summary_df['fee_btc'].cumsum()
            summary_df['agg_net_eth'] = summary_df['agg_pnl_eth'] - summary_df['fee_eth'].cumsum()
            summary_df['agg_net_usd'] = summary_df['agg_pnl_usd'] - summary_df['fee_usd'].cumsum()
            summary_df.to_csv(os.path.join(folder, '{}_daily_statement.csv'.format(symbol_dict['dot'])))
        return summary_df

    def get_portfolio_df(self, symbol_list, quote_coin, start, end):
        stat_df = pd.DataFrame(columns = ['day', 'net', 'pnl', 'sharpe', 'winrate', 'dd'], index = symbol_list)
        portfolio_pnl = pd.DataFrame()
        portfolio_net = pd.DataFrame()
        portfolio_columns = []
        for symbol in symbol_list:
            symbol_dict = self._format_symbol(symbol)
            f = os.path.join(self.output_folder, '{0}/{0}_daily_statement.csv'.format(symbol_dict['dot']))
            if not os.path.exists(f):
                continue
            df = pd.read_csv(f, header = 0, index_col = 0, parse_dates = True)
            df = df[(df.index >= start) & (df.index <= end)]
            if quote_coin.lower() == 'btc':
                pnl = df['realized_pnl_btc']
                net = pnl - df['fee_btc']
                
            elif quote_coin.lower() == 'eth':
                pnl = df['realized_pnl_eth']
                net = pnl - df['fee_eth']
            else:
                pnl = df['realized_pnl_usd']
                net = pnl - df['fee_usd']
            portfolio_net = pd.concat([portfolio_net, net], axis = 1)
            portfolio_pnl = pd.concat([portfolio_pnl, pnl], axis = 1)
            portfolio_columns.append(symbol)
        portfolio_net.columns = portfolio_columns
        portfolio_pnl.columns = portfolio_columns
        agg_net = portfolio_net.sum(axis = 1)
        agg_pnl = portfolio_pnl.sum(axis = 1)
        portfolio_net['aggregate'] = agg_net
        portfolio_pnl['aggregate'] = agg_pnl
        return {'net': portfolio_net, 'pnl': portfolio_pnl}

    def get_statistics(self, net_df, pnl_df):
        stat_df = pd.DataFrame(index = net_df.columns, columns = ['day', 'net', 'pnl', 'sharpe', 'winrate', 'dd'])
        for symbol in net_df.columns:
            net = net_df[symbol]
            pnl = pnl_df[symbol]
            day = len(net[net != 0])
            sharpe = np.mean(net) / np.std(net) if np.std(net) != 0 else np.nan
            winrate = len(net[net > 0]) / day if day != 0 else np.nan
            stat_df.loc[symbol] = [day, net.sum(), pnl.sum(), sharpe, winrate, net.min()]
        return stat_df

    def plot(self, net_df, pnl_df, quote_coin = None, save_to = None):
        plt.figure(figsize = (8, 12))
        n_col = 2
        n_row = int(np.ceil(net_df.shape[1] / n_col))
        i = 1
        for symbol in net_df.columns:
            plt.subplot(n_row, n_col, i)
            plt.plot(net_df.index, net_df[symbol].cumsum(), 'b')
            plt.plot(pnl_df.index, pnl_df[symbol].cumsum(), 'r--')
            plt.title(symbol)
            if quote_coin is not None:
                plt.ylabel('pnl_{}'.format(quote_coin))
            plt.xticks(rotation = 60)
            plt.grid()
            i += 1
        plt.tight_layout()
        if save_to is not None:
            plt.savefig(save_to, dpi = 300)
        else:
            plt.show()


class ccxt_trades:
    def __init__(self, exchange_str):
        self.exchange_str = exchange_str
        self.auth_file = r'C:\Users\Penny\.catalyst\data\exchanges\{}\auth.json'.format(self.exchange_str.lower())
        self.key_secret = self._get_api_key()
        self.ccxt_exchange = self._get_ccxt_exchange()

    def _get_api_key(self):
        if not os.path.exists(self.auth_file):
            return None
        with open(self.auth_file) as f:
            jdata = json.load(f)
        key = jdata['key']
        secret = jdata['secret']
        return {'key': key, 'secret': secret}

    def _get_ccxt_exchange(self):
        if self.exchange_str == 'huobipro':
            exchange = ccxt.huobipro({
                                    "apiKey": self.key_secret['key'],
                                    "secret": self.key_secret['secret'],
                                    "password": "",
                                    "enableRateLimit": True
                                })
            return exchange
        return None

    def get_ccxt_trades(self, symbol = None, since = None, limit = None, params = {}):
        # if self.ccxt_exchange.has('fetchMyTrades'):
        try:
            raw_trades = self.ccxt_exchange.fetch_my_trades(symbol, since, limit, params)
            return raw_trades
        except:
            return None

    def _get_huobipro_trade_df(self, symbol = None, since = None, limit = None, params = {}):
        raw_trades = self.get_ccxt_trades(symbol, since, limit, params)
        if raw_trades is None or len(raw_trades) == 0:
            return None
        df = pd.DataFrame(columns = ['Market', 'Type', 'Price', 'Amount', 'Total', 'Fee', 'Fee Coin'])
        for trade in raw_trades:
            ts = dt.datetime.utcfromtimestamp(trade['timestamp'] / 1000)
            df.loc[ts] = [trade['info']['symbol'].upper(), trade['side'].upper(), trade['price'], trade['amount'], 
                          trade['price'] * trade['amount'], trade['fee']['cost'], trade['fee']['currency']]
        return df

    def get_trade_df(self, symbol = None, since = None, limit = None, params = {}):
        if self.exchange_str == 'huobipro':
            return self._get_huobipro_trade_df(symbol, since, limit, params)
        return None


# my_trade = ccxt_trades('huobipro')            
# print(my_trade.get_trade_df())
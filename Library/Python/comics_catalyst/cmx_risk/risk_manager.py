import numpy as np
import pandas as pd
import logging
import datetime as dt
import os
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
import sys
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_crypto_compare'))
import hist_data

class base_risk:
    def __init__(self, context):
        self.context = context
        self.ts = None

    def update(self, data):
        self.ts = data.current_dt
        return True

class multileg_risk:
    def __init__(self, context):
        self.context = context
        self.ts = self.context.cmx_signal.ts
        self.prices = self.context.cmx_invent.prices
        self.leg_num = self.context.cmx_config.leg_num
        self.leg_pnls = [0] * self.leg_num
        self.leg_realized_pnls = [0] * self.leg_num
        self.leg_unrealized_pnls = [0] * self.leg_num
        self.positions = self.context.cmx_invent.positions
        self.pre_positions = self.context.cmx_invent.pre_positions
        self.amounts = self.context.cmx_invent.amounts
        self.traded_positions = self.context.cmx_invent.trade_positions
        self.traded_amounts = self.context.cmx_invent.trade_amounts
        self.pnl = 0

        self.daily_init_leg_pnls = [0] * self.leg_num
        self.daily_end_leg_pnls  = [0] * self.leg_num
        self.daily_min_leg_pnls  = [0] * self.leg_num
        self.daily_init_pnl      = 0
        self.daily_end_pnl       = 0
        self.daily_min_pnl       = 0
        self.daily_init_positions = [np.nan] * self.leg_num
        self.daily_end_positions  = self.positions
        self.daily_max_positions  = [0] * self.leg_num
        self.daily_min_positions  = [0] * self.leg_num
        self.daily_init_trade_positions = [0] * self.leg_num
        self.daily_end_trade_positions  = [0] * self.leg_num
        self.daily_init_amounts = [np.nan] * self.leg_num
        self.daily_end_amounts  = self.amounts
        self.daily_max_amounts  = [0] * self.leg_num
        self.daily_min_amounts  = [0] * self.leg_num
        self.daily_init_trade_amounts = [0] * self.leg_num
        self.daily_end_trade_amounts  = [0] * self.leg_num

    def update(self):
        self.ts = self.context.cmx_signal.ts
        # self.prices = self.context.cmx_invent.prices
        # self.positions = self.context.cmx_invent.positions
        # self.amounts = self.context.cmx_invent.amounts
        # self.traded_positions = self.context.cmx_invent.trade_positions
        self.pnl = self.context.portfolio.pnl
        self.daily_end_pnl = self.pnl - self.daily_init_pnl
        self.daily_min_pnl = min(self.daily_min_pnl, self.daily_end_pnl)
        # self.daily_end_positions = self.positions
        # self.daily_end_positions = self.amounts

        for i in range(self.leg_num):
            asset = self.context.cmx_config.catalyst_symbols[i]
            self.daily_end_leg_pnls[i] = self.leg_pnls[i] - self.daily_init_leg_pnls[i]
            self.daily_min_leg_pnls[i] = min(self.daily_min_leg_pnls[i], self.daily_end_leg_pnls[i])
            self.daily_max_positions[i] = max(self.daily_max_positions[i], self.daily_end_positions[i])
            self.daily_min_positions[i] = min(self.daily_min_positions[i], self.daily_end_positions[i])
            self.daily_max_positions[i] = max(self.daily_max_positions[i], self.daily_end_positions[i])
            self.daily_min_positions[i] = min(self.daily_min_positions[i], self.daily_end_positions[i])
            self.daily_end_trade_positions[i] = self.traded_positions[i] - self.daily_init_trade_positions[i]

            self.daily_max_amounts[i] = max(self.daily_max_amounts[i], self.daily_end_amounts[i])
            self.daily_min_amounts[i] = min(self.daily_min_amounts[i], self.daily_end_amounts[i])
            self.daily_max_amounts[i] = max(self.daily_max_amounts[i], self.daily_end_amounts[i])
            self.daily_min_amounts[i] = min(self.daily_min_amounts[i], self.daily_end_amounts[i])
            self.daily_end_trade_amounts[i] = self.traded_amounts[i] - self.daily_init_trade_amounts[i]
            logging.info('[cmx_risk] update {} risk at {}: price = {}|pnl = {}|position = {}|amount = {}|traded = {}'.format(
                                                                                    asset.symbol,
                                                                                    self.ts,
                                                                                    self.prices[i],
                                                                                    self.leg_pnls[i],
                                                                                    self.positions[i],
                                                                                    self.amounts[i],
                                                                                    self.traded_positions[i]
                                                                                        ))
        # self.pnl = np.sum(self.leg_pnls)
        logging.info('[cmx_risk] update risk at {}: pnl = {}'.format(self.ts, self.pnl))

    def update_daily(self):
        self.daily_init_leg_pnls = self.leg_pnls.copy()
        self.daily_end_leg_pnls  = [0] * self.leg_num
        self.daily_min_leg_pnls  = [0] * self.leg_num
        self.daily_init_pnl      = self.pnl
        self.daily_end_pnl       = 0
        self.daily_min_pnl       = 0
        self.daily_init_positions = self.daily_end_positions.copy()
        self.daily_end_positions  = self.positions
        self.daily_max_positions  = [0] * self.leg_num
        self.daily_min_positions  = [0] * self.leg_num
        self.daily_init_trade_positions = self.daily_end_trade_positions.copy()
        self.daily_end_trade_positions  = [np.nan] * self.leg_num
        self.daily_init_amounts = self.daily_end_amounts.copy()
        self.daily_end_amounts  = self.amounts
        self.daily_max_amounts  = [0] * self.leg_num
        self.daily_min_amounts  = [0] * self.leg_num
        self.daily_init_trade_amounts =self.daily_end_trade_amounts.copy()
        self.daily_end_trade_amounts  = [np.nan] * self.leg_num

    def run(self):
        self.update()

class trade_monitor:
    def __init__(self, context):
        self.context = context
        self.trade_df = pd.DataFrame()
        self.ts = None
        self.eod = None
        self.new_trade_df = pd.DataFrame()
        self.position = 0
        self.cost_basis = 0
        self.realized_pnl = 0

    def bootstrap(self, ts = None, position = 0, cost_basis = 0):
        # read trade_df from .trade.csv
        self.ts = ts
        self.position = position
        self.cost_basis = cost_basis
        if self.ts:
            self.eod = self.ts.date()            
            trade_file = '{}_{}.trade.csv'.format(self.context.cmx_recorder.file_prefix, self.eod)
            trade_path = os.path.join(self.context.trade_path, trade_file)
            if os.path.exists(trade_path):
                self.trade_df = pd.read_csv(trade_path, header = 0, index_col = 0, parse_dates = True)

    def _get_new_trade_df(self):
        processed_transaction_dict = self.context.perf_tracker.todays_performance.processed_transactions
        logging.debug('[cmx_risk] processed_transaction_dict: {}'.format(processed_transaction_dict))
        self.new_trade_df = pd.DataFrame(columns = ['symbol', 'side', 'price', 'amount', 'fee', 'fee_coin', 'position', 'cost_basis'])
        t0 = dt.datetime.combine(self.eod, dt.time(0,0))
        if self.trade_df is not None and len(self.trade_df) > 0:
            t0 = self.trade_df.index[-1]

        for ts, transactions in processed_transaction_dict.items():
            ts = ts.replace(tzinfo = None)
            if ts > t0:
                for tran in transactions:
                    symbol = tran['asset'].symbol
                    price  = tran['price']
                    amount = tran['amount']
                    fee    = tran['commission']
                    fee_coin = tran['fee_currency'] if tran['fee_currency'] is not None else tran['asset'].quote_currency
                    self._process_trade(tran)
                    cur_df = pd.DataFrame({
                                           'symbol': symbol, 
                                           'side'  : 'BUY' if amount > 0 else 'SELL', 
                                           'price' : price, 
                                           'amount': amount, 
                                           'fee'   : fee, 
                                           'fee_coin' : fee_coin,
                                           'position' : self.position,
                                           'cost_basis': self.cost_basis
                                           }, index = [ts])
                    self.new_trade_df = self.new_trade_df.append(cur_df)
        self.new_trade_df.sort_index(inplace = True)
        return self.new_trade_df

    def _process_trade(self, txn):
        price = txn['price']
        amount = txn['amount']

        if self.cost_basis is None:
            self.cost_basis = price
        else:
            if self.position * amount > 0:
                self.cost_basis = (self.cost_basis * self.position + price * amount) / (self.position + amount)
            else:
                if abs(amount) <= abs(self.position):
                    self.realized_pnl += (price - self.cost_basis) * amount * (-1)
                else:
                    self.realized_pnl += (price - self.cost_basis) * self.position
                    self.cost_basis = price
        self.position += amount

    def update(self):
        self.ts = self.context.cmx_signal.ts
        if self.ts is None:
            return False
        if self.ts.date() != self.eod:
            self.eod = self.ts.date()
            self.trade_df = pd.DataFrame()
            self.new_trade_df = pd.DataFrame()
            self.realized_pnl = 0
            logging.info('[cmx_risk] eod changed. Reset all trade DFs.')

        self._get_new_trade_df()
        if len(self.new_trade_df) > 0:
            self.trade_df = pd.concat([self.trade_df, self.new_trade_df])
            logging.info('[cmx_risk] added new trades to DF.')
            logging.info(self.new_trade_df)
            
            return True
        return False


class outright_risk:
    def __init__(self, context):
        self.init_ts = None
        self.init_position = 0
        self.init_cost_basis = 0
        self.init_realized = 0
        self.init_unrealized_offset = 0
        self.init_fee = 0
        self.init_traded = 0

        self.context = context
        self.trade_monitor = trade_monitor(self.context)
        self.ts  = None
        self.eod = None
        self.price = None
        self.pnl = 0 # in quote currency
        self.fee = 0
        self.net = 0
        self.realized = 0
        self.unrealized = 0
        self.unrealized_offset = 0
        self.cost_basis = 0
        self.position = 0
        self.base_pos = 0
        self.quote_pos= 0
        self.traded = 0
        self.trade_df = self.trade_monitor.trade_df
        self.new_trade_df = self.trade_monitor.new_trade_df

        self.daily_init_net = 0
        self.daily_end_net  = 0
        self.daily_min_net  = 0
        self.daily_init_position = self.position
        self.daily_end_position  = self.position
        self.daily_max_position  = self.position
        self.daily_min_position  = self.position
        self.daily_init_traded = 0
        self.daily_end_traded  = 0

        self.trading_enabled = True
        # self.require_exit = False
        self.trading_status = 'normal' # {'normal', 'exit_nonew', 'exit_passive', 'exit_active'}
        self.fee_refprice_map = {}

    def bootstrap(self):
        if self.context.global_mode == 'backtest':
            return False
        if not os.path.exists(self.context.pnl_stat_file):
            return False
        pnl_stat = pd.read_csv(self.context.pnl_stat_file, index_col = 0, header = 0, parse_dates = True).iloc[-1]
        self.init_ts = pnl_stat.name
        self.init_position   = pnl_stat.get('position') if pnl_stat.get('position') else 0
        self.init_cost_basis = pnl_stat.get('cost_basis') if pnl_stat.get('cost_basis') else 0
        self.init_realized   = pnl_stat.get('realized') if pnl_stat.get('realized') else 0
        self.init_unrealized_offset = pnl_stat.get('unrealized_offset') if pnl_stat.get('unrealized_offset') else 0
        self.init_fee      = pnl_stat.get('fee') if pnl_stat.get('fee') else 0
        self.init_traded   = pnl_stat.get('traded') if pnl_stat.get('traded') else 0
        self.trade_monitor.bootstrap(self.init_ts, self.init_position, self.init_cost_basis)
        logging.info('[cmx_risk] bootstrap completed: ts = {}|position = {}|cost_basis = {}|realized = {}|unrealized_offset = {}|fee = {}|traded = {}'.format(
                                                                                                                    self.init_ts,
                                                                                                                    self.init_position,
                                                                                                                    self.init_cost_basis,
                                                                                                                    self.init_realized,
                                                                                                                    self.init_unrealized_offset,
                                                                                                                    self.init_fee,
                                                                                                                    self.init_traded
                                                                                                                                                              ))
        logging.info('traded_df = \n{}'.format(self.trade_monitor.trade_df))

        self.position = self.init_position
        self.cost_basis = self.init_cost_basis
        self.unrealized_offset = self.init_unrealized_offset if self.init_unrealized_offset else 0
        self.daily_init_position = self.position
        self.daily_end_position  = self.position
        self.daily_max_position  = self.position
        self.daily_min_position  = self.position
        return True

    def save_pnl_stat(self):
        if self.context.global_mode == 'backtest':
            return False
        df = pd.DataFrame(columns = [
                                     'position', 
                                     'cost_basis', 
                                     'realized', 
                                     'unrealized_offset', 
                                     'fee', 
                                     'traded',
                                     'net',
                                     'price'
                                     ])
        df.loc[self.ts] = [
                           self.position, 
                           self.cost_basis, 
                           self.realized, 
                           self.unrealized_offset, 
                           self.fee, 
                           self.traded,
                           self.net,
                           self.price,
                           ]
        df.to_csv(self.context.pnl_stat_file)
        logging.info('[cmx_risk] saved pnl stat\n{}'.format(df))
        return True

    def adjust_position_limits(self, data):
        # acct_availables = self.context.cmx_account.available_balances
        # acct_base_pos = acct_availables[self.context.base_currency]
        # acct_quote_pos = acct_availables[self.context.quote_currency]
        # self.price = data.current(self.context.asset, 'price')
        # TODO: 
        # 1. adjust init position based on accout base position
        # acct_allowed_short_pos = -1 * acct_base_pos
        # if self.price > 0:
        #   acct_allowed_long_pos  = acct_quote_pos / self.price + acct_base_pos
        # else:
        #   acct_allowed_long_pos = acct_base_pos

        # adjusted = False
        # if acct_allowed_short_pos > self.context.risk_max_short_pos:
        #   self.context.risk_max_short_pos = acct_allowed_short_pos
        #   adjusted = True
        # if acct_allowed_long_pos < self.context.risk_max_long_pos:
        #   self.context.risk_max_long_pos = acct_allowed_long_pos
        #   adjusted = True
        # if adjusted:
        #   self.context.cmx_logger.log_risk_adjust()
        # return adjusted
        pass

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

    def _get_cc_hourly_data_by_exchange(self, exchange, symbol, start, end):
        sym_info = self._format_symbol(symbol)
        if (sym_info['base'] == 'usdt') \
        or (sym_info['base'] == 'btc' and sym_info['quote'] not in ['usdt']) \
        or (sym_info['base'] == 'eth' and sym_info['quote'] not in ['usdt', 'btc']) \
        or (sym_info['base'] == 'bnb' and sym_info['quote'] not in ['usdt', 'btc', 'eth']):
            hourly_data = 1 / hist_data.get_hourly_df(
                                                    sym_info['quote'].upper(), 
                                                    sym_info['base'].upper(), 
                                                    start, 
                                                    end,
                                                    exchange = exchange
                                                    )
        else:
            hourly_data = hist_data.get_hourly_df(
                                                sym_info['base'].upper(), 
                                                sym_info['quote'].upper(), 
                                                start, 
                                                end,
                                                exchange = exchange
                                                )
        return hourly_data

    def _get_cc_price(self, symbol):
        tn = self.ts.replace(tzinfo = None)
        t0 = tn - dt.timedelta(hours = 10)
        hourly_data = self._get_cc_hourly_data_by_exchange(
                                                           self.context.exchange_str, 
                                                           symbol, 
                                                           t0,
                                                           tn,
                                                           )
        if hourly_data is None:
            return None
        hourly_data.dropna(inplace = True)
        return hourly_data['close'][-1]

    def _convert_fee(self, fee, fee_coin):
        if fee_coin == self.context.asset.quote_currency:
            return fee
        if fee_coin == self.context.asset.base_currency:
            return fee * self.price
        symbol = '{}_{}'.format(fee_coin, self.context.asset.quote_currency)
        price = self.fee_refprice_map.get(symbol)
        if price:
            return fee * price
        else:
            price = self._get_cc_price(symbol)
            if price:
                self.fee_refprice_map[symbol] = price
                return fee * price
            logging.warning('[cmx_risk] failed to get {} price, ignoring trading fee'.format(symbol))
            print('WARNING! [cmx_risk] failed to get {} price, ignoring trading fee'.format(symbol))
            return 0

    def _convert_fees(self, trade_df):
        if trade_df is None or len(trade_df) == 0:
            return 0
        total_fee = 0
        for i in range(len(trade_df)):
            fee = trade_df['fee'][i]
            fee_coin = trade_df['fee_coin'][i]
            total_fee += self._convert_fee(fee, fee_coin)
        return total_fee

    def initialize_pnl_stat(self):
        bootstrapped = self.bootstrap()
        if bootstrapped:
            logging.info('[cmx_risk] initialized pnl stat: position = {}|cost_basis = {}|unrealized_offset = {}'.format(
                                                                                                            self.position,
                                                                                                            self.cost_basis,
                                                                                                            self.unrealized_offset
                                                                                                                        ))
            if self.ts.date() == self.init_ts.date():
                # restarted on the same day:
                self.realized = self.init_realized if self.init_realized else 0
                self.fee = self.init_fee if self.init_fee else 0
                self.traded = self.init_traded if self.init_traded else 0
                logging.info('[cmx_risk] initalized pnl stat on the same day: realized = {}|fee = {}'.format(self.realized, self.fee))
        return bootstrapped

    def update(self, data):
        self.ts = data.current_dt
        if self.ts is None:
            return False
        self.price = data.current(self.context.asset, 'price')
        if self.eod is None:
            # algo restarted
            self.eod = self.ts.date()
            self.initialize_pnl_stat()
        elif self.ts.date() != self.eod:
            self.eod = self.ts.date()
            self.reset_daily()

        trade_updated = self.trade_monitor.update()
        self.new_trade_df = self.trade_monitor.new_trade_df
        if trade_updated:
            self.trade_df = self.trade_monitor.trade_df
            self.position = self.trade_monitor.position
            self.cost_basis = self.trade_monitor.cost_basis
            self.fee += self._convert_fees(self.new_trade_df[['fee', 'fee_coin']])
            self.realized = self.trade_monitor.realized_pnl
            self.traded += self.new_trade_df['amount'].abs().sum()
            logging.info('[cmx_risk] new trade filled: pos = {}|cost_basis = {}|fee = {}|realized = {}|traded = {}'.format(
                                                                                                                           self.position,
                                                                                                                           self.cost_basis,
                                                                                                                           self.fee,
                                                                                                                           self.realized,
                                                                                                                           self.traded
                                                                                                                           ))

        if self.cost_basis is not None and self.position is not None:
            self.unrealized = (self.price - self.cost_basis) * self.position - self.unrealized_offset
        else:
            self.unrealized = - self.unrealized_offset
        self.pnl = self.realized + self.unrealized
        self.net = self.pnl - self.fee
        self.base_pos = self.position
        self.quote_pos = - self.base_pos * self.price if self.base_pos is not None else None
        logging.info('[cmx_risk] price updated: realized = {}|unrealized = {}|pnl = {}|net = {}|base_pos = {}|quote_pos = {}'.format(
                                                                                                       self.realized,
                                                                                                       self.unrealized,
                                                                                                       self.pnl,
                                                                                                       self.net,
                                                                                                       self.base_pos,
                                                                                                       self.quote_pos
                                                                                                       ))
        # self.save_pnl_stat()
        self.daily_end_net = self.net - self.daily_init_net
        self.daily_min_net = min(self.daily_min_net, self.daily_end_net)
        self.daily_end_position = self.position
        self.daily_max_position = max(self.daily_max_position, self.daily_end_position)
        self.daily_min_position = min(self.daily_min_position, self.daily_end_position)
        self.daily_end_traded = self.traded - self.daily_init_traded
        # Assert:
        catalyst_cost_basis = self.context.portfolio.positions[self.context.asset].cost_basis
        catalyst_position = self.context.portfolio.positions[self.context.asset].amount
        catalyst_pnl = self.context.portfolio.pnl
        if catalyst_position != self.position:
            logging.warning('[cmx_risk] position mismatch: catalyst = {} | cmx = {}'.format(catalyst_position, self.position))
        if catalyst_cost_basis != self.cost_basis:
            logging.warning('[cmx_risk] cost_basis mismatch: catalyst = {} | cmx = {}'.format(catalyst_cost_basis, self.cost_basis))
        if catalyst_pnl != self.net:
            logging.warning('[cmx_risk] pnl mismatch: catalyst = {} | cmx = {}'.format(catalyst_pnl, self.net))
        self.update_exit_status()
        return True

    def update_exit_status(self):
        if self.context.exit_active_dt and self.ts >= self.context.exit_active_dt:
            self.trading_status = 'exit_active'
            return
        if self.context.exit_passive_dt and self.ts >= self.context.exit_passive_dt:
            self.trading_status = 'exit_passive'
            return
        if self.context.exit_nonew_dt and self.ts >= self.context.exit_nonew_dt:
            self.trading_status = 'exit_nonew'
            return
        self.trading_status = 'normal'

    def reset_exit_status(self):
        self.require_exit = False

    def reset_daily(self):
        self.pnl = 0
        self.fee = 0
        self.net = 0
        self.realized = 0
        self.unrealized_offset += self.unrealized
        self.traded = 0
        logging.info('[cmx_risk] reset_daily: pnl = {}|net = {}|realize = {}|unrealized_offset = {}'.format(
                                                                                                            self.pnl,
                                                                                                            self.net,
                                                                                                            self.realized,
                                                                                                            self.unrealized_offset
                                                                                                            ))

        self.daily_init_net = 0
        self.daily_end_net  = 0
        self.daily_min_net  = 0
        self.daily_init_position = self.position
        self.daily_end_position  = self.position
        self.daily_max_position  = self.position
        self.daily_min_position  = self.position
        self.daily_init_traded = 0
        self.daily_end_traded  = 0

        self.init_position = self.position
        self.init_cost_basis = self.cost_basis
        self.fee_refprice_map = {}

    def run(self, data):
        self.update(data)


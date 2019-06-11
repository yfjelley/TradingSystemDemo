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

def format_symbol(symbol):
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

def get_cc_hourly_data_by_exchange(exchange, symbol, start, end):
    sym_info = format_symbol(symbol)
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

def get_cc_price(exchange, symbol, ts):
    tn = ts.replace(tzinfo = None)
    t0 = tn - dt.timedelta(hours = 10)
    hourly_data = get_cc_hourly_data_by_exchange(
                                                 exchange, 
                                                 symbol, 
                                                 t0,
                                                 tn,
                                                )
    if hourly_data is None:
        return None
    hourly_data.dropna(inplace = True)
    return hourly_data['close'][-1]

class leg_trade_monitor:
    def __init__(self, context, symbol):
        self.context = context
        self.symbol  = symbol
        self.ts = None
        self.eod = None
        self.trade_df = pd.DataFrame()
        self.new_trade_df = pd.DataFrame()
        self.position = 0
        self.cost_basis = 0
        self.realized_pnl = 0
        self.trade_path = None

    def bootstrap(self, ts = None, position = 0, cost_basis = 0, realized = 0):
        # read trade_df from .trade.csv
        self.ts = ts
        self.position = position
        self.cost_basis = cost_basis
        self.realized_pnl = realized
        if self.ts:
            self.eod = self.ts.date()
            self.trade_path = os.path.join(self.context.cmx_config.storage_trade_folder, self.context.cmx_config.storage_trade_file)
            if os.path.exists(self.trade_path):
                self.trade_df = pd.read_csv(self.trade_path, header = 0, index_col = 0, parse_dates = True)
                self.trade_df = self.trade_df[self.trade_df['symbol'] == self.symbol]
                return True
        return False

    def _get_new_trade_df(self):
        processed_transaction_dict = self.context.perf_tracker.todays_performance.processed_transactions
        logging.debug('[cmx_risk][leg_trade_monitor] processed_transaction_dict: {}'.format(processed_transaction_dict))
        self.new_trade_df = pd.DataFrame(columns = ['symbol', 'side', 'price', 'amount', 'fee', 'fee_coin', 'position', 'cost_basis'])
        t0 = dt.datetime.combine(self.eod, dt.time(0,0))
        if self.trade_df is not None and len(self.trade_df) > 0:
            t0 = self.trade_df.index[-1]

        for ts, transactions in processed_transaction_dict.items():
            ts = ts.replace(tzinfo = None)
            if ts > t0:
                for tran in transactions:
                    symbol = tran['asset'].symbol
                    if symbol == self.symbol:
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
            logging.info('[cmx_risk][leg_trade_monitor] eod changed. Reset all trade DFs.')

        self._get_new_trade_df()
        if len(self.new_trade_df) > 0:
            self.trade_df = pd.concat([self.trade_df, self.new_trade_df])
            logging.info('[cmx_risk][leg_trade_monitor] added new trades to DF.')
            logging.info(self.new_trade_df)
            return True
        return False

class leg_risk:
    def __init__(self, context, leg_index):
        self.context = context
        self.leg_index = leg_index
        self.exchange = self.context.cmx_config.global_exchanges[self.leg_index]
        self.symbol  = self.context.cmx_config.global_symbols[self.leg_index]
        self.trade_monitor = leg_trade_monitor(context, self.symbol)
        self.catalyst_asset = self.context.cmx_config.catalyst_assets[self.leg_index]
        self.quote_currency = self.context.cmx_config.risk_quote_currency

        self.init_ts = None
        self.init_position = 0
        self.init_cost_basis = 0
        self.init_realized = 0
        self.init_unrealized_offset = 0
        self.init_fee = 0
        self.init_traded = 0

        self.ts  = None
        self.eod = None
        self.price = None
        self.pnl = 0 # in quote currency
        #TODO: check anchor leg's self.pnl
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
        self.trading_status = 'normal' # {'normal', 'exit_nonew', 'exit_passive', 'exit_active'}
        self.fee_refprice_map = {}
        self.pnl_stat_path = None

    def reload_config(self, symbol):
        self.symbol  = symbol
        self.trade_monitor = leg_trade_monitor(self.context, symbol)
        self.leg_index = self.context.cmx_config.global_symbols.index(symbol)
        self.catalyst_asset = self.context.cmx_config.catalyst_assets[self.leg_index]
        self.quote_currency = self.context.cmx_config.risk_quote_currency

    def bootstrap(self):
        if self.context.cmx_config.global_mode == 'backtest':
            return False
        self.pnl_stat_path = os.path.join(self.context.cmx_config.storage_perf_stat_folder, self.context.cmx_config.storage_perf_stat_file)
        if not os.path.exists(self.pnl_stat_path):
            return False
        pnl_stat = pd.read_csv(self.pnl_stat_path, index_col = 0, header = 0, parse_dates = True).iloc[-1]
        self.init_ts = pnl_stat.name
        self.init_position   = pnl_stat.get('leg_pos')[self.leg_index] if pnl_stat.get('leg_pos') else 0
        self.init_cost_basis = pnl_stat.get('leg_cost')[self.leg_index] if pnl_stat.get('leg_cost') else 0
        self.init_realized   = pnl_stat.get('leg_realized')[self.leg_index] if pnl_stat.get('leg_realized') else 0
        self.init_unrealized_offset = pnl_stat.get('leg_unrealized_offset')[self.leg_index] if pnl_stat.get('leg_unrealized_offset') else 0
        self.init_fee        = pnl_stat.get('leg_fee')[self.leg_index] if pnl_stat.get('leg_fee') else 0
        self.init_traded     = pnl_stat.get('leg_traded')[self.leg_index] if pnl_stat.get('leg_traded') else 0
        self.trade_monitor.bootstrap(self.init_ts, self.init_position, self.init_cost_basis, self.init_realized)
        logging.info('[cmx_risk] bootstrap completed: ts = {}|symbol = {}|position = {}|cost_basis = {}|realized = {}|unrealized_offset = {}|fee = {}|traded = {}'.format(
                                                                                                                    self.init_ts,
                                                                                                                    self.symbol,
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

    def _convert_fee(self, fee, fee_coin):
        if not fee or not fee_coin:
            return 0
        if fee_coin == self.quote_currency:
            return fee
        
        symbol = '{}_{}'.format(fee_coin, self.quote_currency)
        price = self.fee_refprice_map.get(symbol)
        if price:
            return fee * price
        else:
            price = get_cc_price(symbol)
            if price:
                self.fee_refprice_map[symbol] = price
                return fee * price
            logging.warning('[cmx_risk][leg_risk] failed to get {} price, ignoring trading fee'.format(symbol))
            print('WARNING! [cmx_risk][leg_risk] failed to get {} price, ignoring trading fee'.format(symbol))
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
            logging.info('[cmx_risk][leg_risk] initialized pnl stat: symbol = {}|position = {}|cost_basis = {}|unrealized_offset = {}'.format(
                                                                                                            self.symbol,
                                                                                                            self.position,
                                                                                                            self.cost_basis,
                                                                                                            self.unrealized_offset
                                                                                                                        ))
            if self.ts.date() == self.init_ts.date():
                # restarted on the same day:
                self.realized = self.init_realized if self.init_realized else 0
                self.fee = self.init_fee if self.init_fee else 0
                self.traded = self.init_traded if self.init_traded else 0
                logging.info('[cmx_risk][leg_risk] initalized pnl stat on the same day: realized = {}|fee = {}'.format(self.realized, self.fee))
        return bootstrapped

    def update(self, data):
        self.ts = data.current_dt
        if self.ts is None:
            return False
        self.price = data.current(self.catalyst_asset, 'price')
        self.fee_refprice_map[self.symbol] = self.price
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
            self.base_pos = self.position
            if self.base_pos is not None and self.catalyst_asset.quote_currency == self.quote_currency:
                self.quote_pos = self.base_pos * self.price
            else:
                self.quote_pos = np.nan
            logging.info('[cmx_risk][leg_risk] new trade filled: symbol = {}|pos = {}|cost_basis = {}|fee = {}|realized = {}|traded = {}'.format(
                                                                                                                           self.symbol,
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
        logging.info('[cmx_risk][leg_risk] price updated: symbol = {}|realized = {}|unrealized = {}|pnl = {}|net = {}|base_pos = {}|quote_pos = {}'.format(
                                                                                                       self.symbol,
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
        catalyst_cost_basis = self.context.portfolio.positions[self.catalyst_asset].cost_basis
        catalyst_position = self.context.portfolio.positions[self.catalyst_asset].amount
        if catalyst_position != self.position:
            logging.info('[cmx_risk][leg_risk] {} position mismatch: catalyst = {}|cmx = {}'.format(self.symbol, catalyst_position, self.position))
        if catalyst_cost_basis != self.cost_basis:
            logging.info('[cmx_risk][leg_risk] {} cost_basis mismatch: catalyst = {}|cmx = {}'.format(self.symbol, catalyst_cost_basis, self.cost_basis))
        return True

    def reset_daily(self):
        self.pnl = 0
        self.fee = 0
        self.net = 0
        self.realized = 0
        self.unrealized_offset += self.unrealized
        self.traded = 0
        logging.info('[cmx_risk][leg_risk] reset_daily: symbol = {}|pnl = {}|net = {}|realize = {}|unrealized_offset = {}'.format(
                                                                                                            self.symbol,
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

class twoleg_risk:
    def __init__(self, context):
        self.context = context
        self.symbols = self.context.cmx_config.global_symbols
        self.leg_num = self.context.cmx_config.global_leg_num
        self.leg_risks = [leg_risk(self.context, i) for i in range(self.leg_num)]
        self.flat_quote_pos = (self.context.cmx_config.risk_max_notional + self.context.cmx_config.risk_min_notional) / 2

        self.init_ts = None
        # self.init_prices = None
        self.init_leg_positions = [0] * self.leg_num
        self.init_leg_costs = [0] * self.leg_num
        self.init_leg_realized_pnls = [0] * self.leg_num
        self.init_leg_unrealized_offsets = [0] * self.leg_num
        self.init_leg_fees = [0] * self.leg_num
        self.init_leg_traded_amounts = [0] * self.leg_num

        self.ts = self.context.cmx_signal.ts
        self.eod = None
        self.prices = self.context.cmx_signal.prices.copy()
        self.leg_pnls = [0] * self.leg_num
        self.leg_nets = [0] * self.leg_num
        self.leg_fees = [0] * self.leg_num
        self.leg_costs= [0] * self.leg_num
        self.leg_realized_pnls = [0] * self.leg_num
        self.leg_unrealized_pnls = [0] * self.leg_num
        self.leg_unrealized_offsets = [0] * self.leg_num
        self.leg_positions = [0] * self.leg_num
        self.leg_quote_positions = [0] * self.leg_num
        self.leg_pre_positions = [0] * self.leg_num
        self.leg_traded_amounts = [0] * self.leg_num
        self.leg_share_ratios = [0] * self.leg_num
        
        self.pnl = 0
        self.net = 0
        self.fee = 0
        self.realized = 0
        self.unrealized = 0
        self.position = 0
        self.unhedged = 0
        self.trade_df = pd.DataFrame()
        self.new_trade_df = pd.DataFrame()

        self.daily_init_net = 0
        self.daily_end_net  = 0
        self.daily_min_net  = 0
        self.daily_init_position = self.position
        self.daily_end_position  = self.position
        self.daily_max_position  = self.position
        self.daily_min_position  = self.position

        self.daily_init_leg_nets = [0] * self.leg_num
        self.daily_end_leg_nets  = [0] * self.leg_num
        self.daily_min_leg_nets  = [0] * self.leg_num
        self.daily_init_leg_positions = self.leg_positions.copy()
        self.daily_end_leg_positions  = self.leg_positions.copy()
        self.daily_max_leg_positions  = self.leg_positions.copy()
        self.daily_min_leg_positions  = self.leg_positions.copy()
        self.daily_init_leg_trade_amounts = [0] * self.leg_num
        self.daily_end_leg_trade_amounts  = [0] * self.leg_num
        
        self.trading_enabled = True
        self.trading_status = 'normal' # {'normal', 'hedge_only', 'exit_nonew', 'exit_passive', 'exit_active'}

    def reload_config(self):
        self.symbols = self.context.cmx_config.global_symbols
        self.leg_num = self.context.cmx_config.global_leg_num
        for i in range(self.leg_num):
            self.leg_risks[i].reload_config(i, self.symbols[i])

    def bootstrap(self):
        bootstrapped = True
        for i in range(self.leg_num):
            bootstrapped &= self.leg_risks[i].bootstrap()
            self.init_leg_positions[i] = self.leg_risks[i].init_position
            self.init_leg_costs[i]     = self.leg_risks[i].init_cost_basis
            self.init_leg_realized_pnls[i] = self.leg_risks[i].init_realized
            self.init_leg_unrealized_offsets[i] = self.leg_risks[i].init_unrealized_offset
            self.init_leg_fees[i]      = self.leg_risks[i].init_fee
            self.init_leg_traded_amounts[i] = self.leg_risks[i].init_traded

            self.leg_positions[i] = self.leg_risks[i].position
            self.leg_costs[i] = self.leg_risks[i].cost_basis
            self.leg_unrealized_offsets[i] = self.leg_risks[i].unrealized_offset

            self.daily_init_leg_positions[i] = self.leg_risks[i].daily_init_position
            self.daily_end_leg_positions[i] = self.leg_risks[i].daily_end_position
            self.daily_max_leg_positions[i] = self.leg_risks[i].daily_max_position
            self.daily_min_leg_positions[i] = self.leg_risks[i].daily_min_position

        self.init_ts = self.leg_risks[0].init_ts
        return bootstrapped

    def initialize_pnl_stat(self):
        bootstrapped = self.bootstrap()
        self.realized = 0
        self.fee = 0
        for i in range(self.leg_num):
            self.leg_realized_pnls[i] = self.leg_risks[i].realized
            self.leg_fees[i] = self.leg_risks[i].fee
            self.leg_traded_amounts[i] = self.leg_risks[i].traded
            self.realized += self.leg_realized_pnls[i]
            self.fee += self.leg_fees[i]
        return bootstrapped

    def update_share_ratios(self):
        # qpl = self.context.cmx_config.invent_share_per_level
        # for i in range(self.leg_num):
        #     self.leg_share_ratios[i] = qpl / self.init_prices[i] if self.init_prices[i] else 0
        pass

    def update(self, data):
        updated = True
        self.ts = self.context.cmx_signal.ts
        self.prices = self.context.cmx_signal.prices.copy()
        # if self.init_prices is None:
        #     self.init_prices = self.context.cmx_signal.prices.copy()
        #     self.update_share_ratios()
        self.pnl = 0
        self.net = 0
        self.fee = 0
        self.realized = 0
        self.unrealized = 0
        self.unhedged = 0
        # need_update_sr = False
        for i in range(self.leg_num):
            updated &= self.leg_risks[i].update(data)
            self.leg_positions[i] = self.leg_risks[i].position
            self.leg_quote_positions[i] = self.leg_risks[i].quote_pos
            self.leg_costs[i] = self.leg_risks[i].cost_basis
            self.leg_fees[i]  = self.leg_risks[i].fee
            self.leg_realized_pnls[i] = self.leg_risks[i].realized
            self.leg_traded_amounts[i] = self.leg_risks[i].traded
            self.leg_unrealized_pnls[i] = self.leg_risks[i].unrealized
            self.leg_pnls[i] = self.leg_risks[i].pnl
            self.leg_nets[i] = self.leg_risks[i].net
            self.daily_end_leg_nets[i] = self.leg_risks[i].daily_end_net
            self.daily_min_leg_nets[i] = self.leg_risks[i].daily_min_net
            self.daily_end_leg_positions[i] = self.leg_risks[i].daily_end_position
            self.daily_max_leg_positions[i] = self.leg_risks[i].daily_max_position
            self.daily_min_leg_positions[i] = self.leg_risks[i].daily_min_position
            self.daily_end_leg_trade_amounts[i] = self.leg_risks[i].daily_end_traded
            self.pnl += self.leg_pnls[i]
            self.net += self.leg_nets[i]
            self.fee += self.leg_fees[i]
            self.realized += self.leg_realized_pnls[i]
            self.unrealized += self.leg_unrealized_pnls[i]
            # if abs(self.prices[i] / self.init_prices[i] - 1) > 0.1:
            #     self.init_prices[i] = self.prices[i]
            #     need_update_sr = True
        # if need_update_sr:
        #     self.update_share_ratios()
        self.eod = self.leg_risks[0].eod
        self.trade_df = pd.concat([x.trade_df for x in self.leg_risks])
        self.trade_df.sort_index(inplace = True)
        self.new_trade_df = pd.concat([x.new_trade_df for x in self.leg_risks])
        self.new_trade_df.sort_index(inplace = True)
        self.position = self.leg_positions[0]
        self.unhedged = np.sum(self.leg_quote_positions)

        self.daily_end_net = self.daily_init_net + self.net
        self.daily_min_net = min(self.daily_min_net, self.daily_end_net)
        self.daily_end_position = self.leg_quote_positions[0]
        if self.leg_quote_positions[0] > self.daily_max_position:
            self.daily_max_position = self.leg_quote_positions[0]
            self.daily_max_leg_positions = self.leg_quote_positions.copy()
        if self.leg_quote_positions[0] < self.daily_min_position:
            self.daily_min_position = self.leg_quote_positions[0]
            self.daily_min_leg_positions = self.leg_quote_positions.copy()
        self.daily_end_leg_nets = self.leg_nets.copy()
        self.daily_end_leg_trade_amounts = self.leg_traded_amounts.copy()
        self.update_trading_status()

    def update_trading_status(self):
        if abs(self.unhedged) >= self.context.cmx_config.risk_max_delta:
            self.trading_status = 'hedge_only'
            return
        if self.context.cmx_config.risk_exit_active_dt and self.ts >= self.context.cmx_config.risk_exit_active_dt:
            self.trading_status = 'exit_active'
            return
        if self.context.cmx_config.risk_exit_passive_dt and self.ts >= self.context.cmx_config.risk_exit_passive_dt:
            self.trading_status = 'exit_passive'
            return
        if self.context.cmx_config.risk_exit_nonew_dt and self.ts >= self.context.cmx_config.risk_exit_nonew_dt:
            self.trading_status = 'exit_nonew'
            return
        self.trading_status = 'normal'

    def reset_daily(self):
        self.pnl = 0
        self.fee = 0
        self.net = 0
        self.realized = 0

        self.daily_init_net = 0
        self.daily_init_position = self.position

        for i in range(self.leg_num):
            self.leg_risks[i].reset_daily()
            self.leg_pnls[i] = self.leg_risks[i].pnl
            self.leg_fees[i] = self.leg_risks[i].fee
            self.leg_nets[i] = self.leg_risks[i].net
            self.leg_realized_pnls[i] = self.leg_risks[i].realized
            self.leg_unrealized_offsets[i] = self.leg_risks[i].unrealized_offset
            self.leg_traded_amounts[i] = self.leg_risks[i].traded
            self.daily_init_leg_nets[i] = 0
            self.daily_init_leg_positions[i] = self.leg_quote_positions[i]
            self.daily_init_leg_trade_amounts[i] = self.leg_traded_amounts[i]
            self.init_leg_positions[i] = self.leg_risks[i].init_position
            self.init_leg_costs[i] = self.leg_risks[i].init_cost_basis
            self.pnl += self.leg_pnls[i]
            self.fee += self.leg_fees[i]
            self.net += self.leg_nets[i]
            self.realized += self.leg_realized_pnls[i]
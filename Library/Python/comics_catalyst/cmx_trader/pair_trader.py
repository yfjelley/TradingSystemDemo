import os
import logging
from catalyst import run_algorithm
from cmx_config.multileg_config import multileg_config
from cmx_signal.multileg_pricing import price_ratio
from cmx_risk.multileg_risk_manager import twoleg_risk
from cmx_execution.multileg_order_manager import multileg_orders
from cmx_risk.multileg_invent_manager import twoleg_invent
from cmx_util.multileg_recorder import multileg_recorder
from cmx_util.multileg_display import twoleg_display

# To disable catalyst log:
# os.environ['CATALYST_LOG_LEVEL'] = '13' #CRITICAL = 15,ERROR = 14,WARNING = 13,NOTICE = 12,INFO = 11,DEBUG = 10,TRACE = 9
# Windows: use cmd and set env variable. instruction below
# http://www.dowdandassociates.com/blog/content/howto-set-an-environment-variable-in-windows-command-line-and-registry/

class pair_trader:
    def __init__(self, json_file):
        self.json_file = json_file
        self.cmx_config = multileg_config(json_file)

    def initialize(self, context):
        self.cmx_config.update_ts(None, context)
        context.cmx_config   = self.cmx_config
        context.cmx_signal   = price_ratio(context)
        context.cmx_risk     = twoleg_risk(context)
        context.cmx_exec     = multileg_orders(context)
        context.cmx_invent   = twoleg_invent(context)
        context.cmx_recorder = multileg_recorder(context)
        context.cmx_display  = twoleg_display(context)

    def before_trading_start(self, context, data):
        # ts = data.current_dt
        context.cmx_display.run_daily()

    def handle_data(self, context, data):
        ts = data.current_dt
        context.cmx_config.update_ts(ts, context)
        config_reloaded = context.cmx_config.reload_config()
        if config_reloaded:
            context.cmx_signal.reload_config(data)
            context.cmx_risk.reload_config()
            context.cmx_invent.reload_config()
        context.cmx_signal.update(data)
        context.cmx_risk.update(data)
        if context.cmx_risk.trading_enabled:
            if context.cmx_risk.trading_status == 'normal':
                context.cmx_invent.trade_normal()
            elif context.cmx_risk.trading_status == 'hedge_only':
                context.cmx_invent.hedge_only()
            elif context.cmx_risk.trading_status == 'exit_nonew':
                context.cmx_invent.exit_nonew()
            elif context.cmx_risk.trading_status == 'exit_passive':
                context.cmx_invent.exit_passive()
            elif context.cmx_risk.trading_status == 'exit_active':
                context.cmx_invent.exit_active()
        context.cmx_recorder.run()
        context.cmx_display.run()
        

    def analyze(self, context, perf):
        pass

    def run(self):
        run_algorithm(
                      live = False if self.cmx_config.global_mode == 'backtest' else True,
                      live_graph = False,
                      analyze_live = None,
                      simulate_orders = False if self.cmx_config.global_mode == 'live' else True,
                      capital_base = self.cmx_config.risk_max_notional,
                      data_frequency = 'minute',
                      data = None,
                      bundle = None,
                      bundle_timestamp = None,
                      default_extension = True,
                      extensions = (),
                      strict_extensions = True,
                      environ = os.environ,
                      initialize = self.initialize,
                      before_trading_start = self.before_trading_start,
                      handle_data = self.handle_data,
                      analyze = self.analyze,
                      exchange_name = ','.join(set(self.cmx_config.global_exchanges)),
                      algo_namespace = self.cmx_config.global_context,
                      quote_currency = self.cmx_config.risk_quote_currency,
                      start = self.cmx_config.risk_start_dt,
                      end = self.cmx_config.risk_end_dt,
                      output = os.path.join(self.cmx_config.storage_record_folder, self.cmx_config.storage_record_file),
                      auth_aliases = None,
                     )
        # TODO: how to change output file....



# cmx_config = {}
# def initialize(context):
#   context.cmx_config  = multileg_config(context, cmx_config)
#   context.cmx_logger  = multileg_logger(context)
#   context.cmx_signal  = multileg_signal(context)
#   context.cmx_account = multileg_account(context)
#   context.cmx_exec    = multileg_orders(context)
#   context.cmx_invent  = multileg_invent(context)
#   context.cmx_risk    = multileg_risk(context)
#   context.cmx_recoder = multileg_recorder(context)
#   context.cmx_display = multileg_display(context)
#   context.cmx_plotter = multileg_plotter(context)
#   #TODO: recorder file prefix != others, plot didn't work

# def before_trading_start(context, data):
#   # this is being called daily at 0:00 UTC
#   context.cmx_display.run_daily()
#   context.cmx_risk.update_daily()
#   return

# def handle_data(context, data):
#   today = data.current_dt.floor('1D')
#   if today != context.current_day:
#       context.current_day = today
#       context.cmx_invent.cancel_all()
#       if context.cmx_config.mode == 'live':
#           # context.cmx_account.update(data)
#           pass
#   context.cmx_signal.update(data)
#   context.cmx_risk.run()
#   context.cmx_invent.trade_normal()
#   context.cmx_recoder.run()
#   context.cmx_display.run()

# def analyze(context, perf):
#   context.cmx_invent.cancel_all()
#   context.cmx_display.run_daily()
#   context.cmx_plotter.plot(perf)
#   pass

# def run(app_config):
#   global cmx_config
#   cmx_config = app_config
#   record_pickle_file = get_pickle_file(cmx_config)
#   cmx_config['record_pickle'] = record_pickle_file
#   run_algorithm(
#                 live = True if cmx_config['global_mode'] in ['live', 'paper'] else False,
#                 live_graph = False,
#                 analyze_live = None, # pass a function
#                 simulate_orders = False if cmx_config['global_mode'] == 'live' else True,
#                 capital_base = cmx_config['risk_max_amount'],
#                 data_frequency = 'minute' if cmx_config['signal_candle_size'] == '1T' else 'daily',
#                 data = None,
#                 bundle = None,
#                 bundle_timestamp = None,
#                 default_extension = True,
#                 extensions = (),
#                 strict_extensions = True,
#                 environ = os.environ,
#                 # initialize = (initialize, cmx_config),
#                 initialize = initialize,
#                 before_trading_start = before_trading_start,
#                 handle_data = handle_data,
#                 analyze = analyze,
#                 exchange_name = ','.join(set(cmx_config['exchanges'])),
#                 algo_namespace = cmx_config['global_namespace'],
#                 quote_currency = cmx_config['risk_quote_currency'],
#                 start = cmx_config['time_start'],
#                 end = cmx_config['time_end'],
#                 output = cmx_config['record_pickle'],
#                 auth_aliases = None, # For example: 'binance,auth2,bittrex,auth2'
#                )


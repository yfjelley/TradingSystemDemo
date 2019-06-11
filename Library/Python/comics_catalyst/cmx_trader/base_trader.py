import os
import logging
import pandas as pd
from cmx_config.load_config import (get_pickle_file, load_base_config)
from cmx_signal.dynamic import base_signal
from cmx_risk.acct_manager import outright_account
from cmx_risk.invent_manager import base_invent
from cmx_risk.risk_manager import base_risk

from cmx_util.recorder import base_recorder
from cmx_util.display import base_display
from catalyst import run_algorithm

# To disable catalyst log:
# os.environ['CATALYST_LOG_LEVEL'] = '13' #CRITICAL = 15,ERROR = 14,WARNING = 13,NOTICE = 12,INFO = 11,DEBUG = 10,TRACE = 9
# Windows: use cmd and set env variable. instruction below
# http://www.dowdandassociates.com/blog/content/howto-set-an-environment-variable-in-windows-command-line-and-registry/

cmx_config = {}
def initialize(context):
    load_base_config(context, cmx_config)
    context.cmx_signal  = base_signal(context)
    context.cmx_invent  = base_invent(context)
    context.cmx_risk    = base_risk(context)
    context.cmx_recorder = base_recorder(context)
    context.cmx_display = base_display(context)

def before_trading_start(context, data):
    pass

def handle_data(context, data):
    today = data.current_dt.floor('1D')
    if today != context.current_day:
        context.current_day = today
            
    context.cmx_signal.update(data)
    context.cmx_recorder.run()
    context.cmx_display.run()

def analyze(context, perf):
    pass

def run(app_config):
    global cmx_config
    cmx_config = app_config
    record_pickle_file = get_pickle_file(cmx_config)
    cmx_config['record_pickle'] = record_pickle_file
    run_algorithm(
                  live = True if cmx_config['global_mode'] in ['live', 'paper'] else False,
                  live_graph = False,
                  analyze_live = None, # pass a function
                  simulate_orders = False if cmx_config['global_mode'] == 'live' else True,
                  capital_base = 1,
                  data_frequency = 'minute',
                  data = None,
                  bundle = None,
                  bundle_timestamp = None,
                  default_extension = True,
                  extensions = (),
                  strict_extensions = True,
                  environ = os.environ,
                  # initialize = (initialize, cmx_config),
                  initialize = initialize,
                  before_trading_start = before_trading_start,
                  handle_data = handle_data,
                  analyze = analyze,
                  exchange_name = cmx_config['exchange'],
                  algo_namespace = cmx_config['global_namespace'],
                  quote_currency = 'eth',
                  start = cmx_config['time_start'],
                  end = cmx_config['time_end'],
                  output = cmx_config['record_pickle'],
                  auth_aliases = None, # For example: 'binance,auth2,bittrex,auth2'
                 )


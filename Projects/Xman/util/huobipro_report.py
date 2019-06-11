import os
import sys
import pathlib
cmx_rootpath = pathlib.Path(os.getcwd()).parents[2]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/cmx_analysis'))
sys.path.append(os.path.join(cmx_rootpath,'Library/Python/comics_crypto_compare'))
sys.path.append(os.path.join(cmx_rootpath,'Library/Python/comics_crypto_compare/*'))
from eod import outright_eod as eod
from exchange_statements import (ccxt_trades, binance_statement)
import datetime as dt


## download trade statement through ccxt api:
exchange = 'huobipro'
folder = r'C:\Users\Penny\crypto\trade_history\{}'.format(exchange)
if not os.path.exists(folder):
	os.makedirs(folder)

outfile = 'TradeHistory.xlsx'
if os.path.exists(os.path.join(folder, outfile)):
	mtime = dt.datetime.utcfromtimestamp(os.path.getmtime(os.path.join(folder, outfile)))
	newname = 'TradeHistory_{}.xlsx'.format((mtime - dt.timedelta(days = 1)).date())
	if not os.path.exists(os.path.join(folder, newname)):
		os.rename(os.path.join(folder, outfile), os.path.join(folder, newname))
huobipro_trades = ccxt_trades(exchange)
trade_df = huobipro_trades.get_trade_df()
trade_df.to_excel(os.path.join(folder, outfile))


# # exchange statements:
end_date   = dt.datetime.utcnow().date() - dt.timedelta(days = 2)
# end_date   = dt.date(2018, 9, 15)
start_date = dt.date(2018, 9, 14)
overwrite = False
f = r'C:\Users\Penny\crypto\trade_history\{}\TradeHistory.xlsx'.format(exchange)
context_map = {
			   'Cecilia': 'xmr.eth', 
			   'Sunfire': 'omg.eth',
			   }
symbols = []
contexts = []
for k, v in context_map.items():
	symbols.append(v)
	contexts.append(k)

binance = binance_statement(f)
for sym in symbols:
	df = binance.save_daily(sym, start_date, end_date, overwrite)

# portfolio stats and plots:
start = dt.datetime.combine(start_date, dt.time(0,0))
end   = dt.datetime.combine(end_date, dt.time(0,0))
quote_coins = ['btc', 'eth', 'usd']
output_folder = r'C:\Fwang\Trading\production\exchange_statements\{}'.format(exchange)
for quote in quote_coins:
	folder = os.path.join(output_folder, 'portfolio_statistics/{}'.format(quote))
	if not os.path.exists(folder):
		os.makedirs(folder)
	stat_f = 'portfolio_stats_{}_{}.csv'.format(quote, end.date())
	pnl_dfs = binance.get_portfolio_df(symbols, quote, start, end)
	stat_df = binance.get_statistics(pnl_dfs['net'], pnl_dfs['pnl'])
	stat_df.to_csv(os.path.join(folder, stat_f))

	fig_folder = os.path.join(output_folder, 'portfolio_plot/{}'.format(quote))
	if not os.path.exists(fig_folder):
		os.makedirs(fig_folder)
	fig_f = 'portfolio_pnls_{}_{}.png'.format(quote, end.date())
	binance.plot(pnl_dfs['net'], pnl_dfs['pnl'], quote, os.path.join(fig_folder, fig_f))




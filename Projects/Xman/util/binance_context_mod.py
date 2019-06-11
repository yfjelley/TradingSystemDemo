import os
import sys
import pathlib
cmx_rootpath = pathlib.Path(os.getcwd()).parents[2]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/cmx_analysis'))
sys.path.append(os.path.join(cmx_rootpath,'Library/Python/comics_crypto_compare'))
sys.path.append(os.path.join(cmx_rootpath,'Library/Python/comics_crypto_compare/*'))
from exchange_statements import binance_statement
from context_daily_record import outright_record
from eod import outright_context_eod
import datetime as dt
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

end_date = dt.datetime.utcnow().date() + dt.timedelta(days = 1)

exchange = 'binance'
instance = 'xman-live-c1'
context_map = {
		       'Changeling': 'dash.eth', \
			   'Nightcrawler': 'tusd.usdt',\
			   'Cyclops': 'xmr.eth', \
			   # 'Polaris': 'etc.usdt', \
			   'Havok': 'xem.eth', \
			   'Sway': 'omg.eth',\
			   }
symbols = []
contexts = []
for k, v in context_map.items():
	symbols.append(v)
	contexts.append(k)

overwrite = False
agg_eod = pd.DataFrame()
plot_files = []
for context, sym in context_map.items():
	context_eod = outright_context_eod(context, instance, exchange, sym, overwrite = overwrite)
	eod_info = context_eod.update_mod(end_date)
	agg_eod = pd.concat([agg_eod, eod_info['report']], axis = 1)
	plot_files.append(eod_info['plot'])
agg_eod = agg_eod.T
print(agg_eod)

#################
# 4. send email #
#################
from_email = 'frankwang.alert@gmail.com'
# to_emails  = [from_email, 'alertyuanye88@outlook.com']
to_emails  = [from_email]

server = smtplib.SMTP('smtp.gmail.com', 587)
server.ehlo()
server.starttls()
server.login(from_email, 'xrzfetasfecmqebj')

msg = MIMEMultipart()
msg['subject'] = '[Xman] mod report: {}'.format(end_date)
msg['From'] = from_email
msg['To']   = ','.join(to_emails)
msg.attach(MIMEText(agg_eod.to_html(), 'html'))
for f in plot_files:
	if f is not None:
		with open(f, 'rb') as pf:
			att = MIMEApplication(pf.read(), Name = os.path.basename(f))
		att['Content-Disposition'] = 'attachment; filename={}'.format(os.path.basename(f))
		msg.attach(att)
server.send_message(msg)
server.quit()
	

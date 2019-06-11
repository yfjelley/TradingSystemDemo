import os
import sys
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/cmx_analysis'))
from performance_analyzer import portfolio_performance
import datetime as dt
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart


def format_float(x):
    if abs(x) < 1:
        return '{0:.3f}'.format(x)
    if abs(x) < 10:
        return '{0:.2f}'.format(x)
    if abs(x) < 100:
        return '{0:.1f}'.format(x)
    return '{0:.0f}'.format(x)

if __name__ == '__main__':
    dn = dt.datetime.utcnow().date() - dt.timedelta(days = 1)
    d0 = dn - dt.timedelta(days = 6)
    contexts = ['changeling', 'cyclops', 'havok', 'sway', 'cannonball', 'colossus', 'husk', 'cecilia', 'sunfire']
    plot_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/weekly/'
    live_plot_path = os.path.join(plot_folder, 'live/weekly_live_{}.png'.format(dn))
    live_sim_plot_path = os.path.join(plot_folder, 'live_sim/weekly_live_sim_{}.png'.format(dn))
    live_exch_plot_path = os.path.join(plot_folder, 'live_exch/weekly_live_exch_{}.png'.format(dn))


    pp = portfolio_performance(contexts)
    perf = pp.calculate_performance(d0, dn)
    # for k,v in perf.items():
    #   print(k)
    #   print(v)
    exch_perf_summary = perf['exch'].applymap(format_float)
    pp.plot_live(live_plot_path)
    pp.plot_live_sim(live_sim_plot_path)
    pp.plot_live_exch(live_exch_plot_path)


    # send email:
    from_email = 'frankwang.alert@gmail.com'
    to_emails  = [from_email]
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(from_email, 'xrzfetasfecmqebj')
    msg = MIMEMultipart()
    msg['subject'] = '[Xman] weekly report: {} - {}'.format(d0, dn)
    msg['From'] = from_email
    msg['To']   = ','.join(to_emails)
    msg.attach(MIMEText(exch_perf_summary.to_html(), 'html'))
    # 
    for f in [live_plot_path, live_sim_plot_path, live_exch_plot_path]:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=os.path.basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(f)
        msg.attach(part)
    server.sendmail(from_email, from_email, msg.as_string())
    server.quit()


import os
import requests
import time
import datetime
from poloniex import Poloniex
import logging
import getopt
import sys
import traceback

argList = sys.argv[1:]
opts = 'h:'
longOpts = ['help', 'pair=', 'period=', 'tguser=', 'prod']
# Default options
pair = 'USDT_BTC'
period = 300
prod = False
tg_username = None

try:
  args, values = getopt.getopt(argList, opts, longOpts)
  for arg, value in args:
    if arg in ('-h', '--help'):
      print('--pair <pair> --period <period> --prod')
      sys.exit(0)
    elif arg in ('--pair'):
      pair = str(value)
    elif arg in ('--period'):
      period = int(value)
    elif arg in ('--prod'):
      prod = True
    elif arg in ('--tguser'):
      tg_username = str(value)
except getopt.error as err:
  print(str(err))
  sys.exit(1)

# Logger setup

try:
  os.makedirs('logs')
  print('Created logs folder')
except FileExistsError:
  pass

log = logging.getLogger()
log.setLevel(logging.DEBUG)

filename = datetime.datetime.now().strftime('%Y-%m-%d') + '-log'
if prod:
  filename += '-prod'
file = logging.FileHandler(os.path.join('logs', filename))
file.setLevel(logging.DEBUG)
fileformat = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file.setFormatter(fileformat)
log.addHandler(file)

stream = logging.StreamHandler()
stream.setLevel(logging.DEBUG)
streamformat = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
stream.setFormatter(fileformat)
log.addHandler(stream)

log.info('========================')
log.info('Start')

if tg_username:
  log.debug(f'Using tg username from command line parameter: {tg_username}')
else:
  try:
    tg_username = os.environ['TG_USER']
    log.debug(f'Using tg username from environment variable: {tg_username}')
  except KeyError as err:
    log.error(f'--tguser parameter not passed, no environment vatiable {err}, exiting...')
    sys.exit(1)

api_key = os.environ['POLO_KEY']
api_sercet = os.environ['POLO_SECRET']

polo = Poloniex(key=api_key, secret=api_sercet)

def tg_call(user, text):
  url = f'http://api.callmebot.com/start.php?source=web&user={user}&text={text}&lang=en-IN-Standard-A&rpt=5'
  return requests.post(url)

def getChartData(pair, period, start, end, lastCandleDate=None):
  if lastCandleDate:
    end = time.time()
    log.debug(f'Last candle date: {lastCandleDate}, {datetime.datetime.utcfromtimestamp(lastCandleDate)}')
  chart = []
  data = polo.returnChartData(pair, period, start, end)
  log.debug(f'Got {len(data)} candles from poloniex')
  log.debug(f'New candle date: {data[-1]["date"]}, {datetime.datetime.utcfromtimestamp(data[-1]["date"])}')
  if lastCandleDate == data[-1]['date']:
    log.debug('New candle is the same, retrying in 15 seconds...')
    time.sleep(15)
    return getChartData(pair, period, start, end, lastCandleDate)
  for candle in data:
    if float(candle['open']) > float(candle['close']):
      color = 'red'
    else:
      color = 'green'
    chart.append(
        {
          'date':int(candle['date']),
          'open':float(candle['open']),
          'close':float(candle['close']),
          'high':float(candle['high']),
          'low':float(candle['low']),
          'color':color
        })
  return chart

def getHeikinAshi(pair, period, start, end, lastCandleDate=None):
  data = getChartData(pair, period, start, end, lastCandleDate)
  chart = []
  chart.append(data[0])
  for candle in data:
    open = ( chart[-1]['open'] + chart[-1]['close'] ) / 2
    close = ( candle['open'] + candle['high'] + candle['low'] + candle['close'] ) / 4
    high = max(candle['high'], candle['low'], open, close)
    low = min(candle['high'], candle['low'], open, close)
    if open > close:
      color = 'red'
    else:
      color = 'green'
    chart.append(
        {
          'date':int(candle['date']),
          'open':open,
          'close':close,
          'high':high,
          'low':low,
          'color':color
        })
  chart.pop(0)
  log.debug(f'Converted {len(chart)} candles to Heikin Ashi')
  return chart

def mainLoop(pair, period):
  now = time.time()
  chart = getHeikinAshi(pair, period, now - period * 1000, now)
  log.debug('Last five candles:')
  for candle in chart[-5:]:
    log.debug(candle)
  lastCandleDate = chart[-1]['date']
  log.debug(f'Current candle date: {lastCandleDate}, {datetime.datetime.utcfromtimestamp(lastCandleDate)}')
  while True:
    now = time.time()
    fromLastCandle = now % period
    untilNextCandle = period - fromLastCandle
    log.info(f'Waiting {datetime.datetime.utcfromtimestamp(untilNextCandle + 20).strftime("%H:%M:%S")} until new candle...')
    time.sleep(untilNextCandle)
    lastCandleDate = chart[-1]['date']
    log.info('Getting new candle...')
    chart = getHeikinAshi(pair, period, now - period * 1000, now, chart[-1]['date'])
    lastCandleColor = chart[-2]['color']
    candleBeforeColor = chart[-3]['color']
    log.debug(chart[-3])
    log.debug(chart[-2])
    log.info(f'Candle pattern is {candleBeforeColor} = > {lastCandleColor}')
    if lastCandleColor == 'green' and candleBeforeColor == 'red':
      log.info('Time to buy, calling user in tg...')
      tg_call(tg_username, f'Time to buy {pair}')
    elif lastCandleColor == 'red' and candleBeforeColor == 'green':
      log.info('Time to move stop loss, calling user in tg...')
      tg_call(tg_username, f'Move stop loss on {pair}')
    else:
      log.info('Nothing to do...')

if __name__ == '__main__':
  log.info(f'Pair: {pair}, period: {period}, tg user: {tg_username}, production: {prod}')
  try:
    mainLoop(pair, period)
  except Exception as e:
    log.error((traceback.format_exc()))

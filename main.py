import os
import requests
from requests.exceptions import Timeout
import time
import datetime
from poloniex import Poloniex
import logging
import getopt
import sys
import traceback
import api

argList = sys.argv[1:]
opts = 'h'
longOpts = ['help', 'pair=', 'period=', 'tguser=', 'prod', 'call', 'apitime']
# Default options
pair = 'USDT_BTC'
period = 300
prod = False
tg_username = None
call = False
apitime = False
private_api = False

try:
  args, values = getopt.getopt(argList, opts, longOpts)
  for arg, value in args:
    if arg in ('-h', '--help'):
      print(
'''
Arguments:
--pair <pair> - currency pair
--period <period> - chart period
--tguser <telegram username> - user to call
--prod - writes separate logs for production run
--call - enable calling in telegram
--apitime - use ipgeolocation.io instead of system time
'''
          )
      sys.exit(0)
    elif arg in ('--pair'):
      pair = str(value)
    elif arg in ('--period'):
      period = int(value)
    elif arg in ('--prod'):
      prod = True
    elif arg in ('--tguser'):
      tg_username = str(value)
    elif arg in ('--call'):
      call = True
    elif arg in ('--apitime'):
      apitime = True
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

# TG username setup
if tg_username:
  log.debug(f'Using tg username from command line parameter: {tg_username}')
else:
  try:
    tg_username = os.environ['TG_USER']
    log.debug(f'Using tg username from environment variable: {tg_username}')
  except KeyError as err:
    log.error(f'--tguser parameter not passed, no environment vatiable {err}, exiting...')
    sys.exit(1)

# Poloniex api setup
try:
  api_key = os.environ['POLO_KEY']
  api_sercet = os.environ['POLO_SECRET']
  polo = Poloniex(key=api_key, secret=api_sercet)
  private_api = True
  log.info(f'Logged to Poloniex with api keys from environment variables')
except KeyError:
  polo = Poloniex()
  log.info('No POLO_KEY and POLO_SECRET environment variables, using public Poloniex api only')

# Api time setup
if apitime:
  try:
    time_api_key = os.environ['TIME_API']
    responce = requests.get(f'https://api.ipgeolocation.io/timezone?apiKey={time_api_key}&tz=Europe/London', timeout=10)
    responce = responce.json()
  except KeyError as err:
    log.error(f'No environment variable {err}, must be set to use --apitime, exiting...')
    sys.exit(1)
  except Timeout:
    log.error('Request to ipgeolocation.io timed out')
    sys.exit(1)
  try:
    unixTime = responce['date_time_unix']
    log.info(f'Connected to ipgeolocation.io, current unix time: {unixTime}')
  except KeyError:
    log.error(responce['message'])
    sys.exit(1)

# End of setup

def getCurrentTime():
  if apitime:
    try:
      responce = requests.get(f'https://api.ipgeolocation.io/timezone?apiKey={time_api_key}&tz=Europe/London', timeout=5)
      responce = responce.json()
      unixTime = responce['date_time_unix']
      return unixTime
    except KeyError:
      log.warning(responce['message'])
      log.warning('Fallback to system time')
    except Timeout:
      log.warning('Request to ipgeolocation.io timed out')
      log.warning('Fallback to system time')
  return time.time()

def tg_call(user, text):
  url = f'http://api.callmebot.com/start.php?source=web&user={user}&text={text}&lang=en-IN-Standard-A&rpt=5'
  return requests.post(url)

def getChartData(pair, period, start, end, lastCandleDate=None):
  if lastCandleDate:
    end = getCurrentTime()
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
  now = getCurrentTime()
  chart = getHeikinAshi(pair, period, now - period * 1000, now)
  log.debug('Last five candles:')
  for candle in chart[-5:]:
    log.debug(candle)
  lastCandleDate = chart[-1]['date']
  log.debug(f'Current candle date: {lastCandleDate}, {datetime.datetime.utcfromtimestamp(lastCandleDate)}')
  while True:
    now = getCurrentTime()
    fromLastCandle = now % period
    untilNextCandle = period - fromLastCandle
    log.info(f'Waiting {datetime.datetime.utcfromtimestamp(untilNextCandle).strftime("%H:%M:%S")} until new candle...')
    time.sleep(untilNextCandle)
    lastCandleDate = chart[-1]['date']
    log.info('Getting new candle...')
    chart = getHeikinAshi(pair, period, now - period * 1000, now, chart[-1]['date'])
    lastCandleColor = chart[-2]['color']
    candleBeforeColor = chart[-3]['color']
    log.debug(chart[-3])
    log.debug(chart[-2])
    log.debug(chart[-1])
    log.info(f'Candle pattern is {candleBeforeColor} = > {lastCandleColor}')
    if lastCandleColor == 'green' and candleBeforeColor == 'red':
      log.info('Time to buy')
      if call:
        log.info('Calling {tg_username}...')
        tg_call(tg_username, f'Time to buy {pair}')
    elif lastCandleColor == 'red' and candleBeforeColor == 'green':
      log.info('Time to move stop loss')
      if call:
        log.info('Calling {tg_username}...')
        tg_call(tg_username, f'Move stop loss on {pair}')
    else:
      log.info('Nothing to do...')

if __name__ == '__main__':
  log.info(f'Pair: {pair}, period: {period}')
  log.info(f'Call: {call}, username: {tg_username}')
  log.info(f'Poloniex private api: {private_api}')
  log.info(f'Production: {prod}')
  try:
    mainLoop(pair, period)
  except Exception as e:
    log.error((traceback.format_exc()))

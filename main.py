import os
import requests
from requests.exceptions import Timeout
import time
import datetime
from poloniex import Poloniex, PoloniexError
import logging
import getopt
import sys
import traceback
import api

argList = sys.argv[1:]
opts = 'h'
longOpts = ['help', 'pair=', 'period=', 'tguser=',
            'maxrisk=', 'maxposition=',
            'polokey=', 'polosecret=',
            'tick=', 'tguserid=', 'tgtoken=',
            'loglevel=',
            'prod', 'call', 'apitime', 'trade', 'notify']
# Default options
pair = 'USDT_BTC'
period = 300
prod = False
tg_username = None
call = False
apitime = False
private_api = False
maxrisk = 0.05
maxposition = False
polokey = False
polosecret = False
tick = 5
trade = False
tguserid = False
tgtoken = False
notify = False
loglevel = logging.DEBUG

try:
  args, values = getopt.getopt(argList, opts, longOpts)
  for arg, value in args:
    if arg in ('-h', '--help'):
      print(
'''
Arguments:
--loglevel <level> - log level to display in terminal, default: DEBUG
--pair <pair> - currency pair, default: USDT_BTC
--period <period> - chart period (5m, 15m, 30m, 2h, 4h, 1d), default: 5m
--maxrisk <amount persent> - maximum persent risk of total account on one trade, default: 5
--maxposition <amount of currency> - maximum position size
--polokey <key> - poloniex api key
--polosecret <secret> - poloniex api secret
--tick <time in seconds> - price check period in seconds
--tguser <telegram username> - user to call
--tguserid <user id> - telegram user id to send notifications to
--tgtoken <token> - telegram bot token
--prod - writes separate logs for production run
--call - enable calling in telegram with callmebot.com
--apitime - use ipgeolocation.io instead of system time
--trade - enable automated trading
--notify - enable telegram notifications
'''
          )
      sys.exit(0)
    elif arg in ('--pair'):
      pair = str(value.upper())
    elif arg in ('--period'):
      names = {
          '5m':300,
          '15m':900,
          '30m':1800,
          '2h':7200,
          '4h':14400,
          '1d':86400
          }
      try:
        period = int(value)
      except ValueError:
        if value not in names.keys():
          print(f'Invalid period "{value}", periods are 5m, 15m, 30m, 2h, 4h, 1d')
          sys.exit(1)
        period = names[value]
    elif arg in ('--prod'):
      prod = True
    elif arg in ('--tguser'):
      tg_username = str(value)
    elif arg in ('--maxrisk'):
      maxrisk = float(value) / 100
      if maxrisk > 1 or maxrisk < 0.005:
        print('--maxrisk must be between 0.005 and 1')
        sys.exit(1)
    elif arg in ('--maxposition'):
      maxposition = float(value)
    elif arg in ('--polokey'):
      polokey = value
    elif arg in ('--polosecret'):
      polosecret = value
    elif arg in ('--tick'):
      tick = float(value)
    elif arg in ('--tguserid'):
      tguserid = value
    elif arg in ('--tgtoken'):
      tgtoken = value
    elif arg in ('--loglevel'):
      names = {
          'INFO':logging.INFO,
          'DEBUG':logging.DEBUG,
          'WARNING':logging.WARNING,
          'ERROR':logging.ERROR
          }
      loglevel = names[value.upper()]
    elif arg in ('--call'):
      call = True
    elif arg in ('--apitime'):
      apitime = True
    elif arg in ('--trade'):
      trade = True
    elif arg in ('--notify'):
      notify = True
except getopt.error as err:
  print(str(err))
  sys.exit(1)

# Logger setup
try:
  os.makedirs('logs')
  print('Created logs folder')
except FileExistsError:
  pass

log = logging.getLogger('main')
log.setLevel(logging.DEBUG)

reqlog = logging.getLogger('urllib3')
reqlog.setLevel(logging.DEBUG)

filename = datetime.datetime.now().strftime('%Y-%m-%d') + '-log'
if prod:
  filename += '-prod'
file = logging.FileHandler(os.path.join('logs', filename))
file.setLevel(logging.DEBUG)
fileformat = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file.setFormatter(fileformat)
log.addHandler(file)

reqfile = logging.FileHandler(os.path.join('logs', filename + '-requests'))
reqfile.setLevel(logging.DEBUG)
fileformat = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
reqfile.setFormatter(fileformat)
reqlog.addHandler(reqfile)

stream = logging.StreamHandler()
stream.setLevel(loglevel)
streamformat = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
stream.setFormatter(fileformat)
log.addHandler(stream)
reqlog.addHandler(stream)

log.info('========================')
log.info('Start')

# TG username setup
if call:
  if tg_username:
    log.debug(f'Using tg username from command line parameter: {tg_username}')
  else:
    try:
      tg_username = os.environ['TG_USER']
      log.debug(f'Using tg username from environment variable: {tg_username}')
    except KeyError as err:
      log.error(f'--tguser parameter not passed, no environment vatiable {err}, exiting...')
      sys.exit(1)

# TG notification bot setup
if notify:
  if tgtoken:
    pass
  else:
    try:
      tgtoken = os.environ['TG_TOKEN']
    except KeyError as err:
      log.error(f'{err} environment variable or --tgtoken should be set up to use --notify')
      sys.exit(1)
  result = requests.get(f'https://api.telegram.org/bot{tgtoken}/getMe')
  result = result.json()
  if result['ok']:
    log.info('Connected to telegram bot api')
  else:
    log.error('Invalid telegram token')
    sys,exit(1)
  if tguserid:
    pass
  else:
    try:
      tguserid = os.environ['TG_USERID']
    except KeyError as err:
      log.error(f'{err} environment variable or --tguserid should be set up to use --notify')

# Poloniex api setup
try:
  if polokey and polosecret:
    api_key = polokey
    api_secret = polosecret
    log.info('Using Poloniex api keys from arguments')
  else:
    api_key = os.environ['POLO_KEY']
    api_secret = os.environ['POLO_SECRET']
    log.info('Using Poloniex api keys from environment variables')
  polo = Poloniex(key=api_key, secret=api_secret)
  private_api = True
  api.getAllBalances(polo, total=True)
  log.info(f'Logged on to Poloniex private api')
except KeyError:
  polo = Poloniex()
  log.info('No Poloniex api keys set, using public api only')
except PoloniexError as err:
  log.error(f'Poloniex: {err}')
  sys.exit(1)

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

def tg_message(text):
  if not notify:
    return 0
  text = f'{datetime.datetime.now()}\n{pair}-{period}\n{text}'
  url = f'https://api.telegram.org/bot{tgtoken}/sendMessage?chat_id={tguserid}&text={text}'
  return requests.get(url)

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
    open = float(f'{open:.8f}')
    close = ( candle['open'] + candle['high'] + candle['low'] + candle['close'] ) / 4
    close = float(f'{close:.8f}')
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
  base, coin = pair.split('_')
  position_open = False
  position_size = False
  position_entry = False
  position_stopLoss = False
  expected_risk_persent = False
  expected_risk = False
  now = getCurrentTime()
  chart = getHeikinAshi(pair, period, now - period * 1000, now)
  log.debug('Last five candles:')
  for candle in chart[-5:]:
    log.debug(candle)
  lastCandleDate = chart[-1]['date']
  log.debug(f'Current candle date: {lastCandleDate}, {datetime.datetime.utcfromtimestamp(lastCandleDate)}')
  if trade:
    currentCoinBalance = float(polo.returnBalances()[coin])
    if currentCoinBalance:
      log.info(f'Found available balance of {currentCoinBalance} {coin}, calculating stop loss...')
      n = -1
      while not position_stopLoss:
        lastCandleColor = chart[n-1]['color']
        candleBeforeColor = chart[n-2]['color']
        if candleBeforeColor != lastCandleColor:
          position_stopLoss = float(chart[n-1]['low'])
          log.info(f'Stop loss set to {position_stopLoss}')
          tg_message(f'Stop loss set to {position_stopLoss}')
          position_open = True
          log.debug(f'position_open: {position_open}')
        n -= 1
  while True:
    now = getCurrentTime()
    fromLastCandle = now % period
    untilNextCandle = period - fromLastCandle
    log.info(f'Waiting {datetime.datetime.utcfromtimestamp(untilNextCandle).strftime("%H:%M:%S")} until new candle...')
    nextCandleTime = chart[-1]['date'] + period
    log.debug(f'Next candle date: {nextCandleTime}')
    # Tick check
    while getCurrentTime() < nextCandleTime:
      if trade:
        currentPrice = api.getTicker(polo, pair)
        if position_entry and currentPrice > position_entry:
          log.info(f'Entry price of {position_entry} hit, buying {coin}...')
          coinBefore = float(polo.returnBalances()[coin])
          baseBefore = float(polo.returnBalances()[base])
          result = api.buy(polo, pair, market=True, total=position_size)
          log.debug(result)
          coinAfter = float(polo.returnBalances()[coin])
          baseAfter = float(polo.returnBalances()[base])
          coinAmount = f'{coinBefore - coinAfter:.8f}'
          baseAmount = f'{baseBefore - baseAfter:.8f}'
          log.info(f'Bought {coinAmount} {coin} for {baseAmount} {base} at {currentPrice}')
          tg_message(f'''Entry price hit
{pair} Buy
Rate: {currentPrice}
Amount: {coinAmount} {coin}
Total:{baseAmount} {base}''')
          position_open = True
          log.debug(f'position_open: {position_open}')
          position_entry = False
          log.debug('Position entry removed')
        if position_open and currentPrice < position_stopLoss:
          log.info(f'Stop loss of {position_stopLoss} hit, selling {coin}...')
          coinBefore = float(polo.returnBalances()[coin])
          baseBefore = float(polo.returnBalances()[base])
          result = api.sell(polo, pair, market=True, all=True)
          log.debug(result)
          coinAfter = float(polo.returnBalances()[coin])
          baseAfter = float(polo.returnBalances()[base])
          coinAmount = f'{coinBefore - coinAfter:.8f}'
          baseAmount = f'{baseAfter - baseBefore:.8f}'
          log.info(f'Sold {coinAmount} {coin} for {baseAmount} {base} at {currentPrice}')
          tg_message(f'''Stop loss hit
{pair} Sell
Rate: {currentPrice}
Amount: {coinAmount} {coin}
Total: {baseAmount} {base}''')
          position_stopLoss = False
          log.debug('Position stop loss removed')
          position_entry = False
          log.debug('Position entry removed')
          position_open = False
          log.debug(f'Position open: {position_open}')
        if position_stopLoss and not position_open and currentPrice < position_stopLoss:
          log.info('Entry not hit, position cancelled')
          tg_message('Entry not hit, position cancelled')
          position_stopLoss = False
          log.debug('Position stop loss removed')
          position_entry = False
          log.debug('Position entry removed')
          position_open = False
          log.debug(f'position_open: {position_open}')
      time.sleep(tick)

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
      if private_api:
        total_balance = api.getTotalBalance(polo)
        position_entry = chart[-2]['high']
        position_stopLoss = chart[-2]['low']
        candle_change = 1 - ( chart[-2]['low'] / chart[-2]['high'] )
        maxloss = total_balance * maxrisk
        available_balance = float(polo.returnBalances()[base])
        position_size = min(maxloss / candle_change, available_balance)
        if maxposition:
          position_size = min(position_size, maxposition)
        expected_risk = position_size * candle_change
        expected_risk_persent = expected_risk / total_balance
        position_size = float(f'{position_size:.8f}')
        log.info(f'Candle risk: {candle_change * 100:.3f}%')
        log.info(f'Available balance: {available_balance} {base}')
        log.info(f'Position entry: {position_entry}')
        log.info(f'Position stop loss: {position_stopLoss}')
        log.info(f'Position size: {position_size} {base}')
        log.info(f'Expected risk: {expected_risk_persent*100:.2f}%, {expected_risk:.8f} {base}')
        tg_message(f'''New position setup
Candle risk: {candle_change * 100:.3f}%
Available balance: {available_balance} {base}
Position entry: {position_entry}
Position stop loss: {position_stopLoss}
Position size: {position_size} {base}
Expected risk: {expected_risk_persent*100:.2f}%, {expected_risk:.8f} {base}
''')
      if call:
        log.info('Calling {tg_username}...')
        tg_call(tg_username, f'Time to buy {pair}')
    elif lastCandleColor == 'red' and candleBeforeColor == 'green':
      log.info('Time to move stop loss')
      if private_api and position_open:
        position_stopLoss = chart[-2]['low']
        log.info(f'Position stop loss moved to {position_stopLoss}')
        tg_message(f'Position stop loss moved to {position_stopLoss}')
      if call:
        log.info('Calling {tg_username}...')
        tg_call(tg_username, f'Move stop loss on {pair}')
    elif lastCandleColor == 'red' and position_open:
      position_stopLoss = chart[-2]['low']
      log.info(f'Position stop loss moved to {position_stopLoss}')
      tg_message(f'Position stop loss moved to {position_stopLoss}')
    else:
      log.info('Nothing to do...')

if __name__ == '__main__':
  log.info(f'Production: {prod}')
  log.info(f'Pair: {pair}, period: {period}')
  log.info(f'Call: {call}, username: {tg_username}')
  log.info(f'Poloniex private api: {private_api}')
  log.info(f'Max risk: {maxrisk*100}%')
  log.info(f'Max position size: {maxposition}')
  log.info(f'Tick period: {tick} seconds')
  log.info(f'Automated trading: {trade}')
  log.info(f'Telegram notifications: {notify}, user id: {tguserid}')
  tg_message(
f'''Crypto Trader started
Production: {prod}
Pair: {pair}, period: {period}
Call: {call}, username: {tg_username}
Poloniex private api: {private_api}
Max risk: {maxrisk*100}%
Max position size: {maxposition}
Tick period: {tick} seconds
Automated trading: {trade}
''')
  try:
    mainLoop(pair, period)
  except Exception as e:
    tg_message(f'''Crypto Trader closed with an exception
{e}
See logs for traceback''')
    log.error((traceback.format_exc()))

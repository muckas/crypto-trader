import os
import requests
import time
import datetime
from poloniex import Poloniex
import logging

log = logging.getLogger()
log.setLevel(logging.DEBUG)

filename = datetime.datetime.now().strftime('%Y-%m-%d') + '-log'
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

tg_username = os.environ['TG_USER']
api_key = os.environ['POLO_KEY']
api_sercet = os.environ['POLO_SECRET']

polo = Poloniex(key=api_key, secret=api_sercet)

def tg_call(user, text):
  url = f'http://api.callmebot.com/start.php?source=web&user={user}&text={text}&lang=en-IN-Standard-A&rpt=5'
  return requests.post(url)

def getChartData(pair, period, start, end):
  chart = []
  data = polo.returnChartData(pair, period, start, end)
  log.debug(f'Got {len(data)} candles from poloniex')
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

def getHeikinAshi(pair, period, start, end):
  data = getChartData(pair, period, start, end)
  chart = []
  chart.append(data[0])
  for candle in data:
    high = candle['high']
    low = candle['low']
    open = ( chart[-1]['open'] + chart[-1]['close'] ) / 2
    close = ( open + high + low + candle['close'] ) / 4
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
  while True:
    now = time.time()
    fromLastCandle = now % period
    untilNextCandle = period - fromLastCandle
    log.info(f'Waiting {datetime.datetime.utcfromtimestamp(untilNextCandle + 20).strftime("%H:%M:%S")}...')
    time.sleep(untilNextCandle + 20)
    chart = getHeikinAshi(pair, period, now - period * 1000, now)
    lastCandleColor = chart[-2]['color']
    candleBeforeColor = chart[-3]['color']
    log.debug(chart[-3])
    log.debug(chart[-2])
    log.info(f'Candle pattern is {candleBeforeColor} = > {lastCandleColor}')
    if lastCandleColor == 'green' and candleBeforeColor == 'red':
      log.info('Time to buy, calling user in tg...')
      tg_call(tg_username, f'Time to buy {pair}')
    else:
      log.info('Nothing to do...')

if __name__ == '__main__':
  pair = 'USDT_BTC'
  period = 86400
  log.info(f'Pair: {pair}, period: {period}')
  mainLoop(pair, period)

import os
import requests
import time
import datetime
from poloniex import Poloniex

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
  return chart[1:]

def mainLoop(pair, period):
  while True:
    now = time.time()
    fromLastCandle = now % period
    untilNextCandle = period - fromLastCandle
    print(f'Waiting {untilNextCandle/60/60:.1f} hours until next candle...')
    time.sleep(untilNextCandle + 60)
    chart = getHeikinAshi(pair, period, now - period * 1000, now)
    print(f'Got {len(chart)} Heikin Ashi candles from poloniex')
    lastCandleColor = chart[-2]['color']
    candleBeforeColor = chart[-3]['color']
    print(f'Last completed candle is {lastCandleColor}')
    print(f'Candle before it is {candleBeforeColor}')
    if lastCandleColor == 'green' and candleBeforeColor == 'red':
      print('Time to buy, calling user in tg...')
      tg_call(tg_username, f'Time to buy {pair}')
    else:
      print('Nothing to do...')

if __name__ == '__main__':
  mainLoop('USDT_BTC', 86400)

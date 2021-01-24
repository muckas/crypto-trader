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
  requests.post(url)

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

if __name__ == '__main__':
  now = int(time.time())
  pair = 'USDT_BTC'
  period = 86400
  start = now - (period * 365)
  end = now
  for candle in getChartData(pair, period, start, end):
    print(candle)

from poloniex import Poloniex

def getTicker(polo, pair=None):
  ticker = polo.returnTicker()
  if pair:
    return float(ticker[pair]['last'])
  return ticker

def getAllBalances(polo, total=False):
  balances = polo.returnCompleteBalances()
  for currency in balances.copy():
    if balances[currency]['btcValue'] == '0.00000000':
      balances.pop(currency)
  if total:
    totalBtc = 0.0
    for currency in balances:
      totalBtc += float(balances[currency]['btcValue'])
    return float(f'{totalBtc:.8f}')
  else:
    return balances

def getTotalBalance(polo):
  total_BTC = getAllBalances(polo, total=True)
  USDT_BTC = getTicker(polo, 'USDT_BTC')
  total_USDT = total_BTC * USDT_BTC
  return total_USDT

def buy(polo, pair, rate=False, amount=False, market=False, total=False):
  if market and amount:
    rate = getTicker(polo, pair) * 1.02
    rate = f'{rate:.8f}'
    return polo.buy(pair, rate, amount)
  if market and total:
    rate = getTicker(polo, pair)
    rate *= 1.02
    amount = total / rate
    amount = f'{amount:.8f}'
    rate = f'{rate:.8f}'
    return polo.buy(pair, rate, amount)
  if total and not market:
    amount = total / rate
    amount = f'{amount:.8f}'
    return polo.buy(pair, rate, amount)
  return 0

def sell(polo, pair, rate=False, amount=False, market=False, all=False):
  base, coin = pair.split('_')
  if market and amount:
    rate = getTicker(polo, pair) * 0.98
    rate = f'{rate:.8f}'
  if market and all:
    amount = polo.returnBalances()[coin]
    rate = getTicker(polo, pair) * 0.98
  if all and not market:
    amount = polo.returnBalances()[coin]
  return polo.sell(pair, rate, amount)
  return 0

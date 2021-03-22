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

import os
import requests

tg_username = os.environ['TG_USER']
def tg_call(user, text):
  url = f'http://api.callmebot.com/start.php?source=web&user={user}&text={text}&lang=en-IN-Standard-A&rpt=5'
  requests.post(url)

if __name__ == '__main__':
  tg_call(tg_username, text='Helo?')

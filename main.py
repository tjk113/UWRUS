import requests
import json

from replace_record import replace_record
from get_records import get_records

class bcolors:
    '''Used for output coloring'''
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

BOT_USER = ''
BOT_PASS = ''
test_page = 'User:Tjk113'
test_new_wr = ('0.00', 'https://www.youtube.com/watch?v=9yjZpBq1XBE')

API = 'https://ukikipedia.net/mediawiki/api.php'
SESSION = requests.Session()
req_params = {
    'action': 'query',
    'meta'  : 'tokens',
    'type'  : 'login',
    'format': 'json'
}
print(f'Logging in to "{BOT_USER}"...', end='')
response = SESSION.get(url=API, params=req_params).json()
LOGIN_TOKEN = response['query']['tokens']['logintoken']

req_params = {
    'action'    : 'login',
    'lgname'    : BOT_USER,
    'lgpassword': BOT_PASS,
    'lgtoken'   : LOGIN_TOKEN,
    'format'    : 'json'
}
response = SESSION.post(API, data=req_params).json()
print(bcolors.OKGREEN+response['login']['result']+bcolors.ENDC)
assert response['login']['result'] == 'Success'

req_params = {
    'action'       : 'query',
    'prop'         : 'revisions',
    'titles'       : test_page,
    'rvslots'      : 'main',
    'rvprop'       : 'content',
    'formatversion': 2,
    'format'       : 'json'
}
response = json.loads(requests.get(API, params=req_params).text)['query']['pages'][0] \
                      ['revisions'][0]['slots']['main']['content']
assert '{{speedrun_infobox' in response

req_params = {
    'action'       : 'query',
    'meta'         : 'tokens',
    'titles'       : 'User:Tjk113',
    'prop'         : 'revisions',
    'rvslots'      : 'main',
    'rvprop'       : 'content|timestamp',
    'formatversion': 2,
    'curtimestamp' : True,
    'format'       : 'json'
}
response = json.loads(SESSION.get(url=API, params=req_params).text)
page_text = response['query']['pages'][0]['revisions'][0]['slots']['main']['content']
BASE_TIMESTAMP  = response['query']['pages'][0]['revisions'][0]['timestamp']
START_TIMESTAMP = response['curtimestamp']
CSRF_TOKEN = response['query']['tokens']['csrftoken']

req_params = {
    'action'        : 'edit',
    'title'         : test_page,
    'token'         : CSRF_TOKEN,
    'basetimestamp' : BASE_TIMESTAMP,
    'starttimestamp': START_TIMESTAMP,
    'bot'           : True,
    'text'          : replace_record(page_text, new_ss_record=test_new_wr),
    'format'        : 'json'
}
print(f'Editing page "{test_page}"...', end='')
response = SESSION.post(API, data=req_params).json()
print(bcolors.OKGREEN+response['edit']['result']+bcolors.ENDC)
assert response['edit']['result'] == 'Success'
import traceback
import requests
import json
import time

from itertools import zip_longest

from replace_record import replace_record, replace_record_bowser, replace_record_multi_100c
from get_records import get_rta_records, save_rta_records,     \
                        get_ss_records, save_ss_records,       \
                        get_creds, set_rta_record_not_to_save, \
                        set_ss_record_not_to_save
from common import prefix_print, bcolors
from log import Log

API = 'https://ukikipedia.net/mediawiki/api.php'

def get_login_response(SESSION, BOT_USER, BOT_PASS) -> dict:
    '''Try to log bot into Ukikipedia and return response'''
    req_params = {
        'action': 'query',
        'meta'  : 'tokens',
        'type'  : 'login',
        'format': 'json'
    }
    prefix_print(f'Logging in to "{BOT_USER}"...', end='')
    response = SESSION.get(url=API, params=req_params).json()
    LOGIN_TOKEN = response['query']['tokens']['logintoken']
    req_params = {
            'action'    : 'login',
            'lgname'    : BOT_USER,
            'lgpassword': BOT_PASS,
            'lgtoken'   : LOGIN_TOKEN,
            'format'    : 'json'
        }
    return SESSION.post(API, data=req_params).json()

def get_star_page_response(SESSION, star_name) -> tuple[str, str, str, str]:
    '''Try to get a star's RTA Guide page text, and return response'''
    req_params = {
        'action'       : 'query',
        'meta'         : 'tokens',
        'titles'       : 'RTA Guide/' + star_name, # page name
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

    return page_text, BASE_TIMESTAMP, START_TIMESTAMP, CSRF_TOKEN

def get_edit_star_page_response(SESSION, star_name, page_text, summary, \
                                CSRF_TOKEN, BASE_TIMESTAMP, START_TIMESTAMP):
    '''Edit a star's RTA Guide page with the new
    updated page text containing the new record(s)'''
    req_params = {
        'action'        : 'edit',
        'title'         : 'RTA Guide/' + star_name,
        'token'         : CSRF_TOKEN,
        'basetimestamp' : BASE_TIMESTAMP,
        'starttimestamp': START_TIMESTAMP,
        'bot'           : True,
        'text'          : page_text,
        'summary'       : summary,
        'format'        : 'json'
    }
    prefix_print(f'Editing page "RTA Guide/{star_name}"...', end='')
    return SESSION.post(API, data=req_params).json()

def main():
    t1 = time.time()
    log = Log()
    # Get new RTA and single star records from their respective spreadsheets
    SHEETS_CREDS = get_creds()
    new_rta_records = get_rta_records(SHEETS_CREDS)
    new_ss_records = get_ss_records(SHEETS_CREDS)

    # Stop execution if there are errors retrieving data from
    # either spreadsheet or there are no new records to update
    if new_rta_records == None:
        msg = 'Failed to retrieve data from RTA spreadsheet!'
        log.add_error_message(msg)
        prefix_print(f'{bcolors.FAIL}Error:{bcolors.ENDC} {msg}')
        return
    if new_ss_records == None:
        msg = 'Failed to retrieve data from single star spreadsheet!'
        log.add_error_message(msg)
        prefix_print(f'{bcolors.FAIL}Error:{bcolors.ENDC} {msg}')
        return
    if new_rta_records == [] and new_ss_records == []:
        log.set_nothing_to_update(True)
        prefix_print('No new single star or RTA records to update...')
        return
    # Make new records lists parallel (i.e. each
    # star will have its own entry in both lists)
    if new_rta_records == []:
        prefix_print('No new RTA records to update...')
    else:
        for i, new_record in enumerate(new_rta_records[:]):
            if new_record:
                # Check if the name of the current RTA record
                # is also present in the SS records list
                if new_record[2] not in [record[2] for record in set(new_ss_records) if record]:
                    new_ss_records.insert(i, None)
    if new_ss_records == []:
        prefix_print('No new single star records to update...')
    else:
        for i, new_record in enumerate(new_ss_records[:]):
            if new_record:
                # Check if the name of the current SS record
                # is also present in the RTA records list
                if new_record[2] not in [record[2] for record in set(new_rta_records) if record]:
                    new_rta_records.insert(i, None)

    try:
        SESSION = requests.Session()
        # Login to Ukikipedia
        BOT_USER = ''
        BOT_PASS = ''
        response = get_login_response(SESSION, BOT_USER, BOT_PASS)
        if response['login']['result'] == 'Success':
            print(f'{bcolors.OKGREEN}Success{bcolors.ENDC}')
        else:
            log.set_error_message(f'Failed to login to {BOT_USER}!')
            log.out()
            print(f'{bcolors.FAIL}Failed{bcolors.ENDC}')
            return

        # Iterate over new RTA and single star records. The replace_record functions can set both an RTA
        # and a single star record in a single edit request to a given star page, but will only act upon
        # the arguments they're given. So if there is only an RTA or single star record to update for a
        # given star's page, then the other record will be passed as None to the appropriate replace_record
        # function (as per the fillvalue in the zip_longest call). 
        for new_rta_record, new_ss_record in zip_longest(new_rta_records, new_ss_records, fillvalue=None):

            time.sleep(0.5)

            # Get star name from whichever record isn't currently None
            new_record_star_name = new_rta_record[2] if new_rta_record != None else new_ss_record[2]
            # Special case handling control variables
            is_bowser_course_record = False
            is_bowser_reds_record = False
            is_first_multi_100c_record = False
            is_second_multi_100c_record = False

            # Format bowser stage records appropriately and
            # update the respective control variable
            if new_record_star_name[:6] == 'Bowser':
                if 'Course' in new_record_star_name:
                    new_record_star_name = new_record_star_name[:-9]
                    is_bowser_course_record = True
                else:
                    new_record_star_name = new_record_star_name[:-10]
                    is_bowser_reds_record = True
            # Special case handling for multi-strategy 100c stars
            elif new_rta_record and '100' in new_record_star_name:
                if 2 not in [i for i in new_rta_record]:
                    is_first_multi_100c_record = True
                else:
                    is_second_multi_100c_record = True

            # If the current star is the second record for a
            # multi-strategy 100c star, add '2' to the current
            # star name in the log
            if is_second_multi_100c_record:
                log.add_star_name(new_record_star_name + ' 2', 'RTA')
            else:
                log.add_star_name(new_record_star_name, ('RTA' if new_rta_record != None else 'SS'))

            # Get current star's RTA Guide page text and some other
            # necessary parameters needed to edit the page
            page_text, BASE_TIMESTAMP, START_TIMESTAMP, CSRF_TOKEN = \
                get_star_page_response(SESSION, new_record_star_name)
            # Handle failure to retrieve page text
            if not '{{speedrun_infobox' in page_text and not '{{speedrun_infobox_bowser_level' in page_text:
                msg = f"Couldn't get page content for '{new_record_star_name}'!"
                log.add_update_result(msg)
                prefix_print(f"{bcolors.FAIL}Error{bcolors.ENDC}: {msg} Skipping record...")
                # Don't save record to local file if it fails to update...
                if new_rta_record:
                    set_rta_record_not_to_save(new_rta_record)
                if new_ss_record:
                    set_ss_record_not_to_save(new_ss_record)
                continue

            # Bowser stage records handling...
            if is_bowser_course_record:
                page_text, summary = replace_record_bowser(page_text, new_rta_course_record=new_rta_record, new_ss_course_record=new_ss_record)
            elif is_bowser_reds_record:
                page_text, summary = replace_record_bowser(page_text, new_rta_reds_record=new_rta_record, new_ss_reds_record=new_ss_record)
            # Multi-strategy 100c records handling...
            elif is_first_multi_100c_record:
                page_text, summary = replace_record_multi_100c(page_text, new_rta_100c_record_1=new_rta_record, new_ss_record=new_ss_record)
            elif is_second_multi_100c_record:
                page_text, summary = replace_record_multi_100c(page_text, new_rta_100c_record_2=new_rta_record, new_ss_record=new_ss_record)
            # Normal record handling
            else:
                page_text, summary = replace_record(page_text, new_rta_record=new_rta_record, new_ss_record=new_ss_record)

            # page_text will be None if the record is
            # already updated (or has a faster time due
            # to me ignoring the extensions sheet for now), 
            # so just skip ahead to the next record in the list
            if page_text == None:
                msg = f"Page 'RTA Guide/{new_record_star_name}' is either already updated or has a faster time than was provided!"
                log.add_update_result(f'"{msg}"')
                prefix_print(f"{msg} Skipping record...")
                continue

            time.sleep(0.5)

            response = get_edit_star_page_response(SESSION, new_record_star_name, page_text, summary, \
                                                   CSRF_TOKEN, BASE_TIMESTAMP, START_TIMESTAMP)
            if response['edit']['result'] == 'Success':
                log.add_update_result('Success')
                print(f'{bcolors.OKGREEN}Success{bcolors.ENDC}')
            # Handle failure to edit page text
            else:
                log.add_update_result(f"\"Failed to edit page 'RTA Guide/{new_record_star_name}'\"")
                print(f'{bcolors.FAIL}Failed{bcolors.ENDC}')
                # Don't save record to local file if it fails to update...
                if new_rta_record:
                    set_rta_record_not_to_save(new_rta_record)
                if new_ss_record:
                    set_ss_record_not_to_save(new_ss_record)

    except (Exception, KeyboardInterrupt) as e:
        # Don't save record to local file if it fails to update...
        if new_rta_record:
            set_rta_record_not_to_save(new_rta_record)
        else:
            set_ss_record_not_to_save(new_ss_record)
        # Don't print traceback for KeyboardInterrupt
        if type(e).__name__ != 'KeyboardInterrupt':
            print(traceback.format_exc())
        prefix_print(f'{bcolors.FAIL}Error{bcolors.ENDC}: {type(e).__name__} occurred! Exiting...')
        return
    finally:
        # Save records and output log
        # at the end of the session
        save_rta_records()
        save_ss_records()
        # Log and print total execution time
        exec_time = (time.time() - t1)
        log.set_execution_time(exec_time)
        log.out()
        prefix_print(f'{bcolors.OKGREEN}Done{bcolors.ENDC}: took {exec_time:.2f}s')

if __name__ == '__main__':
    main()
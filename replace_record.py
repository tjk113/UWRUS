import re

from get_records import remove_mins_place

def replace_record(cur_page_text: str, new_rta_record: tuple[str, str] = None, \
                   new_ss_record: tuple[str, str] = None) -> tuple[str, str]:
    '''
    Replaces specified records in page text (specify record params in call),
    and returns the new page text and edit summary
    '''
    # TODO: handle bowser stage infoboxes and 100c pages
    # Updating multiple wrs in one category at once (multiple
    # rta or ss records in the records list), i'll probably
    # just make two separate edits (we'll see tho)

    records_pattern = re.compile(r'rta_record=(?P<rta_record>.+)\n'
                                 +'\|ss_record=(?P<ss_record>.+)\n')
    record_time_pattern = re.compile(r'\d+\.\d+')
    parsed_records = records_pattern.search(cur_page_text)
    edit_summary = "Updated WR(s) '"

    new_records = [i for i in [new_rta_record, new_ss_record] if i != None]
    cur_records = []
    if new_rta_record:
        cur_records.append(parsed_records.group('rta_record'))
    if new_ss_record:
        cur_records.append(parsed_records.group('ss_record'))
    parsed_records = parsed_records.group() # we only need this as a string now

    # If somehow replace_record is called for a page
    # that is already updated (or has a faster time due
    # to me ignoring the extensions sheet for now),
    # don't bother updating it again.
    parsed_record_times = record_time_pattern.findall(parsed_records)
    for new_record, cur_record_time in zip(new_records, parsed_record_times):
        new_record_time = new_record[0]
        if new_record_time == cur_record_time:
            return
        if ':' in new_record_time:
            new_record_time = remove_mins_place(new_record_time)
        if 'IGT' in new_record_time:
            new_record_time = new_record_time[:-6]
        new_record_time = float(new_record_time)
        if ':' in cur_record_time:
            cur_record_time = remove_mins_place(cur_record_time)
        if 'IGT' in cur_record_time:
            cur_record_time = cur_record_time[:-6]
        cur_record_time = float(cur_record_time)
        if new_record_time > cur_record_time:
            return

    # Replace provided record tuples with properly formatted
    # strings, and update those records in the page text
    new_page_text = cur_page_text
    for cur_record, new_record in zip(cur_records, new_records):
        # Note: this can't handle a scenario in which
        # there is a new rta record and a new best available
        # video. To handle this, there would need to be
        # logic that could search the whole spreadsheet
        # by row for the matching video link, and then use
        # that cell's time in place of new_record[0] in the
        # time comparison below
        cur_record_time = record_time_pattern.search(cur_record).group()
        new_record_time = new_record[0]
        if 'Best Available Video' in cur_record:
            # If the best time currently has no video
            # and video and this new entry still isn't
            # faster, just replace the video
            if float(new_record[0]) > float(cur_record_time):
                new_record = f'{new_record[0]} [{new_record[1]} (Best Available Video)]'
            else:
                new_record = f'[{new_record[1]} {new_record[0]}]'
        else:
            new_record = f'[{new_record[1]} {new_record[0]}]'
        edit_summary += cur_record_time + "' to '" + new_record_time + "', '"
        # Update parsed_records with the newly added record, so the next
        # iteration will be looking for the correct string in the page text,
        # and update the page text with the new parsed_records
        new_parsed_records = parsed_records.replace(cur_record, new_record)
        new_page_text = new_page_text.replace(parsed_records, new_parsed_records)
        parsed_records = new_parsed_records
    edit_summary = edit_summary[:-3] # remove final hanging ", '"

    return new_page_text, edit_summary

# Test Driver Code
if __name__ == '__main__':
    page_text = ''
    with open('test_page.txt', 'r') as file:
        for line in file:
            page_text += line

    new_rta_wr = ('17.40', 'https://www.youtube.com/watch?v=W72cyc5sESo')
    new_ss_wr = ('8.20', 'https://www.youtube.com/watch?v=GznIqiD5bX8')

    new_text, edit_summary = replace_record(page_text, new_rta_record=new_rta_wr, new_ss_record=new_ss_wr)
    print(edit_summary)
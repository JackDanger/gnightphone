"""
G'night, Phone!

Every night this sends a text to your phone and asks you whatever
questions you've configured. You respond before bed and then put the
damned phone away until you get the rest you need.

"""
from __future__ import print_function
import json
from datetime import datetime
from flask import Flask
from flask import request
import os
import bugsnag
from bugsnag.flask import handle_exceptions

from twilio.rest import Client as Twilio

import gspread
from oauth2client.service_account import ServiceAccountCredentials

BUGSNAG_API_KEY = os.environ['BUGSNAG_API_KEY']
TWILIO_FROM_NUMBER = os.environ['TWILIO_FROM_NUMBER']
TO_NUMBER = os.environ['TO_NUMBER']

# Ensure the environment has the right credentials
os.environ['TWILIO_ACCOUNT_SID']
os.environ['TWILIO_AUTH_TOKEN']

GOOGLE_SHEETS_CREDENTIALS = os.environ['GOOGLE_SHEETS_CREDENTIALS']

# use gsheet_creds to create a client to interact with the Google Drive API
scopes = ['https://spreadsheets.google.com/feeds']
# CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
gsheet_creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_SHEETS_CREDENTIALS), scopes)

# Details about our spreadsheet layout
NumberOfQuestions = 8
SkipColumns = 1
SleepHourColumn = SkipColumns + NumberOfQuestions + 1

client = gspread.authorize(gsheet_creds)
spreadsheet = client.open_by_key("1ri5JklpBiTrFOQ1WiT2nQCGdBIOdq57B37coVDlSzh8")
# Hardcoding the year at boot time. Let's restart this every year, yeah?
worksheet = spreadsheet.worksheet(datetime.now().strftime("%Y"))
header_row = worksheet.range(1, SkipColumns + 1, 1, SkipColumns + NumberOfQuestions)


def update_next_cell(value):
    now = datetime.utcnow()
    if now.hour < 15:
        # It's past midnight
        date = datetime(now.year, now.month, now.day-1).strftime("%Y-%m-%d")
        sleep_hour = 24 + now.hour
    else:
        date = now.strftime("%Y-%m-%d")
        sleep_hour = now.hour

    today_row_num = worksheet.findall(date)[0].row
    today = worksheet.range(today_row_num, SkipColumns + 1, today_row_num, SleepHourColumn)

    for index in range(len(header_row)):
        print('index: {}, current value: {}'.format(index, today[index].value))
        # Get the next cell that hasn't been filled in yet
        if not today[index].value:
            header = header_row[index]

            row = today_row_num
            col = index + 2  # There's a leftmost column that's just dates and it's also 1-indexed
            to_update = (row, col, value,)
            break

    # `index` is now the location of the last answered question
    if index < (len(header_row) - 1):
        next_message = "{}) {}".format(index + 2, header_row[index + 1].value)
    else:
        next_message = "You're all set. Put your phone away and sleep."

    sent = Twilio().messages.create(
            to=TO_NUMBER,
            from_=TWILIO_FROM_NUMBER,
            body=next_message)
    print(sent)

    if to_update:
        print('updating "{}" at {},{} with {}'.format(header.value, row, col, value))
        worksheet.update_cell(*to_update)

    # If the bedtime is not recorded yet, set it right away. The moment
    # the person texts back is considered bedtime
    if not today[-1].value:
        worksheet.update_cell(today_row_num, SleepHourColumn, sleep_hour)


# Configure Bugsnag
bugsnag.configure(
  api_key=BUGSNAG_API_KEY,
  project_root="/app",
)

app = Flask(__name__)
handle_exceptions(app)


@app.route('/')
def root():
    return """
        <h2>
            <a href="https://github.com/JackDanger/gnightphone">G'night, phone!</a>
        </h2>
    """


@app.route('/collect-answers')
def collect_answers():
    first_question = header_row[0].value
    body = "G'night phone! Answer these {} ?s and go to sleep.\n 1) {}".format(
            NumberOfQuestions, first_question)
    sent = Twilio().messages.create(
            to=TO_NUMBER,
            from_=TWILIO_FROM_NUMBER,
            body=body)
    print(sent)
    return '', 200


@app.route('/<path>', methods=['POST'])
def incoming_text(path):
    message = request.form.get('Body')
    update_next_cell(message)
    return '', 200


@app.route('/_status')
def status():
    return json.dumps({'status': 'ok'}, indent=4), 200

if __name__ == "__main__":
    print("starting")
    app.run(host='0.0.0.0', port=5000)

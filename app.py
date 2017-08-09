"""
G'night, Phone!

Every night this sends a text to your phone and asks you whatever
questions you've configured. You respond before bed and then put the
damned phone away until you get the rest you need.

"""
from __future__ import print_function
import json
from datetime import datetime
import pytz
from flask import Flask
from flask import request
from flask_twisted import Twisted
import os
import bugsnag
from bugsnag.flask import handle_exceptions

from cached_property import cached_property_with_ttl

from twilio.rest import Client as Twilio

import gspread
from gspread.exceptions import RequestError
from oauth2client.service_account import ServiceAccountCredentials

BUGSNAG_API_KEY = os.environ['BUGSNAG_API_KEY']
TWILIO_FROM_NUMBER = os.environ['TWILIO_FROM_NUMBER']
TO_NUMBER = os.environ['TO_NUMBER']
GOOGLE_SPREADSHEET_ID = os.environ['GOOGLE_SPREADSHEET_ID']

# Ensure the environment has the right credentials
os.environ['TWILIO_ACCOUNT_SID']
os.environ['TWILIO_AUTH_TOKEN']

# Details about our spreadsheet layout
NumberOfQuestions = 8
SkipColumns = 1
SleepHourColumn = SkipColumns + NumberOfQuestions + 1
HourOfDayToConsiderCutoffForReportingPreviousDay = 18

GOOGLE_SHEETS_CREDENTIALS = os.environ['GOOGLE_SHEETS_CREDENTIALS']


class Spreadsheet():

    # use gsheet_creds to create a client to interact with the Google Drive API
    scopes = ['https://spreadsheets.google.com/feeds']
    gsheet_creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_SHEETS_CREDENTIALS), scopes)
    pst = pytz.timezone('US/Pacific')

    @property
    def end_of_day(self):
        now = pst.localize(datetime.now())
        if now.hour < 19:
            # It's past midnight of the next day
            return datetime(now.year, now.month, now.day-1, now.hour)

    @property
    def date(self):
        return self.end_of_day.strftime("%Y-%m-%d")

    @cached_property_with_ttl(ttl=60*60)
    def worksheet(self):
        # Hardcoding the year at boot time. Let's restart this every year, yeah?
        return self.spreadsheet.worksheet(datetime.now().strftime("%Y"))

    @property
    def client(self):
        return gspread.authorize(Spreadsheet.gsheet_creds)

    @cached_property_with_ttl(ttl=60*60)
    def spreadsheet(self):
        return self.client.open_by_key(GOOGLE_SPREADSHEET_ID)

    @cached_property_with_ttl(ttl=60*60)
    def header_row(self):
        return self.worksheet.range(1, SkipColumns + 1, 1, SkipColumns + NumberOfQuestions)

    @cached_property_with_ttl(ttl=60*60)
    def today_row_num(self):
        return self.worksheet.findall(self.date)[0].row

    @property
    def today(self):
        return self.worksheet.range(self.today_row_num, SkipColumns + 1, self.today_row_num, SleepHourColumn)

    @property
    def todays_values(self):
        return [
           "{}: {}".format(
               self.header_row[SkipColumns + i].value,
               self.today[SkipColumns + i].value)
           for i in range(NumberOfQuestions)
        ]



spreadsheet = Spreadsheet()


def update_next_cell(value):
    for index in range(len(spreadsheet.header_row)):
        print('index: {}, current value: {}'.format(index, spreadsheet.today[index].value))
        # Get the next cell that hasn't been filled in yet
        if not spreadsheet.today[index].value:
            header = spreadsheet.header_row[index]

            row = spreadsheet.today_row_num
            col = index + 2  # There's a leftmost column that's just dates and it's also 1-indexed

            print('updating "{}" at {},{} with {}'.format(header.value, row, col, value))
            spreadsheet.worksheet.update_cell(row, col, value)
            break

    # `index` is now the location of the last answered question
    if index < len(spreadsheet.header_row):
        next_message = "{}) {}".format(index + 2, spreadsheet.header_row[index + 1].value)
    else:
        next_message = "You're all set. Put your phone away and sleep."

    sent = Twilio().messages.create(
            to=TO_NUMBER,
            from_=TWILIO_FROM_NUMBER,
            body=next_message)
    print(sent)



# Configure Bugsnag
bugsnag.configure(
  api_key=BUGSNAG_API_KEY,
  project_root="/app",
)

app = Flask(__name__)
handle_exceptions(app)
twisted = Twisted(app)


@app.route('/')
def root():
    return """
        <h2>
            <a href="https://github.com/JackDanger/gnightphone">G'night, phone!</a>
        </h2>
    """


@app.route('/collect-answers')
def collect_answers():
    """
    Configured to run every day via: https://cron-job.org
    """
    first_question = spreadsheet.header_row[0].value
    message = "G'night phone! Answer these {} ?s and go to sleep.\n 1) {}".format(
            NumberOfQuestions, first_question)
    print(deliver_text(message))
    return '', 200


@app.route('/<path>', methods=['POST'])
def incoming_text(path):
    message = request.form.get('Body')
    if message == "?":
        deliver_text(','.join(spreadsheet.todays_values))
    else:
        update_next_cell(message)
    return '', 200


@app.route('/_status')
def status():
    return json.dumps({'status': 'ok'}, indent=4), 200


def deliver_text(content):
    return Twilio().messages.create(
            to=TO_NUMBER,
            from_=TWILIO_FROM_NUMBER,
            body=content)


if __name__ == "__main__":
    print("starting")
    twisted.run(host='0.0.0.0', port=5000, debug=True)

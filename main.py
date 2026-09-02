import os

import dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

dotenv.load_dotenv()

class GoogleCalendar:
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, credentials_filename, calendar_id):
        credentials = service_account.Credentials.from_service_account_file(
            filename=credentials_filename, scopes=self.SCOPES
        )
        self.service = build('calendar', 'v3', credentials=credentials)
        self.calendar_id = calendar_id

    def insert_event(self, event):
        self.service.events().insert(calendarId=self.calendar_id, body=event).execute()


def main():
    file_path = os.getenv('CREDENTIALS_FILEPATH')
    if file_path is None:
        raise ValueError('Credentials file not provided')
    if not os.path.isfile(file_path):
        raise FileNotFoundError('Credentials file not found')

    calendar_id = os.getenv('CALENDAR_ID')
    if calendar_id is None:
        raise ValueError('Calendar ID not provided')

    calendar = GoogleCalendar(credentials_filename=file_path, calendar_id=calendar_id)

if __name__ == '__main__':
    main()

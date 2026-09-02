import os

import dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

dotenv.load_dotenv()

class GoogleCalendar:
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, credentials_filename):
        credentials = service_account.Credentials.from_service_account_file(
            filename=credentials_filename, scopes=self.SCOPES
        )
        self.service = build('calendar', 'v3', credentials=credentials)

def main():
    file_path = os.getenv('CREDENTIALS_FILEPATH')
    if file_path is None:
        print('Credentials file not provided')
        return
    if not os.path.isfile(file_path):
        print('Credentials file not found')
        return

    calendar = GoogleCalendar(credentials_filename=file_path)
    calendar_list = calendar.service.calendarList().list().execute()
    print(calendar_list)

if __name__ == '__main__':
    main()

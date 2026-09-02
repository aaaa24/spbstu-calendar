import os
from datetime import timedelta, timezone, datetime

import dotenv
import requests
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
        print(event)
        self.service.events().insert(calendarId=self.calendar_id, body=event).execute()


class Schedule:
    BASE_URL = 'https://ruz.spbstu.ru/api/v1/ruz/scheduler'

    def __init__(self, schedule_id):
        self.schedule_id = schedule_id

    def get_week_schedule(self, date=None):
        url = f'{self.BASE_URL}/{self.schedule_id}'
        date_str = date.strftime('%Y-%m-%d') if date else None
        response = requests.get(url, params={'date': date_str})
        response.raise_for_status()
        return response.json()

    def get_weeks_schedule(self, weeks_count=None):
        weeks_schedule = []
        for i in range(weeks_count):
            date = datetime.today() + timedelta(weeks=i)
            weeks_schedule.append(self.get_week_schedule(date))
        return weeks_schedule

    @staticmethod
    def create_iso8601(date_str, time_str):
        dt_local = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
        result = dt_local.strftime('%Y-%m-%dT%H:%M:%S') + '+03:00'
        return result

    @staticmethod
    def create_description(lesson):
        rename_type_names = {
            'Лекции': 'Лекция'
        }

        description_lines = []
        if lesson['typeObj']:
            description_lines.append(rename_type_names.get(lesson['typeObj']['name']) or lesson['typeObj']['name'])
        if lesson['groups']:
            description_lines.append(f'Группы: {', '.join(sorted([group['name'] for group in lesson['groups']]))}')
        if lesson['teachers']:
            description_lines.append(', '.join([teacher['full_name'] for teacher in lesson['teachers']]))
        if lesson['lms_url']:
            description_lines.append(f'<a href={lesson['lms_url']}>СДО</a>')
        description = '\n'.join(description_lines)
        return description

    @staticmethod
    def create_events_from_week_schedule(week_schedule):
        events = []
        for day in week_schedule['days']:
            for lesson in day['lessons']:
                event = {
                    'summary': lesson['subject'],
                    'description': Schedule.create_description(lesson),
                    'location': ';'.join(
                        [', '.join((auditory['building']['abbr'], auditory['name'])) for auditory in lesson['auditories']]
                    ),
                    'start': {
                        'dateTime': Schedule.create_iso8601(day['date'], lesson['time_start']),
                    },
                    'end': {
                        'dateTime': Schedule.create_iso8601(day['date'], lesson['time_end']),
                    },
                }
                events.append(event)
        return events


def insert_event(calendar, schedule):
    week_schedule = schedule.get_week_schedule()
    event = schedule.create_events_from_week_schedule(week_schedule)[0]
    calendar.insert_event(event)


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

    schedule_id = os.getenv('SCHEDULE_ID')
    if schedule_id is None:
        raise ValueError('Schedule ID not provided')

    schedule = Schedule(schedule_id=schedule_id)

    insert_event(calendar, schedule)

if __name__ == '__main__':
    main()

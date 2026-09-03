import os
from datetime import timedelta, datetime

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
        self.service.events().insert(calendarId=self.calendar_id, body=event).execute()

    def get_events_list(self, *, time_min=None, time_max=None):
        events = []

        time_min_str = time_min and Schedule.datetime_to_str(time_min)
        time_max_str = time_max and Schedule.datetime_to_str(time_max)

        response = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min_str, timeMax=time_max_str
        ).execute()
        events.extend(response['items'])

        while response.get('nextPageToken'):
            response = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min_str, timeMax=time_max_str,
                pageToken=response.get['nextPageToken']
            ).execute()
            events.extend(response['items'])

        return events


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

    def get_weeks_schedule(self, weeks_count=1):
        weeks_schedule = []
        for i in range(weeks_count):
            date = datetime.today() + timedelta(weeks=i)
            weeks_schedule.append(self.get_week_schedule(date))
        return weeks_schedule

    @staticmethod
    def datetime_to_str(dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%S') + '+03:00'

    @staticmethod
    def create_str_iso(date_str, time_str):
        dt_local = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
        result = Schedule.datetime_to_str(dt_local)
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
                        'dateTime': Schedule.create_str_iso(day['date'], lesson['time_start']),
                    },
                    'end': {
                        'dateTime': Schedule.create_str_iso(day['date'], lesson['time_end']),
                    },
                }
                events.append(event)
        return events


def update_calendar(calendar, schedule, weeks_count=1):
    weeks_schedule = schedule.get_weeks_schedule(weeks_count)

    schedule_events = []
    for week_schedule in weeks_schedule:
        schedule_events.extend(schedule.create_events_from_week_schedule(week_schedule))

    now = datetime.now()
    time_min = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    calendar_events = calendar.get_events_list(time_min=time_min)

    comparison = compare_events(calendar_events, schedule_events)
    print(comparison)


def compare_events(calendar_events, schedule_events):
    calendar_events = calendar_events.copy()
    schedule_events = schedule_events.copy()
    i = 0
    while i < len(schedule_events):
        j = 0
        while j < len(calendar_events):
            formatted_calendar_event = {
                'summary': calendar_events[j]['summary'],
                'description': calendar_events[j]['description'],
                'location': calendar_events[j]['location'],
                'start': {'dateTime': calendar_events[j]['start'].get('dateTime')},
                'end': {'dateTime': calendar_events[j]['end'].get('dateTime')}
            }
            if schedule_events[i] == formatted_calendar_event:
                del schedule_events[i]
                del calendar_events[j]
                break
            else:
                j += 1
        else:
            i += 1

    return {'delete': [calendar_event['id'] for calendar_event in calendar_events], 'add': schedule_events}


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

    update_calendar(calendar, schedule)


if __name__ == '__main__':
    main()

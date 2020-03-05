from datetime import datetime

time_format = '%Y-%m-%dT%H:%M:%SZ'

# Parse zendesk's date format
def parse_time(date):
    return datetime.strptime(date, time_format)

def to_string(date):
    return date.strftime(time_format)
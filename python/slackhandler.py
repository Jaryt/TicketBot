import os
import json, requests
import slack
import certifi
import ssl

token = os.getenv("SLACK_TOKEN")
slack_url = 'https://slack.com/api/'
channels_key = 'conversations.list'
messages_key = 'chat.postMessage'
users_key = 'users.list'
client = None
channel_id = ''

def slack_get(api, after):
    response = requests.get(slack_url + api + '?token=' + token + after)

    if response.status_code != 200:
        print('Status:', response.status_code, 'Problem with the', api, 'request. Exiting.')
        exit()

    return response.json()

def get_paged(api, func, params):
    cursor = ''

    while True:
        response_json = slack_get(api, cursor)

        if func(response_json, params):
            return True

        if 'response_metadata' in response_json:
            next_cursor = response_json['response_metadata']['next_cursor']

            if next_cursor:
                cursor = '&cursor=' + next_cursor
            else:
                return False


def check_channels(response_json, channel_name):
    global channel_id

    for channel in response_json['channels']:
        if channel['name'] == channel_name:
            channel_id = channel['id']
            
            return True

    return False


def set_channel(channel_name):
    get_paged(channels_key, check_channels, channel_name)


def add_users(users_json, emails):
    for user in users_json['members']:
        profile = user['profile']

        if 'email' in profile:
            email = profile['email']

            if email != None:
                email = email.lower()

            if email in emails:
                emails[email] = user['name']


# Takes a dict of emails and sets their values to the slack username
def lookup_emails(emails):
    get_paged(users_key, add_users, emails)

    return emails


def join():
    global client

    ssl_context = ssl.create_default_context(cafile=certifi.where())

    client = slack.WebClient(
        token=token, ssl=ssl_context
    )


def send_message(message):
    global client

    client.chat_postMessage(
        channel=channel_id,
        link_names=1,
        text=message
    )
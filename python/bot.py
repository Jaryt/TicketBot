#!/usr/bin/python

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import grequests
import requests
import json
import sys
import os
import parse
import zendesk as zd
import slackhandler as slack


user = ''
domain = ''
view = ''
channel = ''
min_days = 5  # Min days since we reply to trigger log
default_offset = -28800  # PST offset in seconds from UTC
check_tz = False
ping = True
weekday = False

tickets_url = "/agent/tickets/"


def setup(argv):
    global user, domain, view, channel
    global check_tz, ping, weekday

    user = argv[1]
    domain = argv[2]
    view = argv[3]
    channel = argv[4]
    check_tz = argv[5].lower() == 'true'
    ping = argv[6].lower() == 'true'
    weekday = datetime.now().weekday() < 5


# grammatical function
def multi(single, val):
    return str(val) + (single + 's' if val != 1 else single)


# process output for an agent's list of tickets
def process_ticket_list(tickets):
    ticket_list = ""
    body = '{months}{days} since we replied to `{link}`\n'

    for ticket_id in tickets:
        ticket = tickets[ticket_id]
        days = ticket['days']
        months = ticket['months']
        month_str = ""
        day_str = ""

        if months > 0:
            month_str = multi(" month", months)

        if days > 0:
            if months > 0:
                day_str = " and "
            day_str += multi(" day", days)

        link = zd.get_zendesk_url() + tickets_url + ticket_id
        ticket_list += body.format(months=month_str, days=day_str, link=link)

    return ticket_list


def check_timezone(tz_offset):
    time = datetime.utcnow() + timedelta(seconds=tz_offset)

    return time.hour >= 9 and time.hour < 12


# Get ticket data and print it out
def process_tickets(agent_tickets, agents, extra_data):
    out = ""

    for agent_id in agent_tickets:
        if agent_id == 'None':
            header = 'Tickets that have no assignee:\n{tickets}\n'
        else:
            header = 'Tickets for {name}:\n{tickets}\n'

        ticket_list = process_ticket_list(agent_tickets[agent_id])
        agent = agents[agent_id]
        name = agent['name']
        tz_offset = default_offset

        if 'email' in agent:
            email = agent['email']

            if email in extra_data and extra_data[email]:
                data = extra_data[email]

                if weekday and ping:
                    name = '@' + data['name']

                if 'tz_offset' in data:
                    tz_offset = data['tz_offset']

        if check_timezone(tz_offset) or not check_tz:
            out += header.format(name=name, tickets=ticket_list)

    return out


def get_agent_tickets(tickets):
    agent_tickets = {}

    for ticket_id in tickets:
        ticket = tickets[ticket_id]
        assignee_id = ticket['assignee_id']
        comments = ticket['comments']
        last_replies = comments['last_replies']

        if 'agents' in last_replies:
            last_reply = last_replies['agents']
            created_at = last_reply['comment']['created_at']

            diff = relativedelta(datetime.today(), created_at)

            if diff.days >= min_days or diff.months != 0:
                delta = {'days': diff.days, 'months': diff.months}

                if assignee_id in agent_tickets:
                    agent_tickets[assignee_id][ticket_id] = delta
                else:
                    agent_tickets[assignee_id] = {ticket_id: delta}

    return agent_tickets


def get_emails(users):
    emails = {}
    agents = users['agents']

    for user_id in agents:
        user = agents[user_id]
        email = user['email']

        if 'email' in user and email != None:
            emails[email.lower()] = None

    return emails


# Run ticket collection and process loop
def loop():
    zd.set_credentials(user, domain)
    zd.load_tickets_view(view)
    zd.load_ticket_replies()
    zd.load_user_data()
    zd.load_last_replies()

    tickets = zd.get_tickets()
    users = zd.get_users()

    slack.join()
    slack.set_channel(channel)

    extra_data = slack.lookup_emails(get_emails(users))
    agent_tickets = get_agent_tickets(tickets)

    if tickets:
        result = process_tickets(agent_tickets, users['agents'], extra_data)

    if not tickets or not result:
        result = "No old tickets found for this loop!"

    slack.send_message(result)


if __name__ == '__main__':
    setup(sys.argv)
    loop()

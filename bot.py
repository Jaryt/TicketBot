#!/usr/bin/python
from datetime import datetime, relativedelta
import requests, json, sys
import os

user = ''
token = os.getenv("ZENDESK_TOKEN")
url = ''
ticketsurl = '' 
usersurl = '/api/v2/users/show_many.json?ids='
ticketlink = "/agent/tickets/"

def setup(argv):
    global user, url, ticketsurl
    user = argv[1]
    url = 'https://' + argv[2] + '.zendesk.com'
    ticketsurl = '/api/v2/views/' + argv[3] + '/tickets.json'


# Zendesk request and oauth
def zendesk_get(api):
    response = requests.get(url + api, auth=(user + '/token', token))

    if response.status_code != 200:
        print('Status:', response.status_code, 'Problem with the request. Exiting.')
        exit()

    return response.json()


# Getting ticket and user id list from zendesk tickets api endpoint
def get_ticket_data(jsondata):
    users = ''
    tickets = {}

    for val in jsondata['tickets']:
        agent = val['assignee_id']

        if updated < date:
            ticket = { 'id': val['id'], 'updated_at': val['updated_at'], 'agent': None }

            if agent not in tickets:
                if agent != None:
                    if users:
                        users += ',' 
                    users += str(agent)
                tickets[agent] = [ticket]
            else:
                tickets[agent].append(ticket)

    return users, tickets


# Setting usernames from zendesk user api endpoint
def set_usernames(jsondata, tickets):
    for user in jsondata['users']:
        for ticket in tickets[user['id']]:
            ticket['agent'] = user['name']


def multi(single, val):
    return single + 's' if val != 1 else single


# Get ticket data and print it out
def process_tickets(tickets):
    out = ""
    for agent in tickets.keys():
        ticket_list = ""
        header = """Ticket for {name}:
    {tickets}"""
        body = '{months} and {days} since we replied to {link}\n'

        for ticket in tickets[agent]:
            name = ticket['agent']

            if name is None:
                header = 'Tickets that have no assignee:\n{tickets}'

            updated = datetime.strptime(ticket['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
            diff = relativedelta.relativedelta(datetime.today(), updated)
            days = diff.days
            months = diff.months

            if months > 0:
                month_str = str(month) + multi(" month", month)

            if days > 0:
                day_str += str(day) + multi(" day", day)

            link = url + ticketlink + str(ticket['id'])
            ticket_list += body.format(months=month_str, day=dat_str, link=link)

        out += header.format(name=name,tickets=ticket_list)
    return out

# Run ticket collection and process loop
def loop():
    tickets_json = zendesk_get(ticketsurl)
    users, tickets = get_ticket_data(tickets_json)
    users_json = zendesk_get(usersurl + users)
    set_usernames(users_json, tickets)

    if tickets:
        result = process_tickets(tickets)
    else:
        result = "No tickets found!"

    print(result)

if __name__ == '__main__':
    setup(sys.argv)
    loop()

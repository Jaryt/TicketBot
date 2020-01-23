#!/usr/bin/python

from datetime import datetime, timedelta
import requests, json, sys

user = ''
token = ''
url = ''
ticketsurl = '' 
usersurl = '/api/v2/users/show_many.json?ids='

def main(argv):
    global user, token, url, ticketsurl
    user = argv[1]
    token = argv[2]
    url = 'https://' + argv[3] + '.zendesk.com'
    print(url)
    ticketsurl = '/api/v2/views/' + argv[4] + '/tickets.json'


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
    date = datetime.today() - timedelta(days=7)

    for val in jsondata['tickets']:
        agent = val['assignee_id']
        updated = datetime.strptime(val['updated_at'][:-10], '%Y-%m-%d')

        if updated < date:
            ticket = { 'id': val['id'], 'updated_at': updated }

            if agent not in tickets:
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


# Get ticket data and print it out
def process_tickets():
    


# Run ticket collection and process loop
def loop():
    tickets_json = zendesk_get(ticketsurl)
    users, tickets = get_ticket_data(tickets_json)
    users_json = zendesk_get(usersurl + users)
    set_usernames(users_json, tickets)
    process_tickets(tickets)

main(sys.argv)
loop()

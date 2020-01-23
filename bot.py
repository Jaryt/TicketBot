#!/usr/bin/python

from datetime import datetime, timedelta
import requests, json, sys

user = ''
token = ''
url = ''
ticketsurl = '' 
usersurl = '/api/v2/users/show_many.json?ids='
ticketlink = "/agent/tickets/"

def main(argv):
    global user, token, url, ticketsurl
    user = argv[1]
    token = argv[2]
    url = 'https://' + argv[3] + '.zendesk.com'
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
            ticket = { 'id': val['id'], 'updated_at': updated, 'agent': None }

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


def multi(val):
    return 's' if val != 1 else ''

# Get ticket data and print it out
def process_tickets(tickets):
    for agent in tickets.keys():
        out = ''

        for ticket in tickets[agent]:
            name = ticket['agent']

            if not out:
                if name is None:
                    out = 'Tickets that have no assignee:\n'
                else:
                    out = 'Tickets for ' + name + ':\n'

            time_dif = datetime.today() - ticket['updated_at']
            
            month_l = 31
            day = time_dif.days % month_l
            month = int(time_dif.days / month_l)

            if month > 0:
                out += str(month) + ' month' + multi(month) + ' '

            if day > 0:
                if month > 0: 
                    out += 'and '
                out += str(day) + ' day' + multi(day) + ' '

            out += 'since we last replied to ' + url + ticketlink + str(ticket['id']) + '\n'
            
        print(out)


# Run ticket collection and process loop
def loop():
    tickets_json = zendesk_get(ticketsurl)
    users, tickets = get_ticket_data(tickets_json)
    users_json = zendesk_get(usersurl + users)
    set_usernames(users_json, tickets)

    if tickets:
        process_tickets(tickets)

main(sys.argv)
loop()

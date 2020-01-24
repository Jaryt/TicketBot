#!/usr/bin/python
from datetime import datetime
from dateutil.relativedelta import relativedelta
import grequests, requests, json, sys, os, parse

user = ''
token = os.getenv("ZENDESK_TOKEN")
url = 'https://{domain}.zendesk.com'
viewsurl = '/api/v2/views/{view_id}/tickets.json' 
usersurl = '/api/v2/users/show_many.json?ids='
ticketsurl = "/agent/tickets/"
commentsurl = '/api/v2/tickets/{ticket_id}/comments.json'


def setup(argv):
    global user, url, viewsurl
    user = argv[1]
    url = url.format(domain=argv[2])
    viewsurl = viewsurl.format(view_id=argv[3])


# Zendesk request and oauth
def zendesk_get(api):
    response = requests.get(url + api, auth=(user + '/token', token))

    if response.status_code != 200:
        print('Status:', response.status_code, 'Problem with the request. Exiting.')
        exit()

    return response.json()


def parse_time(date):
    return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')


# get ticket comments in bunk to find the latest response from an agent
def get_ticket_replies(tickets):
    rs = (grequests.get(url + commentsurl.format(ticket_id=ticket), auth=(user + '/token', token)) for ticket in tickets)

    for response in grequests.map(rs):
        ticket_id = parse.parse(url + commentsurl, response.url)['ticket_id']

        comment_data = response.json()
        recent = datetime.fromtimestamp(0)

        for comment in comment_data['comments']:
            updated = parse_time(comment['created_at'])
        
            if comment['author_id'] == tickets[ticket_id] and updated > recent:
                recent = updated

            diff = relativedelta(datetime.today(), recent)

    return diff


# Getting ticket and user id list from zendesk tickets api endpoint
def get_ticket_data(json_data):
    users = ''
    agent_tickets = {}
    tickets = {}

    for ticket in json_data['tickets']:
        agent = ticket['assignee_id']

        created = parse_time(ticket['created_at'])
        diff = relativedelta(datetime.today(), created)

        if diff.days >= 5 or diff.months > 0:
            ticket_data = { 'id': ticket['id'], 'time_passed': { 'months': diff.months, 'days': diff.days }, 'agent': None }

            if agent not in agent_tickets:
                if agent != None:
                    if users:
                        users += ',' 
                    users += str(agent)
                agent_tickets[agent] = [ticket_data]
            else:
                agent_tickets[agent].append(ticket_data)

            tickets[str(ticket['id'])] = agent_tickets[agent]

    reply_times = get_ticket_replies(tickets)

    return users, agent_tickets


# Setting usernames from zendesk user api endpoint
def set_usernames(json_data, tickets):
    for user in json_data['users']:
        for ticket in tickets[user['id']]:
            ticket['agent'] = user['name']


# grammatical function
def multi(single, val):
    return str(val) + (single + 's' if val != 1 else single)


# process output for an agent's list of tickets
def process_ticketlist(tickets):
    ticket_list = ""
    body = '{months}{days} since we replied to {link}\n'
    tickets.sort(key = lambda item:(item['time_passed']['months'], item['time_passed']['days']), reverse=True)

    for ticket in tickets:
        name = ticket['agent']

        if name is None:
            header = 'Tickets that have no assignee:\n{tickets}'

        days = ticket['time_passed']['days']
        months = ticket['time_passed']['months']
        month_str = ""
        day_str = ""

        if months > 0:
            month_str = multi(" month", months)

        if days > 0:
            if months > 0:
                day_str = " and "
            day_str += multi(" day", days)

        link = url + ticketsurl + str(ticket['id'])
        ticket_list += body.format(months=month_str, days=day_str, link=link)

    return ticket_list, name

# Get ticket data and print it out
def process_tickets(tickets):
    out = ""
    
    for agent in tickets.keys():
        header = 'Ticket for {name}:\n{tickets}\n'
        ticket_list, name = process_ticketlist(tickets[agent])
        out += header.format(name=name,tickets=ticket_list)

    return out

# Run ticket collection and process loop
def loop():
    tickets_json = zendesk_get(viewsurl)
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

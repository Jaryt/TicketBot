# Zendesk Support v2 API Python Wrapper

from datetime import datetime
import grequests, requests, json, sys, os, parse

# Zendesk Keys
user = ''
token = os.getenv("ZENDESK_TOKEN")
url = 'https://{domain}.zendesk.com'
views_hook = '/api/v2/views/{view_id}/tickets.json'
comments_hook = '/api/v2/tickets/{ticket_id}/comments.json' 
users_hook = '/api/v2/users/show_many.json?ids={users}'
policies_hook = '/api/v2/slas/policies'

# Zendesk data
tickets = {}
users = { 'end_users': {}, 'agents': {}, 'unknown': {} }
sla_policies = {}


# Set zendesk username and domain
def set_credentials(login, domain):
    global user, url
    user = login
    url = url.format(domain=domain)


# Zendesk request and oauth
def zendesk_get(api):
    response = requests.get(url + api, auth=(user + '/token', token))

    if response.status_code != 200:
        print('Status:', response.status_code, 'Problem with the', api, 'request. Exiting.')
        exit()

    return response.json()


def get_zendesk_url():
    return url

# Parse ticket data 
def parse_tickets(tickets_json):
    for ticket in tickets_json['tickets']:
        assignee_id = str(ticket['assignee_id'])
        ticket_id = str(ticket['id'])
        created_at = parse_time(ticket['created_at'])
        tickets[ticket_id] = { 'assignee_id': assignee_id, 'created_at': created_at, 'comments': { 'public': {}, 'private': {} } }
        agents = users['agents']

        if assignee_id in agents:
            agents[assignee_id]['assigned'].append(ticket_id)
        else:
            agents[assignee_id] = { 'name': None, 'email': None, 'assigned': [ ticket_id ], 'commented': {} }


# Load tickets from zendesk view id
def load_tickets_view(view_id):
    parse_tickets(zendesk_get(views_hook.format(view_id=view_id)))


# Parse zendesk's date format
def parse_time(date):
    return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')


# Get replies from all tickets
def load_ticket_replies():
    rs = (grequests.get(url + comments_hook.format(ticket_id=ticket), auth=(user + '/token', token)) for ticket in tickets)
    
    for response in grequests.map(rs):
        ticket_id = parse.parse(url + comments_hook, response.url)['ticket_id']
        ticket = tickets[ticket_id]
        comment_json = response.json()

        for comment in comment_json['comments']:
            author_id = str(comment['author_id'])
            is_public = 'public' if comment['public'] else 'private'
            ticket_vis = ticket['comments'][is_public]
            created_at = parse_time(comment['created_at'])
            comment_data = { 'created_at': created_at, 'body': comment['body'] }
            agents = users['agents']
            unknown_users = users['unknown']

            if author_id in agents:
                agent = agents[author_id]
                if not ticket_id in agent:
                    agent_comments = agent['commented']

                    if ticket_id in agent_comments:
                        agent_comments[ticket_id] = agent_comments[ticket_id] + 1
                    else:
                        agent_comments[ticket_id] = 1
            else:
                if author_id in unknown_users:
                    unknown_user = unknown_users[author_id]

                    if ticket_id in unknown_user:
                        unknown_user[ticket_id] = unknown_user[ticket_id] + 1
                    else:
                        unknown_user[ticket_id] = 1
                else:
                    unknown_users[author_id] = { ticket_id: 1 }

            if author_id in ticket_vis:
                author_data = ticket_vis[author_id]
                last = ticket_vis[author_id]['last']

                if created_at > last['created_at']:
                    author_data['all'] = last
                    author_data['last'] = comment_data
                else:
                    author_data['all'].append(comment_data)
            else: 
                ticket_vis[author_id] = { 'last': comment_data, 'all': []}


def load_user_data():
    cs = ','

    users_cs = cs.join(users['agents']).strip('None') + ',' + cs.join(users['unknown'])
    user_json = zendesk_get(users_hook.format(users=users_cs))

    for user in user_json['users']:
        user_id = str(user['id'])
        role = user['role'] 
        name = user['name']
        email = user['email']
        agents = users['agents']    
        end_users = users['end_users']
        unknown = users['unknown']

        if user_id in agents:
            agent = agents[user_id]
            agent['name'] = name
            agent['email'] = email
        else:
            if role == 'end-user':
                end_users[user_id] = { 'name': name, 'email': email, 'tickets': unknown[user_id] }
            else:
                agents[user_id] = { 'name': name, 'email': email, 'commented': unknown[user_id] }
            del unknown[user_id]


def load_last_replies():
    for ticket_id in tickets:
        ticket = tickets[ticket_id]
        comments = ticket['comments']
        comments['last_replies'] = {}       
        last = comments['last_replies']
        public = comments['public']

        for commenter in public:
            for user_type in users:
                if commenter in users[user_type]:
                    commenter_last = public[commenter]['last']
                    created_at = commenter_last['created_at']

                    if user_type in last:
                        if created_at > last[user_type]['comment']['created_at']:
                            last[user_type] = { 'author_id': commenter, 'comment': commenter_last }
                    else:
                        last[user_type] = { 'author_id': commenter, 'comment': commenter_last }


# Start of SLA loading, 
def load_sla_policies():
    sla_json = zendesk_get(policies_hook)


def load_ticket_sla():
    if not sla_policies:
        load_sla_policies()


def get_tickets():
    return tickets


def get_users():
    return users
#!/usr/bin/env python3.6

import gdax
import configparser
import json
from twilio.rest import Client
import os
import os.path

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

config = configparser.ConfigParser()
config.read('settings.ini')

try:
    DEBUG = config.getboolean('Preferences','debug')
except:
    DEBUG = False

if DEBUG:
    print('[DEBUG] - Running in debug mode.')

API_KEY = config['GDAX_API']['key'].strip('\'')
API_SECRET = config['GDAX_API']['secret'].strip('\'')
API_PASSPHRASE = config['GDAX_API']['passphrase'].strip('\'')

USER_PHONE = config['User']['phone']

TWILIO_ACCOUNT_SID = config['Twilio']['account']
TWILIO_AUTH_TOKEN = config['Twilio']['token']
TWILIO_NUMBER = config['Twilio']['number']
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms(message, tophone):
    if DEBUG:
        print('DEBUG MODE ACTIVE - no notifications sent.')
        return
    twilio_client.messages.create(to=tophone, from_=TWILIO_NUMBER,
                                 body=message)



KNOWN_ORDER_DATA_FILE = config['Preferences']['orderfile']

if not os.path.isfile(KNOWN_ORDER_DATA_FILE):
    print('First run creating {}...'.format(KNOWN_ORDER_DATA_FILE))
    with open(KNOWN_ORDER_DATA_FILE, "w") as newfile:
        newfile.write("[]")
        newfile.close()


with open(KNOWN_ORDER_DATA_FILE, 'r') as raw_disk_order_data:
    raw_disk_order_data = raw_disk_order_data.read()
KNOWN_ORDER_DATA = json.loads(raw_disk_order_data)

auth_client = gdax.AuthenticatedClient(API_KEY, API_SECRET, API_PASSPHRASE)

gdax_account = auth_client.get_accounts()


#for wallet in gdax_account:
#    print('{} Balance:{}'.format(wallet['currency'], wallet['balance']))
#    print('{} Holding:{}'.format(wallet['currency'], wallet['hold']))
#    print('')

API_OPEN_ORDERS = auth_client.get_orders()

# Make an array of order IDs for easy matching.
API_ORDER_IDS = []
for open_orders_array in API_OPEN_ORDERS:
    for open_order in open_orders_array:
        API_ORDER_IDS.append(open_order['id'])

if DEBUG:
    print(API_ORDER_IDS)

# Make an array of known order IDs for easy matching later.
KNOWN_ORDER_IDS= []
for open_order in open_orders_array:
    KNOWN_ORDER_IDS.append(open_order['id'])
    # Check if an order we knew about went away, add to array of filled orders to notify about.
    if open_order['id'] in API_ORDER_IDS:
        if DEBUG:
            print('[DEBUG] - The order {} has NOT been filled.'.format(open_order['id']))
    else:
        if DEBUG:
            print('[DEBUG] - The order {} has been filled.'.format(open_order['id']))
        send_sms('The {} order of {} has been filled for {} at {}. ID" {}'.format(open_order['side'],open_order['product_id'],open_order['size'],open_order['price'],open_order['id']), USER_PHONE)


# Check if there is a new order we dont know about.
for open_orders_array in API_OPEN_ORDERS:
    for open_order in open_orders_array:
        if open_order['id'] in KNOWN_ORDER_IDS:
            if DEBUG:
                print('[DEBUG] - We know about order {}. continuing...'.format(open_order['id']))
        else:
            if DEBUG:
                print('[DEBUG] - The order {} is a NEW Order'.format(open_order['id']))
            KNOWN_ORDER_DATA.append(open_order)
            #send notification about new order here
            send_sms('There is a new {} order of {} for {} at {}. ID: {}'.format(open_order['side'],open_order['product_id'],open_order['size'],open_order['price'],open_order['id']),USER_PHONE)


# Write the known order array to disk
orderfile = open(KNOWN_ORDER_DATA_FILE, 'w')
orderfile.write(str(json.dumps(KNOWN_ORDER_DATA)))
orderfile.close()

#!/usr/bin/env python3.6
# Cron job for sending notifications for GDAX.
# Ralph Luaces
# Version 0.1.1

import gdax
import configparser
import json
from twilio.rest import Client
import os, sys
import os.path
import logging

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

config = configparser.ConfigParser()
config.read('settings.ini')

DEBUG = config.getboolean('Preferences','debug', fallback=False)

logging.basicConfig(
    filename=config['Preferences']['logfile'],
    filemode='a',
    format=('%(asctime)s - %(levelname)s '
            '%(module)s.%(funcName)s:%(lineno)d - '
            '%(message)s'),
    level=logging.getLevelName(config['Preferences']['loglevel']),
)

logger = logging.getLogger(__name__)

if DEBUG:
    logger.debug('Running in debug mode.')
    print('[DEBUG] - Running in debug mode.')

# Get user data
USER_PHONE = config['User']['phone']
# get user notification preferences, 3 is all, 2 is all except new orders, 1 is only order fill
NOTIFICATION_LEVEL = int(config['User']['notification_level'])
logger.debug('Running for user {} on notification level {}.'.format(USER_PHONE, NOTIFICATION_LEVEL))

logger.debug('Establishing twilio client.')
twilio_client = Client(config['Twilio']['account'], config['Twilio']['token'])


def send_sms(message, tophone):
    if DEBUG:
        logger.debug('DEBUG MODE ACTIVE - notifications NOT sent.')
        return
    logger.debug('Notification - {} - sent to {}.'.format(message, tophone))
    twilio_client.messages.create(to=tophone, from_=config['Twilio']['number'],
                                 body=message)


KNOWN_ORDER_DATA_FILE = config['Preferences']['orderfile']

# checks if the known order data file is existant, creates it if not
if not os.path.isfile(KNOWN_ORDER_DATA_FILE):
    logger.info('First run creating {}...'.format(KNOWN_ORDER_DATA_FILE))
    with open(KNOWN_ORDER_DATA_FILE, "w") as newfile:
        newfile.write("")
        newfile.close()

logger.debug('Reading {}'.format(KNOWN_ORDER_DATA_FILE))
with open(KNOWN_ORDER_DATA_FILE, 'r') as raw_disk_order_data:
    raw_disk_order_data = raw_disk_order_data.read()

try:
    KNOWN_ORDER_DATA = json.loads(raw_disk_order_data)
except Exception as error:
    logger.debug(error)
    KNOWN_ORDER_DATA = []

logger.debug('KNOWN_ORDER_DATA = {}'.format(KNOWN_ORDER_DATA))

try:
    auth_client = gdax.AuthenticatedClient(
        config['GDAX_API']['key'].strip('\''),
        config['GDAX_API']['secret'].strip('\''),
        config['GDAX_API']['passphrase'].strip('\'')
    )
    gdax_account = auth_client.get_accounts()
    logger.debug('Connected to GDAX and acquired account.')
except:
    logger.info('Failed to access GDAX API aborting.')
    sys.exit('Failed to access GDAX API.')

#for wallet in gdax_account:
#    print('{} Balance:{}'.format(wallet['currency'], wallet['balance']))
#    print('{} Holding:{}'.format(wallet['currency'], wallet['hold']))
#    print('')

logger.debug('Loading currently open orders from API.')
API_OPEN_ORDERS = auth_client.get_orders()
logger.debug('Currently open orders = {}'.format(API_OPEN_ORDERS))

# Make an array of order IDs for easy matching.
API_ORDER_IDS = []
for open_orders_array in API_OPEN_ORDERS:
    for open_order in open_orders_array:
        API_ORDER_IDS.append(open_order['id'])


# Make an array of known order IDs for easy matching later.
KNOWN_ORDER_IDS= []
for open_order_array in KNOWN_ORDER_DATA:
    for open_order in open_order_array:
        KNOWN_ORDER_IDS.append(open_order['id'])
        # Check if an order we knew about went away, add to array of filled orders to notify about.
        if open_order['id'] in API_ORDER_IDS:
            logger.debug('The order {} has NOT been filled. Continuing.'.format(open_order['id']))
        else:
            try:
                if auth_client.get_order(open_order['id'])['done_reason'] == "filled":
                    send_sms(
                        'The {} order of {} has been filled for {} at ${} USD. ID: {}'.format(
                            open_order['side'],
                            open_order['product_id'],
                            open_order['size'],
                            open_order['price'],
                            open_order['id']),
                        USER_PHONE
                    )
                    logger.info('The order {} has been filled.'.format(open_order['id']))
            except KeyError:
                logger.debug('The order {} has been canceled.'.format(open_order['id']))
                if NOTIFICATION_LEVEL >= 2:
                    send_sms(
                        'The {} order of {} has been canceled for {} at ${} USD. ID: {}'.format(
                            open_order['side'],
                            open_order['product_id'],
                            open_order['size'],
                            open_order['price'],
                            open_order['id']),
                        USER_PHONE
                    )
                    logger.info('Order {} cancellation notification sent!')


# Check if there is a new order we dont know about.
for open_orders_array in API_OPEN_ORDERS:
    for open_order in open_orders_array:
        if open_order['id'] in KNOWN_ORDER_IDS:
            logger.debug('Order {} is still open. continuing...'.format(open_order['id']))
        else:
            logger.debug('The order {} is a NEW Order.'.format(open_order['id']))
            KNOWN_ORDER_DATA.append(open_order) # add this new order to known order array to be written to file
            if NOTIFICATION_LEVEL >= 2:
                send_sms(
                    'There is a new {} order of {} for {} at ${} USD. ID: {}'.format(
                    open_order['side'],
                    open_order['product_id'],
                    open_order['size'],
                    open_order['price'],
                    open_order['id']),
                    USER_PHONE
                )
                logger.info('New sell order notification for order {} sent!'.format(open_order['id']))


# Write the known order array to disk
logger.debug('Writing known order data file ({})to disk.'.format(KNOWN_ORDER_DATA))
logger.debug(API_OPEN_ORDERS)
orderfile = open(KNOWN_ORDER_DATA_FILE, 'w')
orderfile.write(str(json.dumps(API_OPEN_ORDERS)))
orderfile.close()
logger.debug('Known order data file written to.')

logger.info('GDAX Notifier Job run complete.')

sys.exit()

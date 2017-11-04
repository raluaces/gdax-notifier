#!/usr/bin/env python3.6

import gdax
import configparser

config = configparser.ConfigParser()
config.read('gdaxapi')

API_KEY = config['GDAX_API']['key'].strip('\'')
API_SECRET = config['GDAX_API']['secret'].strip('\'')
API_PASSPHRASE = config['GDAX_API']['passphrase'].strip('\'')


auth_client = gdax.AuthenticatedClient(API_KEY, API_SECRET, API_PASSPHRASE)

gdax_account = auth_client.get_accounts()

for wallet in gdax_account:
    print('{} Balance:{}'.format(wallet['currency'], wallet['balance']))
    print('{} Holding:{}'.format(wallet['currency'], wallet['hold']))
    print('')

print(auth_client.get_fills())

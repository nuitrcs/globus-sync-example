#!/usr/bin/env python

import click
import json
import os
import six

from globus_sdk import (NativeAppAuthClient, TransferClient,
        RefreshTokenAuthorizer, TransferData)
from globus_sdk.exc import GlobusAPIError, TransferAPIError

CLIENT_ID = os.environ.get('GLOBUS_SYNC_CLIENT_ID', 'ENTER YOUR CLIENT ID HERE')
REDIRECT_URI = 'https://auth.globus.org/v2/web/auth-code'
SCOPES = ('urn:globus:auth:scope:transfer.api.globus.org:all')

get_input = getattr(__builtins__, 'raw_input', input)

@click.command()
@click.argument('source_endpoint', type=click.UUID)
@click.argument('source_path')
@click.argument('destination_endpoint', type=click.UUID)
@click.argument('destination_path')
@click.option('--synctype', type=click.Choice(['exists', 'size', 'mtime',
    'timestamp', 'checksum']), default='checksum')
@click.option('--sync-data-file', default='.globus-sync-data.json')
@click.option('--transfer-label', default='My Globus Sync')
def sync(source_endpoint, source_path, destination_endpoint, destination_path,
        synctype, sync_data_file, transfer_label):

    global DATA_FILE

    if source_endpoint == destination_endpoint:
        raise click.UsageError('Source and destination endpoints must be different.')

    DATA_FILE = sync_data_file

    tokens = get_tokens()
    transfer = setup_transfer_client(tokens['transfer.api.globus.org'],
            source_endpoint, destination_endpoint)

    try:
        task_data = load_data_from_file(DATA_FILE)['task']
        task = transfer.get_task(task_data['task_id'])
        if task['status'] not in ['SUCCEEDED', 'FAILED']:
            print('The last transfer status is {}, skipping run...'.format(
                task['status']
            ))
            sys.exit(1)
    except KeyError:
        # Ignore if there is no previous task
        pass

    check_endpoint_path(transfer, source_endpoint, source_path)
    create_destination_directory(transfer, destination_endpoint, destination_path)

    tdata = TransferData(transfer, source_endpoint, destination_endpoint,
            label=transfer_label, sync_level=synctype)
    tdata.add_item(source_path, destination_path, recursive=True)
    
    task = transfer.submit_transfer(tdata)
    save_data_to_file(DATA_FILE, 'task', task.data)
    print('Transfer has been started from\n  {}:{}\nto\n  {}:{}'.format(
        source_endpoint,
        source_path,
        destination_endpoint,
        destination_path
    ))
    url_string = 'https://globus.org/app/transfer?' + \
        six.moves.urllib.parse.urlencode({
            'origin_id': source_endpoint,
            'origin_path': source_path,
            'destination_id': destination_endpoint,
            'destination_path': destination_path
        })
    print('Visit the link below to see the changes:\n{}'.format(url_string)) 

def check_endpoint_path(client, endpoint, path):
    try:
        client.operation_ls(endpoint, path=path)
    except TransferAPIError as tapie:
        print('Failed to query endpoint "{}": {}'.format(
            endpoint,
            tapie.message
        ))
        sys.exit(1)

def create_destination_directory(client, dest_ep, dest_path):
    try:
        client.operation_ls(dest_ep, path=dest_path)
    except TransferAPIError:
        try:
            client.operation_mkdir(dest_ep, dest_path)
            print('Created directory: {}'.format(dest_path))
        except TransferAPIError as tapie:
            print('Failed to start transfer: {}'.format(tapie.message))
            sys.exit(1)

def get_tokens():
    tokens = None
    try:
        # if we already have tokens, load and use them
        tokens = load_data_from_file(DATA_FILE)['tokens']
    except:
        pass

    if not tokens:
        # if we need to get tokens, start the Native App authentication process
        tokens = do_native_app_authentication(CLIENT_ID, REDIRECT_URI, SCOPES)

        try:
            save_data_to_file(DATA_FILE, 'tokens', tokens)
        except:
            pass

    return tokens

def load_data_from_file(filepath):
    with open(filepath, 'r') as f:
        tokens = json.load(f)
    return tokens

def update_tokens_file_on_refresh(token_response):
    """
    Callback function passed into the RefreshTokenAuthorizer.
    Will be invoked any time a new access token is fetched.
    """
    save_data_to_file(DATA_FILE, 'tokens', token_response.by_resource_server)

def setup_transfer_client(transfer_tokens, source_endpoint,
        destination_endpoint):
    authorizer = RefreshTokenAuthorizer(
        transfer_tokens['refresh_token'],
        NativeAppAuthClient(client_id=CLIENT_ID),
        access_token=transfer_tokens['access_token'],
        expires_at=transfer_tokens['expires_at_seconds'],
        on_refresh=update_tokens_file_on_refresh)

    transfer_client = TransferClient(authorizer=authorizer)

    try:
        transfer_client.endpoint_autoactivate(source_endpoint)
        transfer_client.endpoint_autoactivate(destination_endpoint)
    except GlobusAPIError as ex:
        if ex.http_status == 401:
            sys.exit('Refresh token has expired. '
                     'Please delete the `tokens` object from '
                     '{} and try again.'.format(DATA_FILE))
        else:
            raise ex
    return transfer_client

def save_data_to_file(filepath, key, data):
    try:
        store = load_data_from_file(filepath)
    except:
        store = {}
    store[key] = data
    with open(filepath, 'w') as f:
        json.dump(store, f)

def do_native_app_authentication(client_id, redirect_uri,
        requested_scopes=None):
    """
    Does a Native App authentication flow and returns a
    dict of tokens keyed by service name.
    """
    client = NativeAppAuthClient(client_id=client_id)
    # pass refresh_tokens=True to request refresh tokens
    client.oauth2_start_flow(requested_scopes=requested_scopes,
                             redirect_uri=redirect_uri,
                             refresh_tokens=True)

    url = client.oauth2_get_authorize_url()

    print('Native App Authorization URL:\n{}'.format(url))

    auth_code = get_input('Enter the auth code: ').strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    # return a set of tokens, organized by resource server name
    return token_response.by_resource_server

if __name__ == '__main__':
    sync()

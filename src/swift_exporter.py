from swiftclient.client import Connection
from swiftclient.exceptions import ClientException

from keystoneauth1 import session
from keystoneauth1.identity import v3

from prometheus_client import Counter
from prometheus_client import start_http_server

import sys
import os
import time

import argparse
import signal


class ExceptionManager:

    def __init__(self):
        self.METRIC_PATTERN_NAME = 'swift_object_storage_auth_error'
        self.METRIC = Counter(self.METRIC_PATTERN_NAME, '', ['type'])
        self.METRIC.labels(type='')

    def add(self, label):
        self.METRIC.labels(type=label).inc()
        print(f'[ERROR] The following exception has been raised: {label}')


# Create a password auth plugin
auth = v3.Password(auth_url=os.environ.get('SWIFT_AUTH_URL'),
                   username=os.environ.get('SWIFT_USERNAME'),
                   password=os.environ.get('SWIFT_PASSWORD'),
                   user_domain_name=os.environ.get('SWIFT_DOMAIN_NAME'),
                   project_name=os.environ.get('SWIFT_PROJECT_NAME'),
                   project_domain_name=os.environ.get('SWIFT_PROJECT_DOMAINE_NAME'))


def handler(signum, frame):
    raise TimeoutError('timeout')


signal.signal(signal.SIGALRM, handler)

# Create session
keystone_session = session.Session(auth=auth)

# Create swiftclient Connection
swift_conn = Connection(session=keystone_session)

exception_manager = ExceptionManager()

def state_checker(container=None):
    try:
        if container!=None:
            resp_headers = swift_conn.head_container(container)
        else:
            resp_headers = swift_conn.head_account()
    except Exception as exc:
        label = (str(exc.__class__)[8:-2]).replace('.', '_').lower()
        exception_manager.add(label)
    except TimeoutError:
        exception_manager.add('timeout')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Prometheus probe for checking Swift Object Storage authentication liveness.')
    parser.add_argument('-r', '--rate', default=1, metavar='rate', type=int,
                        help='the ping rate in seconds')
    parser.add_argument('-t', '--timout', required=False, default=1, metavar='timout', type=int,
                        help='each request allowed time (in seconds) before timout error is raised')
    parser.add_argument('-c', '--container', required=False, default=None, metavar='name', type=str,
                        help='the container\'s name you wan\'t to ping')
    parser.add_argument('-p', '--port', required=False, default=9790, metavar='port', type=int,
                        help='probe\'s port (default: 9790)')

    args = parser.parse_args()

    REQ_TIMEOUT = int(os.environ.get('EXPORTER_REQUEST_TIMOUT_SEC')) if 'EXPORTER_REQUEST_TIMOUT_SEC' in os.environ else args.timout
    REQ_RATE = int(os.environ.get('EXPORTER_REQUEST_RATE_SEC')) if 'EXPORTER_REQUEST_RATE_SEC' in os.environ else args.time
    CONTAINER = os.environ.get('OPTIONAL_CONTAINER_TARGET') if 'OPTIONAL_CONTAINER_TARGET' in os.environ else args.container
    
    # Start up the server to expose the metrics.
    start_http_server(args.port)
    
    # Generate some requests.
    while True:
        signal.alarm(TIMEOUT)
        state_checker(CONTAINER)
        signal.alarm(0)
        time.sleep(REQ_RATE)
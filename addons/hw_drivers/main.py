# -*- coding: utf-8 -*-
# Part of Flectra. See LICENSE file for full copyright and licensing details.
from traceback import format_exc
import json
import platform
import logging
import socket
from threading import Thread
import time
import urllib3

from flectra.addons.hw_drivers.tools import helpers
from flectra.addons.hw_drivers.websocket_client import WebsocketClient

_logger = logging.getLogger(__name__)

try:
    import schedule
except ImportError:
    schedule = None
    # For now, it is intended to not be installed on the iot-box as it uses native Unix cron system
    if platform.system() == 'Windows':
        _logger.warning('Could not import library schedule')

try:
    from dbus.mainloop.glib import DBusGMainLoop
except ImportError:
    DBusGMainLoop = None
    _logger.error('Could not import library dbus')

drivers = []
interfaces = {}
iot_devices = {}


class Manager(Thread):
    def send_alldevices(self, iot_client=None):
        """
        This method send IoT Box and devices informations to Flectra database
        """
        server = helpers.get_flectra_server_url()
        if server:
            subject = helpers.read_file_first_line('flectra-subject.conf')
            if subject:
                domain = helpers.get_ip().replace('.', '-') + subject.strip('*')
            else:
                domain = helpers.get_ip()
            iot_box = {
                'name': socket.gethostname(),
                'identifier': helpers.get_mac_address(),
                'ip': domain,
                'token': helpers.get_token(),
                'version': helpers.get_version(detailed_version=True),
            }
            devices_list = {}
            for device in iot_devices:
                identifier = iot_devices[device].device_identifier
                devices_list[identifier] = {
                    'name': iot_devices[device].device_name,
                    'type': iot_devices[device].device_type,
                    'manufacturer': iot_devices[device].device_manufacturer,
                    'connection': iot_devices[device].device_connection,
                }
            data = {'params': {'iot_box': iot_box, 'devices': devices_list,}}
            # disable certifiacte verification
            urllib3.disable_warnings()
            http = urllib3.PoolManager(cert_reqs='CERT_NONE')
            try:
                resp = http.request(
                    'POST',
                    server + "/iot/setup",
                    body=json.dumps(data).encode('utf8'),
                    headers={
                        'Content-type': 'application/json',
                        'Accept': 'text/plain',
                    },
                )
                if iot_client:
                    iot_client.iot_channel = json.loads(resp.data).get('result', '')
            except json.decoder.JSONDecodeError:
                _logger.exception('Could not load JSON data: Received data is not in valid JSON format\ncontent:\n%s', resp.data)
            except Exception:
                _logger.exception('Could not reach configured server')
        else:
            _logger.warning('Flectra server not set')

    def run(self):
        """
        Thread that will load interfaces and drivers and contact the flectra server with the updates
        """

        helpers.start_nginx_server()
        _logger.info("IoT Box Image version: %s", helpers.get_version(detailed_version=True))
        if platform.system() == 'Linux' and helpers.get_flectra_server_url():
            helpers.check_git_branch()
            helpers.generate_password()
        is_certificate_ok, certificate_details = helpers.get_certificate_status()
        if not is_certificate_ok:
            _logger.warning("An error happened when trying to get the HTTPS certificate: %s",
                            certificate_details)

        iot_client = helpers.get_flectra_server_url() and WebsocketClient(helpers.get_flectra_server_url())
        # We first add the IoT Box to the connected DB because IoT handlers cannot be downloaded if
        # the identifier of the Box is not found in the DB. So add the Box to the DB.
        self.send_alldevices(iot_client)
        helpers.download_iot_handlers()
        helpers.load_iot_handlers()

        # Start the interfaces
        for interface in interfaces.values():
            try:
                i = interface()
                i.daemon = True
                i.start()
            except Exception as e:
                _logger.error("Error in %s: %s", str(interface), e)

        # Set scheduled actions
        schedule and schedule.every().day.at("00:00").do(helpers.get_certificate_status)

        #Setup the websocket connection
        if helpers.get_flectra_server_url():
            iot_client.start()
        # Check every 3 secondes if the list of connected devices has changed and send the updated
        # list to the connected DB.
        self.previous_iot_devices = []
        while 1:
            try:
                if iot_devices != self.previous_iot_devices:
                    self.previous_iot_devices = iot_devices.copy()
                    self.send_alldevices(iot_client)
                time.sleep(3)
                schedule and schedule.run_pending()
            except Exception:
                # No matter what goes wrong, the Manager loop needs to keep running
                _logger.error(format_exc())

# Must be started from main thread
if DBusGMainLoop:
    DBusGMainLoop(set_as_default=True)

manager = Manager()
manager.daemon = True
manager.start()

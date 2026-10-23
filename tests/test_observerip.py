# Copyright 2026 weewx-packages
# Distributed under the terms of the GNU Public License (GPLv3)
import importlib.machinery
import importlib.util
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import threading
from unittest.mock import Mock

import pytest
import weewx

spec = importlib.util.spec_from_file_location('observerip', Path(__file__).parents[1] / 'bin/user/observerip.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_unit_mismatch_is_actionable(monkeypatch, caplog):
    hardware = Mock()
    hardware.getstationsettings.return_value = {'u_Temperature': 'degC'}
    monkeypatch.setattr(m, 'OpserverIPHardware', Mock(return_value=hardware))
    with pytest.raises(weewx.WeeWxIOError, match='Station units'):
        m.ObserverIPDriver(mode='direct')


def test_html_selected_unit_and_eof():
    parser = m.StationPage(False)
    parser.feed('<select name="u_Temperature"><option value="0">degC</option><option selected value="1">degF</option></select><input name="outTemp" value="0">')
    assert parser.values == {'u_Temperature': 'degF', 'outTemp': '0'}
    truncated = m.StationPage()
    truncated.feed('<select name="unit"><option>no selection')
    assert truncated.values == {}


def test_local_http_bytes():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'<input name="outTemp" value="0"><input name="Apply" value="Apply">')
        def log_message(self, *args):
            pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    hardware = object.__new__(m.OpserverIPHardware)
    hardware.timeout = 1
    hardware.max_tries = 1
    try:
        assert hardware.page_to_dict('http://127.0.0.1:%d/livedata.htm' % server.server_port) == {'outTemp': '0'}
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_udp_probe_bytes_and_decoding():
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(('127.0.0.1', 0))
    receiver.settimeout(2)
    replies = []
    def receive():
        data, sender = receiver.recvfrom(1024)
        replies.append(data)
        reply = bytearray(128)
        reply[0x22:0x26] = bytes([127, 0, 0, 1])
        reply[0x73:0x7b] = b'3.0.0\x00\x00\x00'
        receiver.sendto(reply, sender)
    thread = threading.Thread(target=receive, daemon=True)
    thread.start()
    hardware = object.__new__(m.OpserverIPHardware)
    hardware.UDP_PORT = receiver.getsockname()[1]
    hardware.hostname = '127.0.0.1'
    hardware.max_tries = 1
    hardware.retry_wait = 1
    try:
        hardware.infopacket = hardware.infoprobe()
        assert hardware.ipaddr() == '127.0.0.1'
        assert hardware.version() == '3.0.0'
    finally:
        thread.join(3)
        receiver.close()
    assert replies == [b'ASIXXISA\x00']


def test_indirect_mode_and_zero_measurements(tmp_path):
    driver = m.ObserverIPDriver(mode='indirect', xferfile=str(tmp_path / 'weather.txt'))
    data = {entry[0]: '0' for entry in driver.map.values()}
    data['epoch'] = '1234'
    packet = driver.parse_page(data)
    assert packet['outTemp'] == 0
    assert packet['dateTime'] == 1234


def test_bounds_raise_instead_of_exit():
    hardware = object.__new__(m.OpserverIPHardware)
    with pytest.raises(ValueError, match='calibration'):
        hardware.boundcheck({'offset': (float, -1, 1)}, {'offset': 99})


def test_post_form_escaping():
    assert m.OpserverIPHardware.dict_to_param({'password': 'a&b=c'}) == 'password=a%26b%3Dc'


def load_installer():
    loader = importlib.machinery.SourceFileLoader('observerip_install', str(Path(__file__).parents[1] / 'install.py'))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module.loader()


def test_installer_writes_only_below_bin_user():
    assert all(destination.startswith('bin/user') for destination, _ in load_installer()['files'])


def test_installer_config_selects_mode_and_ignores_station_calibration(monkeypatch):
    config = load_installer()['config']['ObserverIP']
    assert config['mode'] == 'direct' and 'direct' not in config
    hardware = Mock()
    hardware.getstationsettings.return_value = {}
    hardware.version.return_value = '3.0.0'
    hardware.getcalibration.return_value = dict(config['calibration'], RainGain='1.5')
    monkeypatch.setattr(m, 'OpserverIPHardware', Mock(return_value=hardware))
    m.ObserverIPDriver(**config)


def test_setnetworksettings_posts_settings():
    posted = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            posted.append((self.path, self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.end_headers()
        def log_message(self, *args):
            pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    hardware = object.__new__(m.OpserverIPHardware)
    hardware.timeout = 1
    hardware.ipaddr = lambda: '127.0.0.1:%d' % server.server_port
    try:
        hardware.setnetworksettings({'dhcp': '1'})
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    assert posted == [('/bscsetting.htm', b'dhcp=1&Apply=Apply')]


@pytest.mark.skipif(shutil.which('bc') is None, reason='the CGI example needs bc')
def test_cgi_example_rewrites_transfer_file_without_seqfile(tmp_path):
    source = Path(__file__).parents[1] / 'bin/user/observerip_examples/apache/weatherstation/updateweatherstation.php'
    xferfile = tmp_path / 'weather.txt'
    script = tmp_path / 'cgi.sh'
    script.write_text(re.sub('(?m)^xferfile=.*$', 'xferfile=%s' % xferfile, source.read_text()))
    query = ('tempf=50&humidity=40&dewptf=30&windchillf=50&winddir=90&windspeedmph=1&windgustmph=2'
             '&yearlyrainin=1&solarradiation=0&UV=0&indoortempf=70&indoorhumidity=30&baromin=29.9'
             '&lowbatt=0&dateutc=2026-10-23%2010:00:00')
    environment = dict(os.environ, QUERY_STRING=query, REMOTE_ADDR='127.0.0.1')
    for _ in range(2):
        subprocess.run(['bash', str(script)], env=environment, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, check=True)
    lines = xferfile.read_text().splitlines()
    assert len(lines) == len(set(lines))
    driver = m.ObserverIPDriver(mode='indirect', xferfile=str(xferfile))
    assert driver.parse_page(driver.get_data())['outTemp'] == 50


def test_config_editor_stanza_does_not_check_calibration():
    import configobj
    stanza = configobj.ConfigObj(m.ObserverIPConfEditor().default_stanza.splitlines())
    assert stanza['ObserverIP']['check_calibration'] == 'false'

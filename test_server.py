"""Self-test: starts the server on spare ports, plays a relay round and a high-score round.
python3 test_server.py  -> ALL OK"""
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

UDP, HTTP = 37620, 37621
data = os.path.join(tempfile.mkdtemp(), 'scores.json')
here = os.path.dirname(os.path.abspath(__file__))
srv = subprocess.Popen([sys.executable, os.path.join(here, 'lumines_server.py'),
                        '--udp', str(UDP), '--http', str(HTTP), '--data', data])
try:
    time.sleep(1.0)
    addr = ('127.0.0.1', UDP)
    a, b, c = (socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(3))
    for s in (a, b, c):
        s.settimeout(2)
    a.sendto(b'LM\x01\x12\x34', addr)
    assert a.recv(16) == b'LM\x02\x00\x00'
    b.sendto(b'LM\x01\x12\x34', addr)
    assert b.recv(16) == b'LM\x02\x01\x01'
    assert a.recv(16) == b'LM\x02\x00\x01'
    a.sendto(b'LM\x03step1', addr)
    assert b.recv(64) == b'LM\x03step1'
    b.sendto(b'LM\x03step2', addr)
    assert a.recv(64) == b'LM\x03step2'
    c.sendto(b'LM\x01\x12\x34', addr)
    assert c.recv(16) == b'LM\x04'
    b.sendto(b'LM\x05', addr)
    assert a.recv(16) == b'LM\x05'

    base = 'http://127.0.0.1:%d' % HTTP
    for body in (b'0 AAA 1200', b'0 BOB 5000', b'0 X 300'):
        assert urllib.request.urlopen(base + '/submit', body).read() == b'OK'
    try:
        urllib.request.urlopen(base + '/submit', b'0 <b> 9')
        raise AssertionError('bad name accepted')
    except urllib.error.HTTPError as e:
        assert e.code == 400
    assert urllib.request.urlopen(base + '/top?mode=0').read() == b'BOB 5000\nAAA 1200\nX 300\n'
    print('ALL OK')
finally:
    srv.terminate()

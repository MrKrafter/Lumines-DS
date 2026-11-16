#!/usr/bin/env python3
"""Lumines DS community server: 1v1 UDP relay + HTTP high-score table. Python 3.8+, stdlib only.

  python3 lumines_server.py [--udp 27620] [--http 27621] [--data scores.json]

UDP relay (every packet starts with b'LM' and a type byte):
  1 HELLO   'LM' 01 room:u16be       join a room (2 players max); the server answers WELCOME
  2 WELCOME 'LM' 02 slot:u8 peer:u8  slot 0 = host, 1 = client; peer 1 = the other player is there
  3 DATA    'LM' 03 <payload>        forwarded unchanged to the other player of the room
  4 FULL    'LM' 04                  the room already has two players
  5 BYE     'LM' 05                  leave the room (also sent to the other player)
Rooms without packets for 60 s are dropped. HELLO doubles as keepalive.

HTTP high scores (plain text, one entry per line):
  GET  /top?mode=N                     -> "NAME SCORE\n" x up to 10, best first
  POST /submit  body "mode name score" -> "OK" (200) / "BAD" (400)
  mode 0..15, name 1..6 chars of A-Z 0-9 - . space, score 0..999999.
"""
import argparse
import json
import os
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOM_TTL = 60
TOP_N = 10
NAME_RE = re.compile(r'^[A-Z0-9.\- ]{1,6}$')


class Relay:
    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', port))
        self.rooms = {}  # room -> [addr, addr]
        self.where = {}  # addr -> room
        self.seen = {}   # room -> time of the last packet

    def leave(self, addr):
        room = self.where.pop(addr, None)
        if room is None:
            return
        players = self.rooms.get(room, [])
        if addr in players:
            players.remove(addr)
        for p in players:
            self.sock.sendto(b'LM\x05', p)
        if not players:
            self.rooms.pop(room, None)
            self.seen.pop(room, None)

    def expire(self):
        now = time.time()
        for room in [r for r, t in self.seen.items() if now - t > ROOM_TTL]:
            for p in self.rooms.get(room, []):
                self.where.pop(p, None)
            self.rooms.pop(room, None)
            self.seen.pop(room, None)

    def handle(self, data, addr):
        if len(data) < 3 or data[:2] != b'LM':
            return
        t = data[2]
        if t == 1 and len(data) >= 5:
            room = int.from_bytes(data[3:5], 'big')
            if self.where.get(addr) not in (None, room):
                self.leave(addr)
            players = self.rooms.setdefault(room, [])
            if addr not in players:
                if len(players) >= 2:
                    self.sock.sendto(b'LM\x04', addr)
                    return
                players.append(addr)
                self.where[addr] = room
            self.seen[room] = time.time()
            for i, p in enumerate(players):  # tell both sides who is there
                self.sock.sendto(bytes([76, 77, 2, i, int(len(players) == 2)]), p)
        elif t == 3:
            room = self.where.get(addr)
            if room is None:
                return
            self.seen[room] = time.time()
            for p in self.rooms[room]:
                if p != addr:
                    self.sock.sendto(data, p)
        elif t == 5:
            self.leave(addr)

    def run(self):
        last = time.time()
        self.sock.settimeout(5)
        while True:
            try:
                data, addr = self.sock.recvfrom(1500)
                self.handle(data, addr)
            except socket.timeout:
                pass
            except OSError:
                pass  # e.g. ICMP "port unreachable" reported by Windows
            if time.time() - last > 10:
                self.expire()
                last = time.time()


class Scores:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.data = {}
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                self.data = json.load(f)

    def top(self, mode):
        with self.lock:
            return list(self.data.get(str(mode), []))

    def submit(self, mode, name, score):
        with self.lock:
            lst = self.data.setdefault(str(mode), [])
            lst.append([name, score])
            lst.sort(key=lambda e: -e[1])
            del lst[TOP_N:]
            tmp = self.path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.data, f)
            os.replace(tmp, self.path)


def make_handler(scores):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, text):
            body = text.encode()
            self.send_response(code)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path != '/top':
                return self.reply(404, 'NO')
            try:
                mode = int(parse_qs(u.query).get('mode', ['0'])[0])
            except ValueError:
                return self.reply(400, 'BAD')
            self.reply(200, ''.join('%s %d\n' % (n, s) for n, s in scores.top(mode)))

        def do_POST(self):
            if urlparse(self.path).path != '/submit':
                return self.reply(404, 'NO')
            n = min(int(self.headers.get('Content-Length') or 0), 64)
            parts = self.rfile.read(n).decode('ascii', 'replace').strip().split(' ')
            try:
                mode, score, name = int(parts[0]), int(parts[-1]), ' '.join(parts[1:-1]).upper()
            except (ValueError, IndexError):
                return self.reply(400, 'BAD')
            if not (0 <= mode <= 15 and 0 <= score <= 999999 and NAME_RE.match(name)):
                return self.reply(400, 'BAD')
            scores.submit(mode, name, score)
            self.reply(200, 'OK')

        def log_message(self, *args):
            pass
    return Handler


def main():
    ap = argparse.ArgumentParser(description='Lumines DS server (1v1 relay + high scores)')
    ap.add_argument('--udp', type=int, default=int(os.environ.get('LUMINES_UDP', 27620)))
    ap.add_argument('--http', type=int, default=int(os.environ.get('LUMINES_HTTP', 27621)))
    ap.add_argument('--data', default=os.environ.get('LUMINES_DATA', 'scores.json'))
    a = ap.parse_args()
    http = ThreadingHTTPServer(('0.0.0.0', a.http), make_handler(Scores(a.data)))
    threading.Thread(target=http.serve_forever, daemon=True).start()
    print('Lumines DS server: relay udp/%d, scores http/%d, data %s' % (a.udp, a.http, a.data), flush=True)
    Relay(a.udp).run()


if __name__ == '__main__':
    main()

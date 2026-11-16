# Lumines DS — server

[Русский](#русский) · [English](#english)

Community server for the Nintendo DS port of Lumines: online 1v1 (UDP relay) and a high-score table (HTTP).
One Python file, standard library only. Anyone can run their own server and point the game at it.

This repository contains **only the server**. No ROM, no game assets and no game code are published here:
the game belongs to its rights holders. Build the ROM yourself from your own copy of the game.

---

## Русский

### Что это
- `lumines_server.py` — сервер: ретранслятор для игры 1 на 1 (UDP, порт **27620**) и таблица рекордов (HTTP, порт **27621**).
- Нужен только Python 3.8+. Рекорды хранятся в `scores.json`.
- Проверка: `python3 test_server.py` → `ALL OK`.

### Запуск на Linux (systemd)
```sh
sudo mkdir -p /opt/lumines-ds
sudo cp lumines_server.py /opt/lumines-ds/
sudo cp deploy/lumines-ds.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lumines-ds
systemctl status lumines-ds
```
Рекорды лежат в `/var/lib/lumines-ds/scores.json`. Сервис работает от отдельного временного пользователя (DynamicUser).

Открыть порты в файрволе:
- ufw: `sudo ufw allow 27620/udp && sudo ufw allow 27621/tcp`
- firewalld: `sudo firewall-cmd --permanent --add-port=27620/udp --add-port=27621/tcp && sudo firewall-cmd --reload`
- nftables: в цепочку input добавить `udp dport 27620 accept` и `tcp dport 27621 accept`.

### Запуск на Windows
1. Поставить Python 3 с python.org (галка «Add to PATH»).
2. Запустить `deploy\run_windows.bat`.
3. Разрешить Python в брандмауэре (Windows спросит при первом запуске) или открыть порты 27620/UDP и 27621/TCP.

### Запуск в Docker
```sh
docker compose up -d --build
```
или `docker build -t lumines-ds . && docker run -d --restart unless-stopped -p 27620:27620/udp -p 27621:27621 -v lumines-data:/data lumines-ds`.

### Доступ из интернета
На роутере пробросить на машину с сервером **27620/UDP** и **27621/TCP**. Если провайдер даёт серый адрес или
стоят два роутера подряд, проброс нужен на обоих (или нужен VPS с белым IP).

### Как указать свой сервер в игре
Адрес не зашит намертво. Порядок поиска:
1. Файл на карте памяти `/data/LuminesDS/server.txt`, одна строка `host:port`, например `your.server:27620`
   (порт — UDP-ретранслятора; рекорды берутся с порта на 1 больше).
2. Если файла нет — адрес по умолчанию, заданный при сборке ROM (соберите ROM у себя из своей копии игры):
   - Windows: `Собрать_LuminesDS.ps1 -Server your.server:27620`
   - Linux/WSL: `SERVER=your.server:27620 sh tools/build.sh`

Текущий сервер показан в игре в меню «Опции».

### Wi-Fi у DS
Nintendo DS подключается только к **открытым** сетям или сетям с **WEP**. WPA/WPA2 она не умеет.
Нужна отдельная точка доступа: второй SSID на роутере без пароля или с WEP, либо хотспот с ноутбука/телефона.
Настройка сети — в любой DS-игре с Wi-Fi (Nintendo WFC) или в DSi. Не держите в такой сети ничего важного.

### Протокол (для своих клиентов)
Описан в начале `lumines_server.py`: пакеты `LM` + тип (HELLO комнаты, WELCOME, DATA, FULL, BYE);
`GET /top?mode=N`, `POST /submit` с телом `mode name score`.

---

## English

### What it is
- `lumines_server.py` — a 1v1 relay (UDP port **27620**) and a high-score table (HTTP port **27621**).
- Needs only Python 3.8+. Scores are stored in `scores.json`.
- Self-test: `python3 test_server.py` → `ALL OK`.

### Linux (systemd)
```sh
sudo mkdir -p /opt/lumines-ds
sudo cp lumines_server.py /opt/lumines-ds/
sudo cp deploy/lumines-ds.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lumines-ds
```
Scores live in `/var/lib/lumines-ds/scores.json`; the unit runs as a throwaway user (DynamicUser).
Open the ports: ufw `sudo ufw allow 27620/udp && sudo ufw allow 27621/tcp`, firewalld
`--add-port=27620/udp --add-port=27621/tcp`, nftables `udp dport 27620 accept` + `tcp dport 27621 accept`.

### Windows
Install Python 3 from python.org (tick "Add to PATH"), run `deploy\run_windows.bat`, allow Python through the
firewall (or open 27620/UDP and 27621/TCP).

### Docker
```sh
docker compose up -d --build
```

### Reaching it from the internet
Forward **27620/UDP** and **27621/TCP** on your router to the server. With carrier-grade NAT or two routers in a
row you need forwards on both, or a VPS with a public IP.

### Pointing the game at your server
1. `/data/LuminesDS/server.txt` on the memory card: one line `host:port`, e.g. `your.server:27620`
   (the UDP relay port; high scores use port + 1).
2. Otherwise the default built into the ROM (build the ROM yourself from your own copy of the game): `Собрать_LuminesDS.ps1 -Server your.server:27620` on Windows,
   or `SERVER=your.server:27620 sh tools/build.sh`.

The game shows the current server in the Options menu.

### DS Wi-Fi
The DS only joins **open** or **WEP** networks — no WPA/WPA2. Use a separate SSID without a password (or WEP),
or a laptop/phone hotspot. Configure it from any Nintendo WFC game or a DSi. Keep nothing important on that network.

### Protocol
Documented at the top of `lumines_server.py`.

## License
MIT, see `LICENSE`. Covers the server code in this repository only.

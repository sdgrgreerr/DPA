import asyncio, time, os, urllib.request, urllib.error, ssl, collections, webbrowser, tkinter as tk
from tkinter import messagebox, ttk
import threading
import re
from urllib.parse import urlparse
import sys
import platform
import subprocess
import json
import socket
import ctypes

def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает для dev-режима и для PyInstaller """
    try:
        # PyInstaller создает временную папку _MEIPASS при упаковке в один файл
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath("..")
    return os.path.join(base_path, relative_path)

DB_FILE = "../websites.txt"
DEFAULT_SITES = [
    "https://google.com",
    "https://yandex.ru",
    "https://vk.com",
    "https://habr.com",
    "https://gosuslugi.ru",
    "192.168.1.1"
    "127.0.0.1"
]
# Глобальное хранилище «чистых» данных (наш бэкенд)
site_history = collections.defaultdict(lambda: collections.deque(maxlen=50))
runtime_states = {}  # Сюда задачи будут писать результаты: {'google.com': {'status': 'Доступен', 'ping': '12 мс', ...}}

HTTP_EXPLANATIONS = {
# 1xx: Информационные
100: "100 Continue: Сервер принял заголовки, продолжайте отправку.",
101: "101 Switching Protocols: Переключение протоколов (например, на WebSocket).",
102: "102 Processing: Запрос принят, сервер всё ещё обрабатывает его.",
103: "103 Early Hints: Предварительная отдача заголовков (Link) для предзагрузки.",

# 2xx: Успешно (в HTTPError обычно не попадают, но нужны для полноты)
200: "200 OK: Запрос успешно выполнен.",
201: "201 Created: Ресурс успешно создан.",
202: "202 Accepted: Запрос принят на обработку, но ещё не завершён.",
203: "203 Non-Authoritative Info: Информация получена из стороннего источника.",
204: "204 No Content: Нет содержимого, запрос выполнен успешно.",
205: "205 Reset Content: Требуется сбросить форму или представление.",
206: "206 Partial Content: Частичное содержимое (скачивание кусками).",
207: "207 Multi-Status: Множественный статус (XML-ответ WebDAV).",
208: "208 Already Reported: Статус элемента уже был возвращен ранее.",
226: "226 IM Used: Сервер вернул разницу (Delta) относительно базы.",

# 3xx: Перенаправления
300: "300 Multiple Choices: Несколько вариантов выбора ресурса.",
301: "301 Moved Permanently: Ресурс перемещен навсегда. Направлен редирект.",
302: "302 Found / Moved Temporarily: Ресурс временно перемещен.",
303: "303 See Other: Ресурс доступен по другому URI через метод GET.",
304: "304 Not Modified: Ресурс не изменялся. Используется кэш.",
305: "305 Use Proxy: Доступ к ресурсу только через указанный прокси.",
306: "306 Switch Proxy: Код зарезервирован, больше не используется.",
307: "307 Temporary Redirect: Временный редирект с сохранением метода запроса.",
308: "308 Permanent Redirect: Вечный редирект с сохранением метода запроса.",

# 4xx: Ошибки клиента
400: "400 Bad Request: Некорректный синтаксис запроса.",
401: "401 Unauthorized: Требуется авторизация или неверные учетные данные.",
402: "402 Payment Required: Требуется оплата (экспериментальный / коммерческий).",
403: "403 Forbidden: Доступ заблокирован сервером или файрволом.",
404: "404 Not Found: Страница или файл не найдены на сервере.",
405: "405 Method Not Allowed: Указанный HTTP-метод запрещен для этого URL.",
406: "406 Not Acceptable: Сервер не может отдать контент в нужном формате.",
407: "407 Proxy Auth Required: Требуется авторизация на прокси-сервере.",
408: "408 Request Timeout: Истекло время ожидания запроса клиентом.",
409: "409 Conflict: Конфликт с текущим состоянием ресурса.",
410: "410 Gone: Ресурс удален навсегда и безвозвратно.",
411: "411 Length Required: В запросе не указан заголовок Content-Length.",
412: "412 Precondition Failed: Одно из условий в заголовках не выполнено.",
413: "413 Payload Too Large: Тело запроса слишком велико для обработки.",
414: "414 URI Too Long: Строка URL-адреса слишком длинная.",
415: "415 Unsupported Media Type: Неподдерживаемый формат данных (Content-Type).",
416: "416 Range Not Satisfiable: Запрошенный диапазон байт не может быть отдан.",
417: "417 Expectation Failed: Сервер не может удовлетворить заголовку Expect.",
418: "418 I'm a teapot: Я чайник (Первоапрельская шутка RFC 2324).",
419: "419 Page Expired: Сессия Laravel/CSRF-токен устарел (Неофициальный).",
421: "421 Misdirected Request: Запрос направлен на сервер, который не может выдать ответ.",
422: "422 Unprocessable Content: Данные верны, но содержат логические ошибки.",
423: "423 Locked: Ресурс заблокирован (WebDAV).",
424: "424 Failed Dependency: Сбой из-за неудачного выполнения зависимого запроса.",
425: "425 Too Early: Сервер отказывается обрабатывать запрос из-за риска Replay-атаки.",
426: "426 Upgrade Required: Клиенту необходимо обновить протокол TLS/HTTP.",
428: "428 Precondition Required: Сервер требует отправки условий (If-Match).",
429: "429 Too Many Requests: Ограничение частоты запросов (Rate Limit лимит превышен).",
430: "430 Request Header Fields Too Large: Заголовки Shopify/клиента слишком велики.",
431: "431 Request Header Fields Too Large: Заголовки запроса превысили лимит.",
440: "440 Login Timeout: Время сессии IIS истекло (Microsoft).",
444: "444 No Response: nginx закрыл соединение без возврата ответа.",
449: "449 Retry With: Выполните повторный запрос после указанного действия (Microsoft).",
450: "450 Blocked by Windows Parental Controls: Заблокировано родительским контролем.",
451: "451 Unavailable For Legal Reasons: Доступ закрыт цензурой или правообладателями.",
460: "460 AWS ALB: Клиент закрыл соединение до истечения таймаута балансировщика.",
463: "463 AWS ALB: Заголовок X-Forwarded-For содержит более 30 IP-адресов.",
494: "494 Request Header Too Large: nginx поймал слишком большой заголовок.",
495: "495 SSL Certificate Error: Клиент предоставил невалидный SSL-сертификат (nginx).",
496: "496 SSL Certificate Required: Клиент не предоставил обязательный SSL-сертификат (nginx).",
497: "497 HTTP Request Sent to HTTPS Port: Ошибка отправки HTTP на HTTPS порт (nginx).",
498: "498 Invalid Token: Токен авторизации невалиден или просрочен (Esri).",
499: "499 Client Closed Request: Клиент разорвал соединение, не дождавшись ответа (nginx).",

# 5xx: Ошибки сервера
500: "500 Internal Server Error: Внутренняя критическая ошибка сервера / падение скрипта.",
501: "501 Not Implemented: Сервер не поддерживает метод или функционал запроса.",
502: "502 Bad Gateway: Прокси или шлюз получили некорректный ответ от бэкенда.",
503: "503 Service Unavailable: Сервер перегружен или находится на тех. обслуживании.",
504: "504 Gateway Timeout: Шлюз не дождался ответа от вышестоящего сервера бэкенда.",
505: "505 HTTP Version Not Supported: Версия протокола HTTP не поддерживается.",
506: "506 Variant Also Negotiates: Ошибка конфигурации: выбранный ресурс ссылается сам на себя.",
507: "507 Insufficient Storage: Серверу не хватает места на диске для завершения операции.",
508: "508 Loop Detected: Обнаружено бесконечное перенаправление при обработке ресурса.",
509: "509 Bandwidth Limit Exceeded: Исчерпан лимит трафика, выделенный сайту (Apache/cPanel).",
510: "510 Not Extended: Требуются дальнейшие расширения запроса для его выполнения.",
511: "511 Network Auth Required: Требуется авторизация в сети (клиент за Captive Portal).",
520: "520 Web Server Returned an Unknown Error: Неизвестная ошибка веб-сервера (Cloudflare).",
521: "521 Web Server Is Down: Целевой веб-сервер упал и отказывает в соединении (Cloudflare).",
522: "522 Connection Timed Out: Превышено время ожидания TCP-подключения (Cloudflare).",
523: "523 Origin Is Unreachable: Целевой сервер недоступен по сети (Cloudflare).",
524: "524 A Timeout Occurred: TCP-соединение установлено, но ответ не пришел вовремя (Cloudflare).",
525: "525 SSL Handshake Failed: Сбой рукопожатия SSL/TLS между Cloudflare и бэкендом.",
526: "526 Invalid SSL Certificate: На бэкенде установлен невалидный/просроченный SSL (Cloudflare).",
527: "527 Railgun Error: Сбой связи между прокси-узлом Railgun и сервером (Cloudflare).",
529: "529 Site is overloaded: Сервер перегружен запросами (Qualys/Неофициальный).",
530: "530 Site is frozen: Сайт заморожен хостингом или ошибка Cloudflare 1016.",
561: "561 Unauthorized: Ошибка авторизации на уровне шлюза (AWS ALB).",
598: "598 Network Read Timeout Error: Таймаут чтения сети за прокси-сервером.",
599: "599 Network Connect Timeout Error: Таймаут подключения к сети за прокси-сервером.",

# 6xx: Граница спецификаций
600: "600 Unparsed Response Headers: Ответ вернул невалидные или пустые заголовки."
}
# (Вы можете скопировать сюда абсолютно все коды из вашего старого expl_dict)

site_history = collections.defaultdict(lambda: collections.deque(maxlen=50))

# Глобальный кэш для сети, чтобы UI не зависал при обращении к PowerShell/WMI
network_info_cache = {"type": "disconnected", "speed": 0, "extra": "", "vpn_ip": ""}
wmi_cellular_cache = {"generation": "", "signal": "", "provider": ""}

def load_sites():
    if not os.path.exists(DB_FILE): 
        open(DB_FILE, "w", encoding="utf-8").write("\n".join(DEFAULT_SITES))
        return DEFAULT_SITES.copy()
    return [l.strip() for l in open(DB_FILE, "r", encoding="utf-8") if l.strip()]

def save_sites(s): 
    open(DB_FILE, "w", encoding="utf-8").write("\n".join(s))




def _fetch_network_info_sync():
    """Кроссплатформенный сбор данных сети без внешних зависимостей."""
    # По умолчанию считаем, что устройство подключено, пока не доказано обратное
    info = {"type": "connected", "speed": 0, "extra": "", "vpn_ip": ""}
    current_os = platform.system().lower()

    if current_os == "windows":
        # Проверка физического подключения к сети через WinINet API
        try:
            flags = ctypes.c_ulong()
            if not ctypes.windll.wininet.InternetGetConnectedState(ctypes.byref(flags), 0):
                info["type"] = "disconnected"
                return info
        except:
            pass

        # Корректные свойства Windows: Name, InterfaceDescription, MajorType, Speed
        # Speed возвращает скорость в бит/с (числом), что избавляет от парсинга строк
        cmd = (
            "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
            "Select-Object Name, InterfaceDescription, MajorType, Speed | ConvertTo-Json"
        )
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # Используем cp866/cp1251 для корректного чтения кириллицы из консоли Windows
            res = subprocess.check_output(
                ["powershell", "-Command", cmd],
                startupinfo=startupinfo,
                timeout=3
            ).decode('cp1251', errors='ignore')

            if res.strip():
                data = json.loads(res)
                adapters = data if isinstance(data, list) else [data]

                for adapter in adapters:
                    name = str(adapter.get("Name", "")).lower()
                    desc = str(adapter.get("InterfaceDescription", "")).lower()
                    # MajorType: 1 = Ethernet, 2 = Wireless, 3 = Кабель/Туннель и т.д.
                    major_type = str(adapter.get("MajorType", ""))

                    # Безопасный перевод скорости из бит/с в Мбит/с
                    try:
                        raw_speed = int(adapter.get("Speed", 0))
                        speed_val = int(raw_speed / 1_000_000)  # Mbps
                    except:
                        speed_val = 0

                    # 1. ПРОВЕРКА НА WI-FI
                    if major_type == "2" or "wi-fi" in name or "wlan" in desc or "wireless" in desc or "wifi" in name:
                        ssid = ""
                        try:
                            wlan_res = subprocess.check_output(
                                ["netsh", "wlan", "show", "interfaces"],
                                startupinfo=startupinfo, timeout=1
                            ).decode('cp866', errors='ignore')
                            for line in wlan_res.split('\n'):
                                if "SSID" in line and "BSSID" not in line:
                                    ssid = line.split(":")[-1].strip()
                                    break
                        except:
                            pass
                        info.update({"type": "wifi", "speed": speed_val, "extra": ssid if ssid else "Wi-Fi сеть"})
                        return info

                    # 2. ПРОВЕРКА НА МОБИЛЬНЫЙ МОДЕМ
                    elif "cellular" in name or "wwan" in name or "modem" in desc or "mobile" in desc:
                        info.update({"type": "modem", "speed": speed_val, "extra": "Мобильный модем"})
                        return info

                    # 3. ПРОВЕРКА НА VPN
                    elif "vpn" in name or "tap" in desc or "tun" in desc or "tunnel" in name:
                        info.update({"type": "vpn", "speed": speed_val, "extra": "VPN Соединение"})
                        return info

                    # 4. ПРОВОДНОЙ ИНТЕРНЕТ (Ethernet)
                    elif major_type == "1" or "ethernet" in name or "lan" in desc or "802.3" in name:
                        info.update({"type": "ethernet", "speed": speed_val, "extra": "Проводная сеть"})
                        # Не делаем тут return, чтобы если есть Wi-Fi/VPN, они определились в приоритете
        except:
            # Если PowerShell отвалился, но WinINet сказал, что коннект есть — оставляем generic "connected"
            pass

    else:
        # Блок для Linux / macOS
        try:
            # 1. Проверяем наличие интернета и получаем локальный IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            info["type"] = "ethernet"  # Дефолт для Linux, если интерфейс не распознан
            info["extra"] = "Проводное подключение"

            # 2. Определяем имя интерфейса по локальному IP (через команду ip route / netstat)
            # Так как в local_ip лежит только строка вида "192.168.1.45"
            try:
                if current_os == "linux":
                    # Ищем какой интерфейс привязан к шлюзу по умолчанию
                    route_res = subprocess.check_output(["ip", "route", "get", "8.8.8.8"], timeout=1).decode('utf-8')
                    # Строка вида: "8.8.8.8 dev wlan0 src 192.168.1.45 ..."
                    if "dev" in route_res:
                        iface = route_res.split("dev")[1].split()[0].lower()

                        if iface.startswith(("wlan", "wlp", "wl")):
                            info.update({"type": "wifi", "extra": f"Wi-Fi ({iface})"})
                        elif iface.startswith(("tun", "tap", "wg", "ppp")):
                            info.update({"type": "vpn", "extra": "VPN туннель", "vpn_ip": local_ip})
                        elif iface.startswith(("rmnet", "cdc", "usb")):
                            info.update({"type": "modem", "extra": "Мобильный модем"})

                elif current_os == "darwin":  # macOS
                    route_res = subprocess.check_output(["route", "-n", "get", "8.8.8.8"], timeout=1).decode('utf-8')
                    for line in route_res.split('\n'):
                        if "interface:" in line:
                            iface = line.split(":")[-1].strip().lower()
                            if "en0" in iface:  # На маках en0 обычно Wi-Fi (или первый Ethernet)
                                info.update({"type": "wifi", "extra": "Беспроводная сеть Mac"})
                            elif "tun" in iface or "ppp" in iface:
                                info.update({"type": "vpn", "extra": "VPN", "vpn_ip": local_ip})
                            break
            except:
                # Если команды ip/route не сработали, делаем базовую проверку подсетей VPN
                if local_ip.startswith(("10.8.", "10.0.", "172.16.")):
                    info.update({"type": "vpn", "vpn_ip": local_ip, "extra": "Вероятный VPN"})

        except:
            info["type"] = "disconnected"

    return info


# Тестовый запуск Dyna
if __name__ == "__main__":
    print(_fetch_network_info_sync())


def fetch_wmi_and_network_loop():
    """Кроссплатформенный фоновый поток. Больше не импортирует WMI."""
    global network_info_cache, wmi_cellular_cache
    current_os = platform.system().lower()

    while True:
        try:
            network_info_cache = _fetch_network_info_sync()
        except:
            pass

        # Опрос специфичных мобильных утилит netsh делаем ТОЛЬКО на Windows
        if current_os == "windows":
            try:
                cmd_wwan = "netsh mbn show connection interface=*"
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                out = subprocess.check_output(cmd_wwan, startupinfo=startupinfo, timeout=2).decode('cp866',
                                                                                                   errors='ignore')

                gen = "Модем"
                provider = ""
                for line in out.split('\n'):
                    if "Технология" in line or "Technology" in line or "Сеть" in line:
                        val = line.split(":")[-1].strip().upper()
                        if "LTE" in val or "4G" in val:
                            gen = "4G (LTE)"
                        elif "5G" in val:
                            gen = "5G"
                        elif "UMTS" in val or "HSDPA" in val or "HSUPA" in val or "3G" in val or "HSPA" in val:
                            gen = "3G (H+)"
                        elif "GPRS" in val or "EDGE" in val or "2G" in val:
                            gen = "2G"
                    if "Поставщик" in line or "Provider" in line or "Оператор" in line:
                        provider = line.split(":")[-1].strip()

                wmi_cellular_cache["generation"] = gen
                if provider:
                    wmi_cellular_cache["provider"] = provider
            except:
                if network_info_cache["type"] == "modem" and not wmi_cellular_cache["generation"]:
                    wmi_cellular_cache["generation"] = "Моб. сеть"
        else:
            # На Mac/Linux зануляем кэш сотовых данных WMI
            wmi_cellular_cache = {"generation": "", "signal": "", "provider": ""}

        time.sleep(4)


def win32_ping(host, port=80, timeout=3.0):
    """
    Легкий кроссплатформенный пинг через замер времени TCP-соединения.
    Не требует прав администратора и не создает тяжелых процессов в ОС.
    """
    # Если на вход пришла ссылка, очищаем её до чистого домена/IP
    if host.startswith(("http://", "https://")):
        try:
            parsed = urlparse(host)
            port = 443 if parsed.scheme == "https" else 80
            host = parsed.hostname or host
        except:
            pass

    host = host.strip()

    # Создаем сокет и засекаем время
    start_time = time.perf_counter()
    try:
        # socket.create_connection автоматически делает резолв DNS и пробует подключиться
        with socket.create_connection((host, port), timeout=timeout) as sock:
            end_time = time.perf_counter()
            ping_ms = (end_time - start_time) * 1000
            return True, ping_ms, "OK", f"Порт {port} ответил"
    except socket.gaierror:
        return False, None, "Ошибка DNS", "Узел не найден в сети."
    except (socket.timeout, TimeoutError):
        return False, None, "Таймаут", "Превышено время ожидания ответа порта."
    except ConnectionRefusedError:
        # Порт закрыт, но узел-то ответил! Значит он живой.
        end_time = time.perf_counter()
        ping_ms = (end_time - start_time) * 1000
        return True, ping_ms, "OK (Порт закрыт)", "Узел активен, но порт отклонил соединение."
    except Exception as e:
        return False, None, "Сбой сети", str(e)


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.label = None  
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 15
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        self.label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#313244", foreground="#cdd6f4",
                              relief=tk.SOLID, borderwidth=1, font=("Arial", 9, "normal"), padx=8, pady=4)
        self.label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        self.label = None
        if tw: tw.destroy()

    def update_text(self, new_text):
        self.text = new_text
        if self.tip_window and self.label:
            self.label.config(text=new_text)


class DetailWindow(tk.Toplevel):
    def __init__(self, parent, url_value):
        # ... (сохраняем вашу базовую логику инициализации) ...
        if hasattr(parent, 'root'):
            self.app = parent
            master_window = parent.root
        else:
            self.app = None
            master_window = parent

        super().__init__(master_window)

        # Установка иконки для окна аналитики, если файл существует
        if os.path.exists("../DPA.ico"):
            try:
                self.iconbitmap("DPA.ico")
            except Exception:
                pass

        self.url = url_value
        self.title(f"Аналитика: {self.url}")
        # ... (весь остальной ваш код без изменений) ...

        self.geometry("600x520")
        self.configure(bg="#1e1e2e")
        self.transient(master_window)

        tk.Label(self, text=f"Мониторинг {self.url}", bg="#1e1e2e", fg="#cdd6f4", font=("Arial", 12, "bold")).pack(pady=5)
        if self.url.startswith(("http://", "https://")):
            tk.Button(self, text="🌐 Открыть адрес в браузере", bg="#89b4fa", fg="#11111b", activebackground="#b4befe",
                      relief=tk.FLAT, font=("Arial", 9, "bold"), command=self.open_in_browser, padx=10).pack(pady=2)

        self.canvas = tk.Canvas(self, bg="#252538", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        ef = tk.LabelFrame(self, text=" Разъяснение последней проблемы ", bg="#1e1e2e", fg="#f38ba8", font=("Arial", 10, "bold"))
        ef.pack(fill=tk.X, padx=15, pady=10)
        self.err_text = tk.Text(ef, bg="#181825", fg="#cdd6f4", font=("Arial", 9), height=4, relief=tk.FLAT, wrap=tk.WORD)
        self.err_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.err_text.config(state=tk.DISABLED)
        self.update_loop()
        self._resize_timer = None
        self.bind("<Configure>", self._on_window_resize)

    def open_in_browser(self):
        if self.url: webbrowser.open(self.url)

    def update_loop(self):
        if self.winfo_exists():
            # Рисуем по таймеру только если окно сейчас НЕ растягивают
            if self._resize_timer is None:
                self.draw_chart()
                self.update_error_info()
            # Увеличиваем интервал до 3 секунд, чтобы снизить нагрузку
            self.after(3000, self.update_loop)

    def _on_window_resize(self, event):
        """Вызывается при изменении размера. Отменяет прошлую отрисовку."""
        # СТРОГАЯ ПРОВЕРКА: реагируем ТОЛЬКО на изменение размеров самого окна
        if event.widget != self:
            return

        if self._resize_timer is not None:
            self.after_cancel(self._resize_timer)

        # Ждем 200 мс после окончания движения мыши перед перерисовкой
        self._resize_timer = self.after(200, self._trigger_redraw)

    def _trigger_redraw(self):
        """Выполняется один раз, когда окно зафиксировано"""
        self._resize_timer = None
        if self.winfo_exists():
            self.draw_chart()
            self.update_error_info()

    def draw_chart(self):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 10 or h < 10: return

        hist = list(site_history.get(self.url, []))
        if not hist:
            self.canvas.create_text(w / 2, h / 2, text="Нет данных для построения графика...", fill="#6c7086")
            return

        pl, pr, pt, pb = 50, 25, 30, 45
        gw, gh = w - pl - pr, h - pt - pb

        self.canvas.create_line(pl, pt, pl, h - pb, fill="#45475a")
        self.canvas.create_line(pl, h - pb, w - pr, h - pb, fill="#45475a")

        pings = [i[1] for i in hist if i[1] is not None]
        mx = max(pings) if pings else 10.0
        if mx <= 0: mx = 10.0

        self.canvas.create_text(pl - 10, pt, text=f"{mx:.0f}", fill="#a6adc8", anchor=tk.E)
        self.canvas.create_text(pl - 10, pt + gh / 2, text=f"{mx / 2:.0f}", fill="#a6adc8", anchor=tk.E)
        self.canvas.create_text(pl - 10, h - pb, text="0", fill="#a6adc8", anchor=tk.E)

        sx = gw / max(len(hist) - 1, 1)
        pts, skip_label = [], max(1, len(hist) // 5)

        for i, item in enumerate(hist):
            ts, ping, status, _ = item
            x = pl + i * sx
            t_str = time.strftime("%H:%M:%S", time.localtime(ts))

            if ping is not None:
                y = (h - pb) - (ping / mx * gh)
                pts.append((x, y, status, ping))
                self.canvas.create_line(x, h - pb, x, y, fill="#313244", dash=(2, 2))
            else:
                self.canvas.create_rectangle(x - max(1, sx / 2), pt, x + max(1, sx / 2), h - pb, fill="#3a2330", outline="")
                self.canvas.create_line(x, h - pb, x, pt, fill="#f38ba8", dash=(4, 4))

            if i % skip_label == 0 or i == len(hist) - 1:
                self.canvas.create_line(x, h - pb, x, h - pb + 4, fill="#45475a")
                self.canvas.create_text(x, h - pb + 15, text=t_str, fill="#a6adc8", font=("Arial", 8))

        if len(pts) > 1:
            coords = []
            for p in pts: coords.extend([p[0], p[1]])
            self.canvas.create_line(coords, fill="#89b4fa", width=2)

        for x, y, status, val in pts:
            dot_color = "#a6e3a1" if status == "OK" else "#f9e2af"
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=dot_color, outline="#1e1e2e")
            self.canvas.create_text(x, y - 10, text=f"{val:.0f}", fill="#cdd6f4", font=("Arial", 7, "bold"))

    def update_error_info(self):
        hist = list(site_history.get(self.url, []))
        if not hist: return
        _, _, st, dt = hist[-1]

        self.err_text.config(state=tk.NORMAL)
        self.err_text.delete("1.0", tk.END)

        # 1. Пробиваемся к таблице, даже если parent — это просто root
        table_status = ""
        tree_widget = None

        # Способ А: Если передали self приложения
        if self.app and hasattr(self.app, 'tree'):
            tree_widget = self.app.tree
        # Способ Б: Если передали self.root, ищем Treeview среди всех виджетов приложения
        elif self.master:
            for child in self.master.winfo_children():
                # Ищем Treeview внутри фреймов или напрямую в корне
                if isinstance(child, ttk.Treeview):
                    tree_widget = child
                    break
                if hasattr(child, 'winfo_children'):
                    for sub_child in child.winfo_children():
                        if isinstance(sub_child, ttk.Treeview):
                            tree_widget = sub_child
                            break
                    if tree_widget: break

        # Если нашли таблицу, ищем строку с нашим URL и забираем её текст
        if tree_widget:
            try:
                for item_id in tree_widget.get_children():
                    vals = tree_widget.item(item_id, "values")
                    if vals and vals[0] == self.url:
                        table_status = str(vals)
                        break
            except:
                pass

        # Ищем 3 цифры кода ответа во всех источниках (таблица, статус, история)
        code_match = re.search(r'\b\d{3}\b', f"{table_status} {st} {dt}")
        explanation = ""

        if code_match:
            code_int = int(code_match.group(0))
            explanation = HTTP_EXPLANATIONS.get(code_int, "")
        elif st == "OK":
            explanation = HTTP_EXPLANATIONS.get(200, "200 OK: Запрос успешно выполнен.")

        # 2. Определяем цвет иконки (для 307 и прочих редиректов/ошибок — красная)
        is_success = (st == "OK" and (not code_match or 200 <= int(code_match.group(0)) < 300))
        icon = "🟢" if is_success else "🔴"

        # 3. Выводим итоговый текст
        if explanation:
            full_report = f"{icon} Статус: {st}\n──────────────────────────────────────\n🔍 Разбор ответа:\n{explanation}"
        else:
            full_report = f"{icon} Статус: {st}\n──────────────────────────────────────\n🔍 Разбор ответа:\n{dt if dt else 'Нет дополнительных данных.'}"

        self.err_text.insert(tk.END, full_report)
        self.err_text.config(state=tk.DISABLED)


class AdvancedStatsWindow(tk.Toplevel):
    def __init__(self, parent, tree_widget):
        super().__init__(parent)
        self.tree = tree_widget
        self.title("Глобальная статистика и качество сети")
        self.geometry("750x640")
        self.configure(bg="#1e1e2e")
        self.transient(parent)


        net_frame = tk.Frame(self, bg="#252538", padx=15, pady=15)
        net_frame.pack(fill=tk.X, padx=15, pady=10)

        self.net_icon_canvas = tk.Canvas(net_frame, width=150, height=80, bg="#252538", highlightthickness=0)
        self.net_icon_canvas.pack(side=tk.LEFT, padx=5)

        text_block = tk.Frame(net_frame, bg="#252538")
        text_block.pack(side=tk.LEFT, padx=15, fill=tk.Y)

        self.net_type_label = tk.Label(text_block, text="Анализ сети...", bg="#252538", fg="#89b4fa", font=("Arial", 14, "bold"), anchor=tk.W)
        self.net_type_label.pack(anchor=tk.W)

        self.net_speed_label = tk.Label(text_block, text="Скорость адаптера: --", bg="#252538", fg="#a6adc8", font=("Arial", 11), anchor=tk.W)
        self.net_speed_label.pack(anchor=tk.W, pady=2)

        self.status_label = tk.Label(text_block, text="Качество связи: расчет...", bg="#252538", fg="#cdd6f4", font=("Arial", 11, "bold"), anchor=tk.W)
        self.status_label.pack(anchor=tk.W)

        self.tooltip = ToolTip(self.net_icon_canvas, "")

        info_frame = tk.Frame(self, bg="#1e1e2e")
        info_frame.pack(fill=tk.X, padx=15, pady=5)

        self.info_text_label = tk.Label(info_frame, text="", bg="#1e1e2e", fg="#a6adc8", font=("Arial", 10), justify=tk.LEFT, anchor=tk.W)
        self.info_text_label.pack(fill=tk.X, padx=5)

        tk.Label(self, text=" Сводный график всех подключений (последние 50 запросов) ", bg="#1e1e2e", fg="#cdd6f4", font=("Arial", 10, "bold")).pack(pady=5)

        self.chart_canvas = tk.Canvas(self, bg="#252538", highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.colors = ["#a6e3a1", "#89b4fa", "#f9e2af", "#f38ba8", "#cba6f7", "#f5e0dc", "#fab387", "#94e2d5", "#74c7ec", "#b4befe", "#a6e3a1", "#f2cdcd"]
        self._resize_timer = None
        self.bind("<Configure>", self._on_window_resize)

        self.update_loop()
    def draw_network_visual(self, net_info, quality_percent):
        self.net_icon_canvas.delete("all")
        ntype = net_info["type"]
        
        main_color = "#a6e3a1" if quality_percent > 50 else "#f9e2af"
        if ntype == "disconnected": main_color = "#f38ba8"

        if ntype == "disconnected":
            self.net_icon_canvas.create_rectangle(30, 20, 90, 55, outline="#6c7086", width=3)
            self.net_icon_canvas.create_line(45, 55, 35, 70, fill="#6c7086", width=4)
            self.net_icon_canvas.create_line(75, 55, 85, 70, fill="#6c7086", width=4)
            self.net_icon_canvas.create_line(30, 70, 90, 70, fill="#6c7086", width=4)
            self.net_icon_canvas.create_line(100, 20, 125, 45, fill="#f38ba8", width=5)
            self.net_icon_canvas.create_line(125, 20, 100, 45, fill="#f38ba8", width=5)

        elif ntype == "ethernet":
            self.net_icon_canvas.create_rectangle(15, 25, 65, 55, fill="#45475a", outline="#cdd6f4", width=2)
            self.net_icon_canvas.create_rectangle(65, 32, 85, 48, fill="#b4befe", outline="")
            line_colors = ["#f38ba8", "#fab387", "#f9e2af", "#a6e3a1", "#89b4fa", "#cba6f7", "#b4befe", "#a6adc8"]
            for i, col in enumerate(line_colors):
                y_pos = 28 + (i * 3.5)
                self.net_icon_canvas.create_line(65, y_pos, 135, y_pos, fill=col, width=2.5)

        elif ntype == "wifi":
            cx, cy = 75, 65
            self.net_icon_canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill=main_color, outline="")
            self.net_icon_canvas.create_arc(cx-20, cy-20, cx+20, cy+20, start=35, extent=110, style=tk.ARC, outline=main_color, width=3)
            self.net_icon_canvas.create_arc(cx-40, cy-40, cx+40, cy+40, start=35, extent=110, style=tk.ARC, outline=main_color, width=4)
            self.net_icon_canvas.create_arc(cx-60, cy-60, cx+60, cy+60, start=35, extent=110, style=tk.ARC, outline=main_color, width=5)

        elif ntype == "modem":
            self.net_icon_canvas.create_rectangle(20, 30, 80, 55, fill="#313244", outline="#89b4fa", width=2)
            self.net_icon_canvas.create_rectangle(80, 37, 95, 48, fill="#a6adc8", outline="")
            self.net_icon_canvas.create_oval(30, 40, 36, 46, fill="#a6e3a1")
            
            for i in range(4):
                hx = 105 + (i * 8)
                hy = 55 - (i * 8)
                self.net_icon_canvas.create_rectangle(hx, hy, hx+5, 55, fill="#fab387", outline="")
            
            gen_text = wmi_cellular_cache.get("generation", "Моб.")
            self.net_icon_canvas.create_text(50, 18, text=gen_text, fill="#f9e2af", font=("Arial", 11, "bold"))

        elif ntype == "vpn":
            self.net_icon_canvas.create_rectangle(10, 35, 40, 55, fill="#313244", outline="#cdd6f4")
            self.net_icon_canvas.create_line(5, 55, 45, 55, fill="#cdd6f4", width=2)
            self.net_icon_canvas.create_rectangle(110, 20, 140, 60, fill="#181825", outline="#f9e2af", width=2)
            self.net_icon_canvas.create_oval(115, 28, 121, 34, fill="#a6e3a1")
            self.net_icon_canvas.create_rectangle(45, 38, 105, 52, fill="#2e3752", outline="#89b4fa", width=2)
            self.net_icon_canvas.create_line(45, 45, 105, 45, fill="#cba6f7", dash=(3,3), width=2)

    def update_loop(self):
        if self.winfo_exists():
            # Если окно не меняет размер, делаем плановое обновление
            if self._resize_timer is None:
                self.calculate_and_draw()
            # Заменяем 1000 мс на 3000 мс, чтобы не грузить процессор каждую секунду
            self.after(3000, self.update_loop)

    def _on_window_resize(self, event):
        """Срабатывает при растягивании окна общей статистики"""
        # СТРОГАЯ ПРОВЕРКА: игнорируем изменения размеров внутренних фреймов и Canvas
        if event.widget != self:
            return

        if self._resize_timer is not None:
            self.after_cancel(self._resize_timer)

        # 200 миллисекунд тишины — и только тогда рисуем сложный график
        self._resize_timer = self.after(200, self._trigger_redraw)

    def _trigger_redraw(self):
        """Финальный разовый расчет геометрии графиков"""
        self._resize_timer = None
        if self.winfo_exists():
            self.calculate_and_draw()

    def calculate_and_draw(self):
        children = self.tree.get_children()
        if not children:
            self.status_label.config(text="Нет данных")
            return

        total_ping, valid_pings_count = 0, 0
        oks, warns, crits = 0, 0, 0
        all_sites = []

        for child in children:
            tags = self.tree.item(child, "tags")
            values = self.tree.item(child, "values")
            url = values[0]
            ping_str = values[2]  # Номер ячейки "Пинг"
            all_sites.append(url)

            if "ok" in tags:
                oks += 1
            elif "warn" in tags:
                warns += 1
            elif "crit" in tags:
                crits += 1

            if "мс" in ping_str and "⏱" not in ping_str:
                try:
                    val = float(ping_str.replace(" мс", ""))
                    total_ping += val
                    valid_pings_count += 1
                except ValueError:
                    pass

        avg_ping = total_ping / valid_pings_count if valid_pings_count > 0 else 0

        total_points, total_checks = 0.0, 0
        for url in all_sites:
            hist = list(site_history.get(url, []))
            for item in hist:
                status = item[2]
                total_checks += 1
                if status == "OK":
                    total_points += 1.0
                elif "WARN" in str(status):
                    total_points += 0.5

        if total_checks == 0:
            total_checks = len(children) if len(children) > 0 else 1
            total_points = (oks * 1.0) + (warns * 0.5)

        quality_percent = (total_points / total_checks) * 100

        # Мгновенное чтение данных из безопасного фонового кэша
        net_info = network_info_cache
        net_gen = wmi_cellular_cache.get("generation", "")
        provider = wmi_cellular_cache.get("provider", "")

        ru_types = {
            "disconnected": "❌ Сеть отключена / Оффлайн",
            "ethernet": "🔌 Проводное подключение (Кабель)",
            "wifi": f"📶 Беспроводная сеть ({net_info['extra']})",
            "modem": f"🚀 Модем ({net_gen})" + (f" [{provider}]" if provider else ""),
            "vpn": "🔒 Виртуальная сеть (VPN туннель)"
        }

        self.net_type_label.config(text=ru_types.get(net_info["type"], "Неизвестное подключение"))

        if net_info["speed"] > 0:
            speed_text = f"{net_info['speed']} Мбит/с" if net_info["speed"] < 1000 else f"{net_info['speed'] / 1000:.1f} Гбит/с"
            self.net_speed_label.config(text=f"Скорость порта адаптера: {speed_text}")
        else:
            self.net_speed_label.config(text="Скорость порта адаптера: не определена")

        if net_info["type"] == "vpn" and net_info["vpn_ip"]:
            self.net_speed_label.config(text=f"Адрес шифрования: {net_info['vpn_ip']}")

        self.status_label.config(text=f"Качество стабильности узлов: {quality_percent:.1f}%")

        self.tooltip.update_text(f"Текущая сеть: {ru_types.get(net_info['type'])}\nСтабильность: {quality_percent:.1f}%")
        self.draw_network_visual(net_info, quality_percent)

        info_msg = f"Средний пинг доступных ресурсов: {avg_ping:.2f} мс  |  Всего хостов: {len(children)}" #
        info_msg += f"🟢 Доступно: {oks}   🟡 Предупреждений: {warns}   🔴 Критических ошибок: {crits}"
        self.info_text_label.config(text=info_msg)

        self.chart_canvas.delete("all")
        cw, ch = self.chart_canvas.winfo_width(), self.chart_canvas.winfo_height()
        if cw < 20 or ch < 20: return

        pl, pr, pt, pb = 60, 180, 20, 40
        gw, gh = cw - pl - pr, ch - pt - pb

        self.chart_canvas.create_line(pl, pt, pl, ch - pb, fill="#45475a")
        self.chart_canvas.create_line(pl, ch - pb, cw - pr, ch - pb, fill="#45475a")

        global_max, max_len = 10.0, 1
        for url in all_sites:
            hist = list(site_history.get(url, []))
            if len(hist) > max_len:
                max_len = len(hist)
            pings = [item[1] for item in hist if item is not None and item[1] is not None]
            if pings:
                m = max(pings)
                if m > global_max:
                    global_max = m

        self.chart_canvas.create_text(pl - 10, pt, text=f"{global_max:.0f} мс", fill="#a6adc8", anchor=tk.E)
        self.chart_canvas.create_text(pl - 10, pt + gh / 2, text=f"{global_max / 2:.0f} мс", fill="#a6adc8", anchor=tk.E)
        self.chart_canvas.create_text(pl - 10, ch - pb, text="0", fill="#a6adc8", anchor=tk.E)

        sx = gw / max(max_len - 1, 1)

        for idx, url in enumerate(all_sites):
            hist = list(site_history.get(url, []))
            if not hist: continue

            color = self.colors[idx % len(self.colors)]
            coords = []

            for i, item in enumerate(hist):
                x = pl + i * sx
                ping = item[1]

                if ping is not None:
                    y = (ch - pb) - (ping / global_max * gh)
                    coords.extend([x, y])
                else:
                    self.chart_canvas.create_line(x, ch - pb, x, ch - pb - 8, fill="#f38ba8", width=1.5)

            if len(coords) >= 4:
                self.chart_canvas.create_line(coords, fill=color, width=2)
                self.chart_canvas.create_oval(coords[-2] - 3, coords[-1] - 3, coords[-2] + 3, coords[-1] + 3, fill=color, outline="#1e1e2e")

            ly = pt + (idx * 20)
            if ly < ch - 10:
                self.chart_canvas.create_rectangle(cw - pr + 15, ly + 4, cw - pr + 27, ly + 14, fill=color, outline="")
                short_url = url.replace("https://", "").replace("http://", "")
                if len(short_url) > 22:
                    short_url = short_url[:20] + "..."
                self.chart_canvas.create_text(cw - pr + 35, ly + 9, text=short_url, fill="#cdd6f4", font=("Arial", 8), anchor=tk.W)

class DynamicPingApp:
    def __init__(self, root, loop):
        self.root, self.loop, self.sites, self.row_map, self.running_tasks = root, loop, load_sites(), {}, {}
        self.root.geometry("1150x500") # Вместо 960x500
        self.root.configure(bg="#1e1e2e")

        self.root.bind("<FocusIn>", lambda e: self.update_title(True))
        self.root.bind("<FocusOut>", lambda e: self.update_title(False))
        self.update_title(True)

        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Treeview", background="#252538", foreground="#cdd6f4", fieldbackground="#252538", rowheight=28, font=("Arial", 9))
        s.map("Treeview", background=[("selected", "#45475a")])
        s.configure("Treeview.Heading", background="#313244", foreground="#cdd6f4", borderwidth=0, font=("Arial", 9, "bold"))

        tf = tk.Frame(root, bg="#1e1e2e", padx=10, pady=10)
        tf.pack(fill=tk.X)
        tk.Label(tf, text="Добавить URL/IP:", bg="#1e1e2e", fg="#cdd6f4", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        self.url_entry = tk.Entry(tf, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", relief=tk.FLAT, font=("Arial", 10), width=30)
        self.url_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        self.url_entry.bind("<Return>", lambda e: self.add_site_event())

        tk.Button(tf, text="Добавить", bg="#a6e3a1", fg="#11111b", activebackground="#94e2d5", relief=tk.FLAT, font=("Arial", 9, "bold"), command=self.add_site_event, padx=8).pack(side=tk.LEFT, padx=3)
        tk.Button(tf, text="Удалить", bg="#f38ba8", fg="#11111b", activebackground="#e07a96", relief=tk.FLAT, font=("Arial", 9, "bold"), command=self.delete_site_event, padx=8).pack(side=tk.LEFT, padx=3)
        tk.Button(tf, text="Статистика", bg="#89b4fa", fg="#11111b", activebackground="#b4befe", relief=tk.FLAT, font=("Arial", 9, "bold"), command=self.show_statistics, padx=8).pack(side=tk.LEFT, padx=3)
        
        tk.Label(tf, text="💡 Дважды кликните для аналитики", bg="#1e1e2e", fg="#a6adc8", font=("Arial", 8, "italic")).pack(side=tk.RIGHT, padx=5)

        table_frame = tk.Frame(root, bg="#1e1e2e", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Обновленный интерфейс таблицы: 4 колонки
        self.tree = ttk.Treeview(table_frame, columns=("url", "status", "ping", "time"), show="headings", selectmode="browse")
        self.tree.heading("url", text="Адрес ресурса")
        self.tree.heading("status", text="Статус")
        self.tree.heading("ping", text="ping ms")
        self.tree.heading("time", text="HTTP/S ms")
        
        self.tree.column("url", width=200, anchor=tk.W)
        self.tree.column("status", width=550, anchor=tk.W)
        self.tree.column("ping", width=110, anchor=tk.CENTER)
        self.tree.column("time", width=250, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.tag_configure("ok", foreground="#a6e3a1")
        self.tree.tag_configure("warn", foreground="#f9e2af")
        self.tree.tag_configure("crit", foreground="#f38ba8")

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<ButtonPress-1>", self.prevent_deselection)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_drag_release)
        self.root.selection_handle(self.export_row_data)

        self.drag_data = {"item": None}
        self.update_table_rows()
        self.tk_async_bridge()

    def update_title(self, is_focused):
        self.root.title("Dynamic Ping Alive" if is_focused else "DPA")

    def tk_async_bridge(self):
        self.root.after(20, self.tk_async_bridge)

    def prevent_deselection(self, event):
        element_under_mouse = self.tree.identify_row(event.y)
        region = self.tree.identify_region(event.x, event.y)
        current_selection = self.tree.selection()

        if not element_under_mouse or region == "heading": return "break"
        if current_selection and element_under_mouse == current_selection[0]:
            self.tree.selection_clear()
            self.tree.focus("")
            return "break"
        self.drag_data["item"] = element_under_mouse

    def on_drag_motion(self, event):
        if not self.drag_data["item"]: return
        target_item = self.tree.identify_row(event.y)
        if target_item and target_item != self.drag_data["item"]:
            self.tree.move(self.drag_data["item"], self.tree.parent(target_item), self.tree.index(target_item))

    def on_drag_release(self, event):
        if self.drag_data["item"]:
            self.sites = [self.tree.item(child, "values")[0] for child in self.tree.get_children()]
            save_sites(self.sites)
            self.drag_data["item"] = None

    def export_row_data(self, offset, length):
        selection = self.tree.selection()
        if not selection: return ""
        text_data = "\t".join(self.tree.item(selection[0], "values"))
        return text_data.encode('utf-8')[int(offset):int(offset) + int(length)]

    def on_double_click(self, event):
        item = self.tree.selection()
        if item: DetailWindow(self.root, self.tree.item(item[0], "values")[0])

    def update_table_rows(self):
        for u in self.sites:
            if u not in self.row_map:
                self.row_map[u] = self.tree.insert("", tk.END, values=(u, "В очереди...", "⏱ ...", "⏱ ..."))
                self.running_tasks[u] = asyncio.run_coroutine_threadsafe(self.individual_site_loop(u), self.loop)

    def add_site_event(self):
        url = self.url_entry.get().strip()
        if not url: return
        u = url
        if u in self.sites:
            messagebox.showinfo("Инфо", "Этот адрес уже отслеживается!")
            return

        focused_item = self.tree.focus()
        if focused_item:
            target_index = self.tree.index(focused_item) + 1
            self.sites.insert(self.sites.index(self.tree.item(focused_item, "values")[0]) + 1, u)
        else:
            target_index = tk.END
            self.sites.append(u)

        save_sites(self.sites)
        new_item = self.tree.insert("", target_index, values=(u, "В очереди...", "⏱ ...", "⏱ ..."))
        self.row_map[u] = new_item
        self.running_tasks[u] = asyncio.run_coroutine_threadsafe(self.individual_site_loop(u), self.loop)

        self.url_entry.delete(0, tk.END)
        self.tree.selection_clear()
        self.tree.selection_set(new_item)
        self.tree.focus(new_item)

    def delete_site_event(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Внимание", "Выберите ресурс из списка для удаления!")
            return

        url_to_remove = self.tree.item(selected_item[0], "values")[0]
        if url_to_remove in self.sites:
            self.sites.remove(url_to_remove)
            save_sites(self.sites)

        if url_to_remove in self.running_tasks:
            self.running_tasks.get(url_to_remove).cancel()
            del self.running_tasks[url_to_remove]

        if 'site_history' in globals() and url_to_remove in site_history: del site_history[url_to_remove]

        if url_to_remove in self.row_map:
            self.tree.delete(self.row_map[url_to_remove])
            del self.row_map[url_to_remove]

    def show_statistics(self):
        AdvancedStatsWindow(self.root, self.tree)

    async def individual_site_loop(self, url):
        try:
            while url in self.sites:
                st_t = time.perf_counter()

                # Флаги состояния для аниматора
                self.ping_done = False
                self.http_done = False
                self.stop_anim = False

                self.current_p_txt = "⏱ ..."
                self.current_t_txt = "⏱ ..."

                async def anim():
                    while not self.stop_anim:
                        try:
                            if url in self.row_map:
                                item_id = self.row_map[url]
                                if self.tree.exists(item_id):
                                    elapsed = (time.perf_counter() - st_t) * 1000

                                    # Анимируем строго свою колонку в зависимости от этапа
                                    p_cell = f"⏱ {elapsed:.0f} мс..." if not self.ping_done else self.current_p_txt
                                    t_cell = f"⏱ {elapsed:.0f} мс..." if (
                                                self.ping_done and not self.http_done) else self.current_t_txt

                                    # Специальная проверка для чистых IP
                                    if not url.startswith(("http://", "https://")):
                                        t_cell = "--"

                                    self.tree.set(item_id, "ping", p_cell)
                                    self.tree.set(item_id, "time", t_cell)
                                else:
                                    break
                            else:
                                break
                        except Exception:
                            break

                        # Снижаем нагрузку на GUI с 50мс до 100мс (глаз разницу не заметит, а лаги уйдут)
                        await asyncio.sleep(0.1)

                t_task = asyncio.create_task(anim())
                now_ts = time.time()

                try:
                    if url.startswith(("http://", "https://")):
                        # 1. Быстрый замер сетевой задержки (TCP-пинг до порта)
                        # Используем функцию из Шага 1 (убедитесь, что smart_tcp_ping объявлена в коде)
                        ping_success, icmp_ping, _, _ = await self.loop.run_in_executor(None, win32_ping, url)
                        self.current_p_txt = f"{icmp_ping:.2f} мс" if ping_success else "Не отвечает"
                        self.ping_done = True  # Фиксируем текст пинга, переключаем анимацию на HTTP

                        # 2. Выполняем HTTP-запрос
                        def do_http_request():
                            try:
                                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req, timeout=4.0) as response:
                                    return response.getcode(), None
                            except urllib.error.HTTPError as he:
                                return he.code, None
                            except:
                                return None, None

                        sc, _ = await self.loop.run_in_executor(None, do_http_request)

                        self.http_done = True
                        self.stop_anim = True
                        await t_task

                        fp_http = (time.perf_counter() - st_t) * 1000
                        t_txt = f"{fp_http:.1f} мс"

                        if sc and 200 <= sc < 400:
                            self.set_row_data(url, f"Доступен (Код: {sc})", self.current_p_txt, t_txt, "ok")
                            site_history[url].append((now_ts, icmp_ping if ping_success else fp_http, "OK", ""))
                        elif sc:
                            msg = f"Код ответа: {sc}"
                            self.set_row_data(url, msg, self.current_p_txt, t_txt, "warn")
                            site_history[url].append((now_ts, icmp_ping if ping_success else fp_http, "WARN", msg))
                        else:
                            raise Exception("Не удалось получить код ответа")
                    else:
                        # Логика для чистых IP адресов
                        self.current_t_txt = "--"
                        self.ping_done = True

                        success, ping_val, status_msg, desc_msg = await self.loop.run_in_executor(None, win32_ping,
                                                                                                  url)

                        self.http_done = True
                        self.stop_anim = True
                        await t_task

                        if success:
                            p_txt = f"{ping_val:.2f} мс"
                            self.set_row_data(url, "Узел доступен", p_txt, "--", "ok")
                            site_history[url].append((now_ts, ping_val, "OK", desc_msg))
                        else:
                            tag = "warn" if "Таймаут" in status_msg else "crit"
                            p_txt = "TIMEOUT" if tag == "warn" else "CRASH"
                            self.set_row_data(url, status_msg, p_txt, "--", tag)
                            site_history[url].append((now_ts, None, status_msg, desc_msg))

                except urllib.error.HTTPError as e:
                    self.http_done = True
                    self.stop_anim = True
                    await t_task

                    fp_http = (time.perf_counter() - st_t) * 1000
                    ping_success, icmp_ping, _, _ = await self.loop.run_in_executor(None, win32_ping, url)

                    p_txt = f"{icmp_ping:.2f} мс" if ping_success else "Не отвечает"
                    t_txt = f"{fp_http:.1f} мс"
                    expl = HTTP_EXPLANATIONS.get(e.code, f"Ошибка {e.code}: Нестандартный код ответа.")
                    self.set_row_data(url, f"Ошибка сервера (Код: {e.code})", p_txt, t_txt, "warn")
                    site_history[url].append((now_ts, icmp_ping if ping_success else fp_http, f"HTTP {e.code}", expl))
                except urllib.error.URLError as e:
                    self.http_done = True
                    self.stop_anim = True
                    await t_task

                    r = e.reason
                    msg, dt = "Сбой сети", str(r)
                    if isinstance(r, socket.gaierror):
                        msg, dt = "Ошибка DNS", "DNS не разрешен. Проверьте сеть."
                    elif isinstance(r, TimeoutError) or "timed out" in str(r).lower():
                        msg, dt = "Таймаут хоста", "Превышено время ожидания."
                    elif isinstance(r, ssl.SSLError):
                        msg, dt = "Ошибка SSL", "Сертификат просрочен или невалиден."

                    self.set_row_data(url, msg, "CRASH", "FAIL", "crit")
                    site_history[url].append((now_ts, None, msg, dt))
                except Exception as e:
                    self.http_done = True
                    self.stop_anim = True
                    await t_task
                    self.set_row_data(url, f"Крит: {type(e).__name__}", "FAIL", "FAIL", "crit")
                    site_history[url].append((now_ts, None, "CRITICAL", str(e)))

                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    def set_row_data(self, url, s_txt, p_txt, t_txt, tag):
        if url in self.row_map: self.tree.item(self.row_map[url], values=(url, s_txt, p_txt, t_txt), tags=(tag,))

if __name__ == "__main__":
    # Безопасный фоновый поток сбора сетевого окружения без фризов GUI
    threading.Thread(target=fetch_wmi_and_network_loop, daemon=True).start()
    
    root = tk.Tk()
    nl = asyncio.new_event_loop()
    threading.Thread(target=lambda: (asyncio.set_event_loop(nl), nl.run_forever()), daemon=True).start()
    app = DynamicPingApp(root, nl)
    root.mainloop()

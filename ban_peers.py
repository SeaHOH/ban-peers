#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""\
Checking & banning BitTorrent leech peers via Web API, working for uTorrent.
"""
__app_name__ = 'Ban-Peers'
__version__ = '0.1.9'
__author__ = 'SeaHOH<seahoh@gmail.com>'
__license__ = 'MIT'
__copyright__ = '2020 SeaHOH'
__py_min__ = '3.6'
__py_max__ = '3.9'
__webpage__ = 'https://github.com/SeaHOH/ban-peers'


import re
import os
import sys
import json
import time
import locale
import base64
import logging
import collections
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import OpenerDirector, Request
from socket import inet_pton, socket, AF_INET, AF_INET6
from shutil import get_terminal_size

from typing import *
from http.client import HTTPResponse

ParamValue = Union[int, str]
Params = TypeVar('Params', Mapping[str, ParamValue], Iterable[Tuple[str, ParamValue]])


if sys.version_info < (3, 7):
    _default_dict = collections.OrderedDict
else:
    _default_dict = dict
_linesep = os.linesep.replace('\r\n', '\n').encode()
_default_columns = 80
_max_columns = get_terminal_size().columns
if _max_columns < _default_columns and (
        os.name == 'nt' and os.system(f'mode con: cols={_default_columns}') == 0 or
        os.name != 'nt' and os.system(f'stty columns {_default_columns}') == 0):
    _max_columns = _default_columns
_max_columns -= 1
_10m = 1024 * 1024 * 10
_100m = _10m * 10

TOKEN = re.compile('<div id=.token.[^>]*>([^<]+)</div>')
LEECHER_XUNLEI = re.compile('^(?:xl|xun|sd|(?:unknown.+?/)?7\.)', re.I)
# DanDan, DLBT, Vagaa, Xfplay, Soda
LEECHER_PLAYER = re.compile('^(?:dan|dl|vag|xf|sod)', re.I)
# Unknown FW/6.8.5.3 -> FrostWire/6.8.5  see github.com/frostwire/frostwire#921
LEECHER_FAKE = re.compile('^(?:unknown )?(?:fw|frostwire)/\d\.\d\.\d\.\d', re.I)
# QQ, Baidu, TuoTu, FlashGet
LEECHER_OTHER = re.compile('^(?:q[qd]|bn|tuo|flashg)', re.I)


try:
    import msvcrt

    def get_keyhit() -> Optional[bytes]:
        if msvcrt.kbhit():
            return msvcrt.getch()

except ImportError:
    import select

    def get_keyhit() -> Optional[bytes]:
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.buffer.read(1)


def is_ip(ip:Any) -> bool:
    try:
        if ':' in ip:
            inet_pton(AF_INET6, ip.strip('[]'))  # Python bug?
        elif '.' in ip:
            inet_pton(AF_INET, ip)
        else:
            return False
    except:
        return False
    return True


def make_size_human(n:Union[int, float]) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if unit != 'GB' and n >= 1024:
            n /= 1024.0
        else:
            break
    return ' '.join(['{:.3f}'.format(n).rstrip('0').rstrip('.')[:7], unit])


def limit_dict_lenght(dict:Dict, lenght:int) -> None:
    while len(dict) > lenght:
        del dict[next(iter(dict))]


class List2Attr:
    # https://github.com/bittorrent/webui/blob/master/constants.js

    class TORRENT:
        HASH = 0
        STATUS = 1
        NAME = 2
        SIZE = 3
        PROGRESS = 4
        DOWNLOADED = 5
        UPLOADED = 6
        RATIO = 7
        UPSPEED = 8
        DOWNSPEED = 9
        ETA = 10
        LABEL = 11
        PEERS_CONNECTED = 12
        PEERS_SWARM = 13
        SEEDS_CONNECTED = 14
        SEEDS_SWARM = 15
        AVAILABILITY = 16
        QUEUE_POSITION = 17
        REMAINING = 18
        DOWNLOAD_URL = 19
        RSS_FEED_URL = 20
        STATUS_MESSAGE = 21
        STREAM_ID = 22
        DATE_ADDED = 23
        DATE_COMPLETED = 24
        APP_UPDATE_URL = 25
        SAVE_PATH = 26

    class FILE:
        NAME = 0
        SIZE = 1
        DOWNLOADED = 2
        PRIORITY = 3
        FIRST_PIECE = 4
        NUM_PIECES = 5
        STREAMABLE = 6
        ENCODED_RATE = 7
        DURATION = 8
        WIDTH = 9
        HEIGHT = 10
        STREAM_ETA = 11
        STREAMABILITY = 12

    class PEER:
        COUNTRY = 0
        IP = 1
        REVDNS = 2
        UTP = 3
        PORT = 4
        CLIENT = 5
        FLAGS = 6
        PROGRESS = 7
        DOWNSPEED = 8
        UPSPEED = 9
        REQS_OUT = 10
        REQS_IN = 11
        WAITED = 12
        UPLOADED = 13
        DOWNLOADED = 14
        HASHERR = 15
        PEERDL = 16
        MAXUP = 17
        MAXDOWN = 18
        QUEUED = 19
        INACTIVE = 20
        RELEVANCE = 21

    def __init__(self, list:List[Union[int, str]], type:str) -> None:
        object.__setattr__(self, '_list', list)
        object.__setattr__(self, '_type', self.__class__.__dict__[type.upper()])

    def __getattr__(self, name:str) -> Union[int, float, str]:
        value = self._list[self._type.__dict__[name.upper()]]
        if name == 'ip' and ':' in value:
            return f'[{value}]'
        elif name == 'client' and value[:1] == '-':
            return value.split('-')[1]
        elif name == 'availability':
            return value / 65536
        return value

    def __setattr__(self, name:str, value:Union[int, str]) -> None:
        if name == 'ip' and value[:1] == '[':
            value = value[1:-1]
        elif name == 'availability':
            value = int(value * 65536)
        self._list[self._type.__dict__[name.upper()]] = value


class UTorrentWebAPI:

    dict: ClassVar[Type[Dict]] = _default_dict

    def __init__(self,
                ipfilter:Optional[str], host:str='127.0.0.1', port:int=8080,
                username:Optional[str]='', password:Optional[str]='',
                expire:int=3600*12, log_header_fmt:str='%H:%M:%S',
                xunlei_reprieve:bool=True, check_fake_progress:bool=True,
                check_serious_leech:bool=True, check_private:bool=False) -> None:
        while not ipfilter:
            ipfilter = input(LANG_INPUT_IPFILTER)
        if os.path.isdir(ipfilter):
            ipfilter = os.path.join(ipfilter, 'ipfilter.dat')
        try:
            socket().connect((host, port))
        except:
            raise ValueError(f'{LANG_CONNECTION_REFUSED} {host}:{port}')
        self.file_ipfilter = ipfilter
        self._url_root = f'http://{host}:{port}/gui/'
        self._req = Request(self._url_root)
        self.set_authorization(username, password)
        self.expire = expire
        self.xunlei_reprieve = xunlei_reprieve
        self.check_fake_progress = check_fake_progress
        self.check_serious_leech = check_serious_leech
        self.check_private = check_private
        self.log_header_fmt = log_header_fmt
        self._params_list = {'list': 1, 'cid': 0, 'getmsg': 1}
        self._seeds_private = {}
        self._statistics = collections.defaultdict(dict)
        self._statistics_progress = collections.defaultdict(dict)
        self._statistics_uploaded = collections.defaultdict(dict)
        self._statistics_str = ''
        self._need_save = False
        self.running = False
        self.init_ipfilter()
        self.init_opener()
        self.get_token()

    def init_ipfilter(self) -> None:
        self.log_ip = self.dict()
        self.ipfilter = ipfilter = self.dict()
        ipfilter_range = []
        ct = int(time.time())
        ct_bytes = str(ct).encode()
        for line in (os.path.exists(self.file_ipfilter) and
                     open(self.file_ipfilter, 'rb') or ()):
            ip, _, rest = [p.strip() for p in line.partition(b'#')]
            if b'-' in ip:
                # store IP range as is
                ipfilter_range.append(line.replace(b'\r\n', _linesep))
            else:
                ip_str = ip.decode()
                if is_ip(ip_str):
                    reason, _, timestamp = [p.strip() for p in rest.partition(b';')]
                    try:
                        ipfilter[ip_str] = ip, reason, timestamp, int(timestamp)
                    except ValueError:
                        ipfilter[ip_str] = ip, reason, ct_bytes, ct
        if ipfilter_range:
            ipfilter_range.append(_linesep)
        self.ipfilter_range = b''.join(ipfilter_range)

    def save_ipfilter(self) -> None:
        buffering = sum((
            sum((len(ip), len(reason), len(timestamp), 8))
            for ip, reason, timestamp, _ in self.ipfilter.values()
        ), len(self.ipfilter_range) + 1)
        with open(self.file_ipfilter, 'wb', buffering=buffering) as f:
            f.write(self.ipfilter_range)
            for ip, reason, timestamp, _ in self.ipfilter.values():
                f.write(ip)
                f.write(b'  # ')
                f.write(reason)
                f.write(b' ; ')
                f.write(timestamp)
                f.write(_linesep)

    def init_opener(self) -> None:
        self.opener = opener = OpenerDirector()
        for handler_name in ['HTTPCookieProcessor', 'HTTPHandler',
                             'HTTPDefaultErrorHandler', 'HTTPRedirectHandler']:
            handler = getattr(urllib.request, handler_name)()
            if handler_name == 'HTTPCookieProcessor':
                self.cookiejar = handler.cookiejar
            opener.add_handler(handler)

    def set_authorization(self, username:Optional[str], password:Optional[str]) -> None:
        if username or password:
            self._req.add_header('Authorization',
                                'Basic ' + base64.b64encode(
                                f'{username or ""}:{password or ""}'.encode()
                                ).decode())


    def request(self, path:str='', params:Params=None) -> Union[HTTPResponse, NoReturn]:
        if params:
            params_str = urlencode({
                'token': self.token,
                **params,
                't': int(time.time())
            })
            url = f'{self._url_root}{path}?{params_str}'
        else:
            url = f'{self._url_root}{path}'
        if self._req.full_url != url:
            self._req.full_url = url
        response = self.opener.open(self._req)
        while response.code == 401:
            self.set_authorization(input(LANG_INPUT_USERNAME),
                                   input(LANG_INPUT_PASSWORD))
            response = self.opener.open(self._req)
        if response.code == 400 and path != 'token.html':
            self.get_token()
        if response.code != 200:
           raise HTTPError(url, response.code, response.msg, response.headers, response)
        return response

    def get_token(self) -> None:
        self._req.remove_header('Cookie')
        self.cookiejar.clear()
        html = self.request(path='token.html').read().decode()
        self.token = TOKEN.search(html).group(1)

    def is_private(self, hash:str) -> bool:
        try:
            return self._seeds_private[hash]
        except KeyError:
            response = self.request(params={
                'action': 'getprops',
                'hash': hash
            })
            self._seeds_private[hash] = private = \
                    json.load(response)['props'][0]['pex'] == -1
            return private

    def get_torrents(self) -> Iterable[List2Attr]:
        torrents = json.load(self.request(params=self._params_list))
        if 'torrentc' in torrents:
            self._params_list['cid'] = torrents['torrentc']
        for hash in torrents.get('torrentm', []):
            self._seeds_private.pop(hash, None)
            self._statistics_uploaded.pop(hash, None)
        for torrent in torrents.get('torrents') or torrents.get('torrentp', []):
            torrent = List2Attr(torrent, 'torrent')
            if torrent.peers_connected and (self.check_private or
                     not self.is_private(torrent.hash)):
                yield torrent

    def get_files(self, hash:str) -> Iterable[List2Attr]:
        response = self.request(params={
            'action': 'getfiles',
            'hash': hash
        })
        return (List2Attr(peer, 'file') for peer in json.load(response)['files'][1])

    def get_peers(self, hash:str) -> Iterable[List2Attr]:
        response = self.request(params={
            'action': 'getpeers',
            'hash': hash
        })
        return (List2Attr(peer, 'peer') for peer in json.load(response)['peers'][1])

    def set_setting(self, s:str, v:Union[int, str, bool]) -> None:
        self.request(params={
            'action': 'setsetting',
            's': s,
            'v': isinstance(v, bool) and int(v) or v
        })
        if s != 'ipfilter.enable':
            print(f'{self.log_header}{LANG_SET_SETTING} {s!r} {LANG_TO} {v}')

    def ban_peers(self) -> None:
        if not self._need_save:
            return
        self.collect_statistics()
        ct = int(time.time())
        expire = ct - self.expire
        expire_interim = ct - 3600
        expire_ips = list(ip
            for ip, (_, reason, _, timestamp) in self.ipfilter.items()
            if timestamp < expire or timestamp < expire_interim and \
                reason.startswith((b'Seeding', b'Suspected'))
        )
        for ip in expire_ips:
            del self.ipfilter[ip]
        self.save_ipfilter()
        self._need_save = False
        self.set_setting('ipfilter.enable', True)

    def ban_push(self, hash:str, peer:List2Attr, reason:str='') -> None:
        ct = int(time.time())
        ip = peer.ip
        self._statistics[ip][hash] = peer.downloaded, peer.uploaded
        limit_dict_lenght(self._statistics, 1024)
        reason = f'{reason} [{peer.client}]'
        self.log_ip.pop(ip, None)
        self.ipfilter.pop(ip, None)
        self.ipfilter[ip] = ip.encode(), reason.encode(), str(ct).encode(), ct
        self._need_save = True
        print(f'{self.log_header}{LANG_BANNED} '
              f'{ip}:{peer.port}@{peer.country}：{reason}')

    def check_peers(self) -> None:
        def log(msg):
            ip = peer.ip
            if ip in self.log_ip or ip in self.ipfilter:
                return
            print(f'{self.log_header}[{hash}][{torrent.name}]'
                  f'{LANG_FOUND}{msg}: {peer.client}@{ip_port}')
            self.log_ip[ip] = True
            limit_dict_lenght(self.log_ip, 32)

        reasons = []
        for torrent in self.get_torrents():
            size_millesimal = int(torrent.size / 1000)
            seeding = torrent.progress >= 1000  # uTorrent bug?
            hash = torrent.hash
            if self.check_serious_leech:
                files = list(self.get_files(hash))
                size_tenth = int(sum(file.size for file in files
                                     if file.priority) / 10)
                size_last_downloaded = torrent.downloaded - sum(
                                       file.downloaded
                                       for file in files)
            for peer in self.get_peers(hash):
                ip_port = f'{peer.ip}:{peer.port}'
                if not self.check_fake_progress:
                    pass
                elif peer.progress:
                    self._statistics_progress.pop(ip_port, None)
                elif (seeding or peer.downloaded == 0):
                    ct = time.monotonic()
                    try:
                        last_uploaded, t = self._statistics_progress[ip_port][hash]
                    except KeyError:
                        self._statistics_progress[ip_port][hash] = \
                                last_uploaded, t = peer.uploaded, None
                    if peer.inactive > 10:
                        self._statistics_progress[ip_port][hash] = last_uploaded, None
                    elif peer.uploaded - last_uploaded > size_millesimal * 1.5:
                        if t is None:
                            self._statistics_progress[ip_port][hash] = last_uploaded, ct
                        elif ct - t > 60:  # did not recovered within one minute
                            log(LANG_FACK_PROGRESS)
                            if seeding:
                                reasons.append('Seeding')
                            reasons.append('Progress')
                limit_dict_lenght(self._statistics_progress, 1024)
                if peer.port >= 65000 and \
                        peer.country == 'CN' and \
                        'Transmission' in peer.client and \
                        peer.downloaded == peer.relevance == 0:
                    log(LANG_OFFLINE_SERVER)
                    if reasons and reasons[0] == 'Seeding':
                        del reasons[0]
                    reasons.append('Offline')
                elif LEECHER_XUNLEI.search(peer.client):
                    log(LANG_XUNLEI)
                    if not self.xunlei_reprieve or \
                            peer.port in [12345, 15000] or not seeding and (
                            peer.downloaded == peer.relevance == 0 or
                            peer.uploaded > min(size_millesimal, _10m) and (
                            peer.downloaded * 5 < peer.uploaded or
                            peer.downloaded * 10 / size_millesimal < peer.relevance)):
                        if reasons and reasons[0] == 'Seeding':
                            del reasons[0]
                        reasons.append('XunLei')
                    elif seeding:
                        reasons.append('Seeding')
                        reasons.append('XunLei')
                elif LEECHER_PLAYER.search(peer.client):
                    log(LANG_PLAYER)
                    if seeding:
                        reasons.append('Seeding')
                        reasons.append('Player')
                    elif peer.downloaded == peer.relevance == 0:
                        reasons.append('Player')
                elif peer.client.startswith('[FAKE]') or \
                        LEECHER_FAKE.search(peer.client):
                    log(LANG_FACK_CLIENT)
                    if seeding:
                        reasons.append('Seeding')
                        reasons.append('Fake')
                    elif peer.downloaded == 0 and \
                            peer.uploaded > min(size_millesimal, _10m):
                        reasons.append('Fake')
                elif LEECHER_OTHER.search(peer.client):
                    log(LANG_LEECHER_CLIENT)
                    if seeding:
                        reasons.append('Seeding')
                        reasons.append('Leecher')
                    elif peer.uploaded > min(size_millesimal, _10m) and (
                            peer.downloaded * 5 < peer.uploaded or
                            peer.downloaded * 10 / size_millesimal < peer.relevance):
                        reasons.append('Leecher')
                if not self.check_serious_leech:
                    pass
                elif seeding:
                    self._statistics_uploaded.pop(hash, None)
                elif reasons or peer.progress >= 1000:
                    if size_last_downloaded > _10m:
                        self._statistics_uploaded[hash].pop(ip_port, None)
                else:
                    if size_last_downloaded > _10m:
                        try:
                            _last_downloaded, _downloaded, _uploaded = \
                                    self._statistics_uploaded[hash][ip_port]
                        except KeyError:
                            _last_downloaded = size_last_downloaded
                            _downloaded = peer.downloaded
                            _uploaded = peer.uploaded
                        if size_last_downloaded - _last_downloaded > _10m:
                            _downloaded = peer.downloaded
                            _uploaded = peer.uploaded
                        self._statistics_uploaded[hash][ip_port] = \
                                _last_downloaded, _downloaded, _uploaded
                        peer.downloaded -= _downloaded
                        peer.uploaded -= _uploaded
                    if ('U' in peer.flags and 'd' in peer.flags or
                            peer.downspeed < 1024 and peer.waited > 60) and \
                            peer.uploaded > min(size_tenth, _100m) and \
                            peer.downloaded * 10 < peer.uploaded and \
                            peer.downloaded * 10 / size_millesimal < peer.relevance:
                        log(LANG_LEECHER_SUSPECTED)
                        reasons.append('Suspected')
                        reasons.append('Leecher')
                        if size_last_downloaded > _10m:
                            self._statistics_uploaded[hash].pop(ip_port, None)
                            peer.downloaded += _downloaded
                            peer.uploaded += _uploaded
                if reasons:
                    if not seeding:
                        self._statistics_progress.pop(ip_port, None)
                    try:
                        self.ban_push(torrent.hash, peer, ' '.join(reasons))
                    finally:
                        reasons.clear()

    def collect_statistics(self) -> None:
        statistics = self._statistics
        if len(statistics) == 0:
            return
        hashes = sum((list(hash.items()) for hash in statistics.values()), [])
        hashes, downloaded, uploaded = zip(*((h, d, u) for h, (d, u) in hashes))
        self._statistics_str = (
            f'{LANG_STATISTICS}: {len(statistics)} IPs, '
            f'{len(set(hashes))}/{len(hashes)} Torrents, '
            f'{LANG_DOWNLOADED}: {make_size_human(sum(downloaded))}, '
            f'{LANG_UPLOADED}: {make_size_human(sum(uploaded))}'
        )

    @property
    def statistics(self) -> str:
        return self._statistics_str[:_max_columns]

    @property
    def log_header(self) -> str:
        return f'{CLL}{time.strftime(self.log_header_fmt, time.localtime())} '

    def run(self, show_operations: bool=True) -> None:
        def log(msg):
            print(f'{self.log_header}uTorrent {LANG_A_NAME}{msg}{LANG_RUNNING}')

        if self.running:
            return
        self.running = True
        pause = False
        ss = False
        self.set_setting('bt.use_rangeblock', False)
        log(LANG_START)
        while True:
            if not self.running:
                break
            if not pause:
                err_cr = None
                try:
                    self.check_peers()
                    self.ban_peers()
                except URLError as e:
                    if isinstance(e.reason, ConnectionRefusedError):
                        print(f'{self.log_header}{LANG_CONNECTION_REFUSED} '
                              f'WebUI@{self._url_root}', end='\r')
                        time.sleep(10)
                        err_cr = True
                    else:
                        logging.exception(f'{self.log_header}{LANG_ERROR_OCCURRED}: {e}')
                except HTTPError as e:
                    print(f'{self.log_header}{LANG_ERROR_OCCURRED}: '
                          f'{e}, {e.filename}')
                except Exception as e:
                    logging.exception(f'{self.log_header}{LANG_ERROR_OCCURRED}: {e}')
            for _ in range(5):
                if show_operations:
                    print(CLL, end='')
                    msgs = ss and self.statistics or LANG_OPERATES_TIP,
                    if err_cr:
                        msgs = LANG_DISCONNECTED, *msgs
                    print(*msgs, end='\r')
                    ss = not ss
                    k = get_keyhit()
                    if k is None:
                        pass
                    elif k in b'qQ':
                        log(LANG_QUIT)
                        sys.exit()
                    elif k in b'sS':
                        self.running = False
                        if __name__ == '__main__' or sys.argv[0].endswith(__name__):
                            log(LANG_QUIT)
                        else:
                            log(LANG_STOP)
                    elif k in b'rR':
                        self.init_ipfilter()
                        self.get_token()
                        self.running = True
                        pause = False
                        log(LANG_RESTART)
                    elif k in b'pP':
                        pause = not pause
                        if pause:
                            log(LANG_PAUSE)
                        else:
                            log(LANG_PROCEED)
                time.sleep(2)


CLL = f'\r{" " * _max_columns}\r'
if locale.getdefaultlocale()[0] == 'zh_CN':
    LANG_INPUT_IPFILTER = '请输入 uTorrent 配置文件夹路径，或者 ipfilter 文件路径:\n'
    LANG_INPUT_USERNAME = '请输入 WebUI 用户名: '
    LANG_INPUT_PASSWORD = '请输入 WebUI 密码: '
    LANG_WELCOME = '欢迎使用'
    LANG_START = '开始'
    LANG_STOP = '停止'
    LANG_QUIT = '退出'
    LANG_RESTART = '重新开始'
    LANG_PAUSE = '暂停'
    LANG_PROCEED = '恢复'
    LANG_RUNNING = '运行'
    LANG_A_NAME = '自动屏蔽脚本'
    LANG_SET_SETTING = '设定 uTorrent 配置'
    LANG_TO = '到'
    LANG_ERROR_OCCURRED = '发生错误'
    LANG_CONNECTION_REFUSED = '无法连接'
    LANG_DISCONNECTED = '已断开'
    LANG_BANNED = '已屏蔽'
    LANG_FOUND = '发现'
    LANG_FACK_PROGRESS = '汇报虚假进度'
    LANG_XUNLEI = '迅雷'
    LANG_PLAYER = '播放器'
    LANG_FACK_CLIENT = '假冒客户端'
    LANG_OFFLINE_SERVER = '离线下载服务器'
    LANG_LEECHER_CLIENT = '吸血客户端'
    LANG_LEECHER_SUSPECTED = '高度疑似吸血'
    LANG_STATISTICS = '统计'
    LANG_DOWNLOADED = '已下载'
    LANG_UPLOADED = '已上传'
    LANG_OPERATES_TIP = ('请选择你要执行的操作: '
                         '(Q)退出，(S)停止，(R)重新开始，(P)暂停/恢复')
    LANG_HELP_USAGE = '用法'
    LANG_HELP_POSITIONAL = '位置参数'
    LANG_HELP_OPTIONAL = '可选参数'
    LANG_HELP_HELP = '显示此帮助信息并退出'
    LANG_HELP_VERSION = '显示版本信息并退出'
    LANG_HELP_IPFILTER_META = 'IP屏蔽配置路径'
    LANG_HELP_IPFILTER = ('ipfilter 目录或文件路径，留空将等待输入。'
                          '重要提示: 必须是 uTorrent 配置使用的路径!')
    LANG_HELP_HOST_META = 'IP|域名'
    LANG_HELP_HOST = '网页界面的主机，默认'
    LANG_HELP_PORT_META = '端口'
    LANG_HELP_PORT = '网页界面的端口，默认'
    LANG_HELP_AUTHORIZATION_META = '用户名:密码'
    LANG_HELP_AUTHORIZATION = '网页界面的授权，如果需要将等待输入'
    LANG_HELP_EXPIRE_META = '小时'
    LANG_HELP_EXPIRE = '屏蔽对端的过期时间，默认'
    LANG_HELP_HEADER_META = '格式'
    LANG_HELP_HEADER = '日志头格式，默认'
    LANG_HELP_RESOLVE_COUNTRY = '启动时，设置 uTorrent 解析对端国家代码'
    LANG_HELP_NO_XUNLEI_REPRIEVE = '直接屏蔽迅雷，不进行更多的检查'
    LANG_HELP_NO_FAKE_PROGRESS_CHECK = '不进行虚假进度检查'
    LANG_HELP_NO_SERIOUS_LEECH_CHECK = '不进行严重吸血检查'
    LANG_HELP_PRIVATE_CHECK = '启用对私人种子的检查'
    __doc__ = '通过网页 API 检查并屏蔽 BitTorrent 吸血对端，工作于 uTorrent。'
else:
    LANG_INPUT_IPFILTER = 'Please input uTorrent settings folder path or ipfilter file path:\n'
    LANG_INPUT_USERNAME = 'Please input WebUI username: '
    LANG_INPUT_PASSWORD = 'Please input WebUI password: '
    LANG_WELCOME = 'Welcome using'
    LANG_START = 'start'
    LANG_STOP = 'stop'
    LANG_QUIT = 'quit'
    LANG_RESTART = 'restart'
    LANG_PAUSE = 'pause'
    LANG_PROCEED = 'proceed'
    LANG_RUNNING = ' running'
    LANG_A_NAME = 'auto-banning script '
    LANG_SET_SETTING = 'Set uTorrent setting'
    LANG_TO = 'to'
    LANG_ERROR_OCCURRED = 'error occurred'
    LANG_CONNECTION_REFUSED = 'unable to connect'
    LANG_DISCONNECTED = 'DISCONNECTED'
    LANG_BANNED = 'banned'
    LANG_FOUND = ' found '
    LANG_FACK_PROGRESS = 'report fack progress'
    LANG_XUNLEI = 'XunLei'
    LANG_PLAYER = 'player'
    LANG_FACK_CLIENT = 'fack client'
    LANG_OFFLINE_SERVER = 'offline download server'
    LANG_LEECHER_CLIENT = 'leecher client'
    LANG_LEECHER_SUSPECTED = 'highly suspected of leecher'
    LANG_STATISTICS = 'Statis'
    LANG_DOWNLOADED = 'D'
    LANG_UPLOADED = 'U'
    LANG_OPERATES_TIP = ('Choose your operation: '
                         '(Q)uit, (S)top, (R)estart, (P)ause/Proceed')
    LANG_HELP_USAGE = 'Usage'
    LANG_HELP_POSITIONAL = 'Positional Arguments'
    LANG_HELP_OPTIONAL = 'Optional Arguments'
    LANG_HELP_HELP = 'Show this help message and exit'
    LANG_HELP_VERSION = 'Show version and exit'
    LANG_HELP_IPFILTER_META = 'IPFILTER-PATH'
    LANG_HELP_IPFILTER = ('Path of ipfilter dir/file, wait input if empty. '
                          'IMPORTANT NOTICE: must be the uTorrent settings path!')
    LANG_HELP_HOST_META = 'IP|DOMAIN'
    LANG_HELP_HOST = 'WebUI host, default'
    LANG_HELP_PORT_META = 'PORT'
    LANG_HELP_PORT = 'WebUI port, default'
    LANG_HELP_AUTHORIZATION_META = 'USERNAME:PASSWORD'
    LANG_HELP_AUTHORIZATION = 'WebUI authorization, wait input if required'
    LANG_HELP_EXPIRE_META = 'HOURS'
    LANG_HELP_EXPIRE = 'Ban expire time for peers, default'
    LANG_HELP_HEADER_META = 'FORMAT'
    LANG_HELP_HEADER = 'Format of log header, default'
    LANG_HELP_RESOLVE_COUNTRY = 'Set uTorrent to resolved peer\'s country code at start-up'
    LANG_HELP_NO_XUNLEI_REPRIEVE = 'Banned XunLei directly, no more checking'
    LANG_HELP_NO_FAKE_PROGRESS_CHECK = 'Don\'t checking fake progress'
    LANG_HELP_NO_SERIOUS_LEECH_CHECK = 'Don\'t checking serious leech'
    LANG_HELP_PRIVATE_CHECK = 'Enable checking for private seeds'

__doc__ = f'''\
{__app_name__} {__version__}

{__doc__}

{__license__} License Copyright (c) {__copyright__}

Python Version: {__py_min__} - {__py_max__}

Web Page: {__webpage__}
'''


def main() -> None:
    import inspect
    import argparse

    kwargs = {
        k: v.default
        for k, v in inspect.signature(UTorrentWebAPI.__init__).parameters.items()
        if v.default is not v.empty
    }
    indent = 8

    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser._get_formatter = lambda: argparse.HelpFormatter(parser.prog, indent)
    parser._positionals.title = LANG_HELP_POSITIONAL
    parser._optionals.title = LANG_HELP_OPTIONAL
    parser.add_argument('ipfilter', nargs='?', metavar=LANG_HELP_IPFILTER_META,
                        help=LANG_HELP_IPFILTER)
    parser.add_argument('-H', '--host', type=str, metavar=LANG_HELP_HOST_META,
                        help=f'{LANG_HELP_HOST} {kwargs["host"]}')
    parser.add_argument('-p', '--port', type=int, metavar=LANG_HELP_PORT_META,
                        help=f'{LANG_HELP_PORT} {kwargs["port"]}')
    parser.add_argument('-a', '--authorization', type=str, default='',
                        metavar=LANG_HELP_AUTHORIZATION_META,
                        help=LANG_HELP_AUTHORIZATION)
    parser.add_argument('-e', '--expire', type=int, metavar=LANG_HELP_EXPIRE_META,
            help=f'{LANG_HELP_EXPIRE} {kwargs["expire"] // 3600} {LANG_HELP_EXPIRE_META}')
    parser.add_argument('-f', '--log-header', type=str, metavar=LANG_HELP_HEADER_META,
            help=f'{LANG_HELP_HEADER} {kwargs["log_header_fmt"]}'.replace("%", "%%"))
    parser.add_argument('-C', '--resolve-country', action='store_true',
                        help=LANG_HELP_RESOLVE_COUNTRY)
    parser.add_argument('-X', '--no-xunlei-reprieve', action='store_true',
                        help=LANG_HELP_NO_XUNLEI_REPRIEVE)
    parser.add_argument('-P', '--no-fake-progress-check', action='store_true',
                        help=LANG_HELP_NO_FAKE_PROGRESS_CHECK)
    parser.add_argument('-L', '--no-serious-leech-check', action='store_true',
                        help=LANG_HELP_NO_SERIOUS_LEECH_CHECK)
    parser.add_argument('-R', '--private-check', action='store_true',
                        help=LANG_HELP_PRIVATE_CHECK)
    parser.add_argument('-h', '--help', action='store_true',
                        help=LANG_HELP_HELP)
    parser.add_argument('-v', '--version', action='store_true',
                        help=LANG_HELP_VERSION)
    args = parser.parse_args()

    if args.version:
        print(f'{__app_name__} {__version__}')
        sys.exit()
    print(f'{LANG_WELCOME} {__app_name__} {__version__}')
    if args.help:
        print(f'\n{LANG_HELP_USAGE}:\n{" " * indent}{parser.format_help()[7:]}')
        sys.exit()

    if args.host:
        kwargs['host'] = args.host
    if args.port:
        kwargs['port'] = args.port
    if args.authorization.count(':') == 1:
        kwargs['username'], kwargs['password'] = args.authorization.split(':')
    if args.expire:
        kwargs['expire'] = args.expire * 3600
    if args.log_header:
        kwargs['log_header_fmt'] = args.log_header
    if args.no_xunlei_reprieve:
        kwargs['xunlei_reprieve'] = False
    if args.no_fake_progress_check:
        kwargs['check_fake_progress'] = False
    if args.no_serious_leech_check:
        kwargs['check_serious_leech'] = False
    if args.private_check:
        kwargs['check_private'] = True
    ut = UTorrentWebAPI(args.ipfilter, **kwargs)
    if args.resolve_country:
        ut.set_setting('peer.resolve_country', True)
        ut.set_setting('resolve_peerips', True)
    ut.run()


if __name__ == '__main__':
    main()

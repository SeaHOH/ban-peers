"""
Checking & banning BitTorrent leecher peers via Web API, working for uTorrent 3.
"""
__version__ = '0.1.3'
__author__ = 'SeaHOH<seahoh@gmail.com>'
__license__ = 'MIT'
__py_min__ = '3.6.0'
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
_max_columns = get_terminal_size().columns - 1
if _max_columns < 79 and \
        os.name == 'nt' and os.system('mode con: cols=80') == 0 or \
        os.name != 'nt' and os.system('stty columns 80') == 0:
    _max_columns = 79

TOKEN = re.compile('<div id=.token.[^>]*>([^<]+)</div>')
LEECHER_XUNLEI = re.compile('^(?:xl|xun|sd|(unknown.+?/)?7\.)', re.I)
# DanDan, DLBT, Vagaa, Xfplay, Soda
LEECHER_PLAYER = re.compile('^(?:dan|dl|vag|xf|sod)', re.I)
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
        self.list = list
        self.type = self.__class__.__dict__[type.upper()]

    def __getattr__(self, name:str) -> Union[int, float, str]:
        value = self.list[self.type.__dict__[name.upper()]]
        if name == 'ip' and ':' in value:
            return f'[{value}]'
        elif name == 'client' and value[:1] == '-':
            return value.split('-')[1]
        elif name == 'availability':
            return value / 65536
        return value


class UTorrentWebAPI:

    dict: ClassVar[Type[Dict]] = _default_dict

    def __init__(self, ipfilter:Optional[str], host:str='127.0.0.1', port:int=8080,
                       username:Optional[str]='', password:Optional[str]='',
                       expire:int=3600*12, log_header_fmt:str='%H:%M:%S') -> None:
        while not ipfilter:
            ipfilter = input(LANG_INPUT_IPFILTER)
        if os.path.isdir(ipfilter):
            ipfilter = os.path.join(ipfilter, 'ipfilter.dat')
        try:
            socket().connect((host, port))
        except:
            raise ValueError(f'{LANG_CONNECTION_REFUSED} {host}:{port}')
        self.file_ipfilter = ipfilter
        self.url_root = f'http://{host}:{port}/gui/'
        self.req = Request(self.url_root)
        self.set_authorization(username, password)
        self.expire = expire
        self.log_header_fmt = log_header_fmt
        self.params_list = {'list': 1, 'cid': 0, 'getmsg': 1}
        self._statistics = collections.defaultdict(dict)
        self._statistics_progress = collections.defaultdict(dict)
        self._statistics_str = ''
        self.need_save = False
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
        for line in open(self.file_ipfilter, 'rb'):
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
            self.req.add_header('Authorization',
                                'Basic ' + base64.b64encode(
                                f'{username or ""}:{password or ""}'.encode()
                                ).decode())


    def request(self, path:str='', params:Params=None) -> HTTPResponse:
        if params:
            params_str = urlencode({
                'token': self.token,
                **params,
                't': int(time.time())
            })
            url = f'{self.url_root}{path}?{params_str}'
        else:
            url = f'{self.url_root}{path}'
        if self.req.full_url != url:
            self.req.full_url = url
        response = self.opener.open(self.req)
        while response.code == 401:
            self.set_authorization(input(LANG_INPUT_USERNAME),
                                   input(LANG_INPUT_PASSWORD))
            response = self.opener.open(self.req)
        if response.code == 400 and path != 'token.html':
            self.get_token()
        if response.code != 200:
           raise HTTPError(url, response.code, response.msg, response.headers, response)
        return response

    def get_token(self) -> None:
        self.req.remove_header('Cookie')
        self.cookiejar.clear()
        html = self.request(path='token.html').read().decode()
        self.token = TOKEN.search(html).group(1)

    def get_torrents(self) -> Iterable[List2Attr]:
        torrents = json.load(self.request(params=self.params_list))
        if 'torrentc' in torrents:
            self.params_list['cid'] = torrents['torrentc']
        for torrent in torrents.get('torrents') or torrents.get('torrentp'):
            torrent = List2Attr(torrent, 'torrent')
            if torrent.peers_connected:
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

    def set_setting(self, s:str, v:ParamValue) -> None:
        self.request(params={
            'action': 'setsetting',
            's': s,
            'v': v
        })

    def ban_peers(self) -> None:
        if not self.need_save:
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
        self.need_save = False
        self.set_setting('ipfilter.enable', 1)

    def ban_push(self, hash:str, peer:List2Attr, reason:str='') -> None:
        ct = int(time.time())
        ip = peer.ip
        self._statistics[ip][hash] = peer.downloaded, peer.uploaded
        limit_dict_lenght(self._statistics, 1024)
        reason = f'{reason} [{peer.client}]'
        self.log_ip.pop(ip, None)
        self.ipfilter.pop(ip, None)
        self.ipfilter[ip] = ip.encode(), reason.encode(), str(ct).encode(), ct
        self.need_save = True
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
            hash = torrent.hash
            size_tenth = int(torrent.size / 10)
            size_millesimal = int(torrent.size / 1000)
            seeding = torrent.progress >= 1000  # uTorrent bug?
            size_last_downloaded = torrent.downloaded - sum(
                                   file.downloaded
                                   for file in self.get_files(hash)
                                   if file.priority)  # not accurate
            for peer in self.get_peers(hash):
                ip_port = f'{peer.ip}:{peer.port}'
                if peer.progress:
                    self._statistics_progress.pop(ip_port, None)
                elif (seeding or peer.downloaded == 0):
                    last_uploaded = self._statistics_progress[ip_port].get(hash)
                    if last_uploaded is None:
                        self._statistics_progress[ip_port][hash] = peer.uploaded
                    elif peer.uploaded - last_uploaded > size_millesimal * 1.5:
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
                    if 'Seeding' in reasons:
                        del reasons[0]
                    reasons.append('Offline')
                elif LEECHER_XUNLEI.search(peer.client):
                    log(LANG_XUNLEI)
                    if peer.port in [12345, 15000] or \
                            not seeding and \
                            peer.downloaded == peer.relevance == 0:
                        if 'Seeding' in reasons:
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
                elif peer.client.startswith('[FAKE]'):
                    log(LANG_FACK_CLIENT)
                    if seeding:
                        reasons.append('Seeding')
                        reasons.append('Fake')
                    elif peer.downloaded == 0 and \
                            peer.uploaded > min(size_millesimal, 10485760):
                        reasons.append('Fake')
                elif LEECHER_OTHER.search(peer.client):
                    log(LANG_LEECHER_CLIENT)
                    if seeding:
                        reasons.append('Seeding')
                        reasons.append('Leecher')
                    elif peer.uploaded > min(size_millesimal, 10485760) and \
                            peer.downloaded * 5 < peer.uploaded or \
                            peer.downloaded * 2 / size_millesimal < peer.relevance:
                        reasons.append('Leecher')
                if not seeding and not reasons and peer.progress < 1000 and \
                        ('U' in peer.flags and 'd' in peer.flags or
                        peer.downspeed < 1024 and peer.waited > 60) and \
                        peer.uploaded - size_last_downloaded > min(size_tenth, 104857600) and \
                        peer.downloaded * 10 < peer.uploaded - size_last_downloaded and \
                        peer.downloaded * 10 / size_millesimal < peer.relevance:
                    log(LANG_LEECHER_SUSPECTED)
                    reasons.append('Suspected')
                    reasons.append('Leecher')
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
                              f'WebUI@{self.url_root}', end='\r')
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
                        if __name__ == '__main__':
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
    LANG_START = '开始'
    LANG_STOP = '停止'
    LANG_QUIT = '退出'
    LANG_RESTART = '重新开始'
    LANG_PAUSE = '暂停'
    LANG_PROCEED = '恢复'
    LANG_RUNNING = '运行'
    LANG_A_NAME = '自动屏蔽脚本'
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
                         '(Q)退出, (S)停止, (R)重新开始, (P)暂停/恢复')
    LANG_HELP_USAGE = '用法'
    LANG_HELP_POSITIONAL = '位置参数'
    LANG_HELP_OPTIONAL = '可选参数'
    LANG_HELP_HELP = '显示此帮助信息并退出'
    LANG_IPFILTER_META = 'IP屏蔽配置路径'
    LANG_IPFILTER_HELP = ('ipfilter 目录或文件路径, 留空将等待输入。'
                          '重要提示: 必须是 uTorrent 配置使用的路径!')
    LANG_HOST_META = 'IP|域名'
    LANG_HOST_HELP = '网页界面的主机, 默认 '
    LANG_PORT_META = '端口'
    LANG_PORT_HELP = '网页界面的端口, 默认 '
    LANG_AUTHORIZATION_META = '用户名:密码'
    LANG_AUTHORIZATION_HELP = '网页界面的授权, 如果需要将等待输入'
    LANG_EXPIRE_META = '小时'
    LANG_EXPIRE_HELP = '屏蔽对端的过期时间, 默认 '
    LANG_HEADER_META = '格式'
    LANG_HEADER_HELP = '日志头格式, 默认 '
    __doc__ = '通过网页 API 检查并屏蔽 BitTorrent 吸血对端, 工作于 uTorrent 3。'
else:
    LANG_INPUT_IPFILTER = 'Please input uTorrent setting folder path or ipfilter file path:\n'
    LANG_INPUT_USERNAME = 'Please input WebUI username: '
    LANG_INPUT_PASSWORD = 'Please input WebUI password: '
    LANG_START = 'start'
    LANG_STOP = 'stop'
    LANG_QUIT = 'quit'
    LANG_RESTART = 'restart'
    LANG_PAUSE = 'pause'
    LANG_PROCEED = 'proceed'
    LANG_RUNNING = ' running'
    LANG_A_NAME = 'auto-banning script '
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
    LANG_IPFILTER_META = 'IPFILTER-PATH'
    LANG_IPFILTER_HELP = ('Path of ipfilter dir/file, wait input if empty. '
                          'IMPORTANT NOTICE: must be the uTorrent setting path!')
    LANG_HOST_META = 'IP|DOMAIN'
    LANG_HOST_HELP = 'WebUI host, default '
    LANG_PORT_META = 'PORT'
    LANG_PORT_HELP = 'WebUI port, default '
    LANG_AUTHORIZATION_META = 'USERNAME:PASSWORD'
    LANG_AUTHORIZATION_HELP = 'WebUI authorization, wait input if required'
    LANG_EXPIRE_META = 'HOURS'
    LANG_EXPIRE_HELP = 'Ban expire time for peers, default '
    LANG_HEADER_META = 'FORMAT'
    LANG_HEADER_HELP = 'Format of log header, default '


def main() -> None:
    import inspect
    import argparse

    kwargs = {
        k: v.default
        for k, v in inspect.signature(UTorrentWebAPI.__init__).parameters.items()
        if v.default is not v.empty
    }

    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser._get_formatter = lambda: argparse.HelpFormatter(parser.prog, 8)
    parser._positionals.title = LANG_HELP_POSITIONAL
    parser._optionals.title = LANG_HELP_OPTIONAL
    parser.add_argument('-h', '--help', action='store_true',
                        help=LANG_HELP_HELP)
    parser.add_argument('ipfilter', nargs='?', metavar=LANG_IPFILTER_META,
                        help=LANG_IPFILTER_HELP)
    parser.add_argument('-H', '--host', type=str, metavar=LANG_HOST_META,
                        help=f'{LANG_HOST_HELP}{kwargs["host"]}')
    parser.add_argument('-p', '--port', type=int, metavar=LANG_PORT_META,
                        help=f'{LANG_PORT_HELP}{kwargs["port"]}')
    parser.add_argument('-a', '--authorization', type=str, default='',
                        metavar=LANG_AUTHORIZATION_META,
                        help=LANG_AUTHORIZATION_HELP)
    parser.add_argument('-e', '--expire', type=int, metavar=LANG_EXPIRE_META,
            help=f'{LANG_EXPIRE_HELP}{kwargs["expire"] // 3600} {LANG_EXPIRE_META}')
    parser.add_argument('-f', '--log-header', type=str, metavar=LANG_HEADER_META,
            help=f'{LANG_HEADER_HELP}{kwargs["log_header_fmt"]}'.replace("%", "%%"))
    args = parser.parse_args()

    if args.help:
        print(f'\n{LANG_HELP_USAGE}:\n        {parser.format_help()[7:]}')
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
    UTorrentWebAPI(args.ipfilter, **kwargs).run()


if __name__ == '__main__':
    main()

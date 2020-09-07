#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""\
Checking & banning BitTorrent leech peers via Web API, remove ads, working for uTorrent.
"""
__app_name__ = 'Ban-Peers'
__version__ = '0.6.2'
__author__ = 'SeaHOH<seahoh@gmail.com>'
__license__ = 'MIT'
__copyright__ = '2020 SeaHOH'
__py_min__ = '3.7'
__py_max__ = '3.9'
__webpage__ = 'https://github.com/SeaHOH/ban-peers'


import sys
if sys.version_info < (3, 7):
    raise RuntimeError('Please run with Python3.7 and above!')

import os
import re
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
from socket import inet_pton, socket, getaddrinfo, AF_INET, AF_INET6
from shutil import get_terminal_size

from typing import *
from http.client import HTTPResponse


_linesep = os.linesep.replace('\r\n', '\n').encode()
_default_columns = 80
_max_columns = get_terminal_size().columns
if _max_columns < _default_columns and (
        os.name == 'nt' and os.system(f'mode con: cols={_default_columns}') == 0 or
        os.name != 'nt' and os.system(f'stty columns {_default_columns}') == 0):
    _max_columns = _default_columns
_max_columns -= 1
_1m = 1024 * 1024
_10m = _1m * 10
_100m = _1m * 100

TOKEN = re.compile('<div id=.token.[^>]*>([^<]+)</div>')
# The PEER CLIENT is not a PeerID or a User-Agent, it's a mixed string
# "-" prefix and suffix were removed by class `List2Attr`
LEECHER_XUNLEI = re.compile('''
^(?:
    7\.|sd|xl|xun|
    unknown\s(?:
        bt/7\.(?!
            (?:9|10)\.\d\D  | # BitTorrent
            0\.0\.0$          # BitTorrent?
        )|
        sd|xl
    )
)
''', re.I|re.X)
LEECHER_PLAYER = re.compile('''
^(?:
    dan               | # DanDan (DL)
    DLB|dlb           | # DLBT (DL)
    [Qq]vo            | # Qvod (QVOD) [Dead]
    [Ss]od            | # Soda
    [Tt]orc           | # Torch (TB)
    [Vv]ag            | # Vagaa (VG) [Dead?]
    [Xx]fp            | # Xfplay (XF)
    Unknown\s(?:
        DL            | # DanDan/DLBT (DL)
        QVO           | # Qvod (QVOD) [Dead]
        TB            | # Torch (TB)
        UW            | # uTorrent Web (UW)
        VG            | # Vagaa (VG) [Dead?]
        XF              # Xfplay (XF)
    )
)
''', re.X)
# Offline Download Servers/Seedboxes (does not used at present)
# Leech? Seems usually does not, depending on the settings thereof?
# bitport.io [Unknown ID/UA]
# justseed.it [Unknown UA] JS [Dead]
# put.io [Unknown ID/UA]
# seedbox.io libTorrent 0.13.6 RevDNS - *.seedbox.io
# seedboxws.com [Unknown ID/UA]
# seedhost.eu libTorrent 0.13.6 RevDNS - *.seedhost.eu
# seedr.cc [Unknown ID/UA]
# yourseedbox.com [Unknown ID/UA]
#LEECHER_OFFLINE = re.compile('''
#^(?:
#    [Jj]usts          | # Justseed.it client [Dead]
#    Unknown\s(?:
#        JS              # Justseed.it client [Dead]
#    )
#)
#''', re.X)
LEECHER_OTHER = re.compile('''
^(?:
    caca              | # Cacaoweb
    [Ff]lash[Gg]      | # FlashGet (FG)
    .+?ransp          | # Net Transport (NX) - need more infomation
    [Qq]{2}           | # QQ (QD) [Dead?]
    [Tt]uo            | # TuoTu (TT) [Dead?]
    Unknown\s(?:
        BN            | # Baidu (BN) [Dead?]
        FG            | # FlashGet (FG)
        NX            | # Net Transport (NX)
        QD            | # QQ (QD) [Dead?]
        TT              # TuoTu (TT) [Dead?]
    )
)
''', re.X)
# Did not included in uTorrent's peer identification
# https://www.bittorrent.org/beps/bep_0020.html
# https://wiki.theory.org/BitTorrentSpecification#peer_id
# Most of them has been died
CLIENT_UNKNOWN = re.compile('''
^Unknown\s(?!
    \d\dRS            | # Rufus [Dead]
    7T                | # aTorrent for Android
    AL                | # AllPeers [Dead]
    AT                | # Artemis [Dead]
    BE                | # Baretorrent [Dead?]
    BitS              | # BitSpirit
    BL                | # BitBlinder [Dead]
                        # BitCometLite
    BOW               | # Bits On Wheels [Dead]
    BP                | # BitTorrent Pro (Azureus + spyware) [Dead?]
    BS                | # BTSlave [Dead]
    Bt                | # Bt [library]
    #BT               | # BBtor [Dead]
    BT/7\.(?:           # mainline BitTorrent [versions >= 7.9]
        (?:9|10)\.\d\D| # So foolish that could not be identified
        0\.0\.0$        #
    )                 | #
    BW                | # BitWombat [Dead]
    DP                | # Propagate Data Client [Dead]
    FC                | # FileCroc [Dead]
    FD                | # Free Download Manager
    FW                | # FrostWire
    FX                | # Freebox BitTorrent
    GS                | # GSTorrent [Dead]
    HK                | # Hekate [Dead?]
    HM                | # hMule [Dead]
    IL                | # iLivid [Dead]
    JT                | # JavaTorrent
    KG                | # KGet [Dead]
    LC                | # LeechCraft
    LH                | # LH-ABC [Dead]
    #M\d-\d           | # Bram's old BitTorrent and many other clients [Dead]
    ML                | # MLdonkey
    MK                | # Meerkat [Dead]
    MO                | # MonoTorrent [Dead?]
    NE                | # BT Next Evolution [Dead?]
    OS                | # OneSwarm
    OT                | # OmegaTorrent [Dead]
    PD                | # Pando [Dead]
    PI                | # PicoTorrent
    PT                | # PHPTracker [Dead]
    #Q\d-\d           | # Queen Bee [Dead]
    #Q\d[a-zA-Z0-9]{2}| # BTQueue [Dead]
    RZ                | # RezTorrent [Dead?]
    SB                | # ~Swiftbit [Dead]
    SM                | # SoMud [Dead]
    ST                | # SymTorrent [Dead]
    st                | # sharktorrent [Dead]
    tT                | # tTorrent
    WD                | # WebTorrent Desktop
    WW                | # WebTorrent [library]
    WY                | # FireTorrent [Dead]
    XBT                 # XBT Client [Dead?]
)
''', re.X)


ANTI_ADS_SETTINGS = [(k, True) for k in (
    #'gui.pro_installed',  # If want using the pro style sidebar, uncomment this
                           # setting and run this script with `--remove-ads`,
                           # restart uTorrent at last
    'gui.playback_tab_hidden_by_user',
    'offers.ads_forgetme_on',
)] + [(k, False) for k in (
    # Commented settings below could not be set via Web API,
    # must modify the settings file directly
    #'ad_enabled',
    #'av_auto_update',
    #'av_enabled',
    'check_update',
    'check_update_beta',
    'enable_share',
    'distributed_share.enable',
    'ftenabled',
    'lrecenabled',
    'bt.enable_pulse',
    'gui.report_problems',
    'gui.show_av_icon',
    'gui.show_devices',
    'gui.show_gate_delete',
    'gui.show_gate_explaination',
    'gui.show_gate_notify',
    'gui.show_notorrents_node',
    'gui.show_player_node',
    'gui.show_plus_av_upsell',
    'gui.show_plus_conv_upsell',
    'gui.show_plus_upsell',
    'gui.show_plus_upsell_nodes',
    'gui.plus_upsell_foreground',
    'offers.enabled',
    'offers.adresource_enabled',
    'offers.adresource_kill_enabled',
    'offers.backup_left_rail_offer_enabled',
    'offers.backup_sponsored_torrent_offer_enabled',
    'offers.bigads_enabled',
    'offers.btfs_enabled',
    'offers.cfu_left_rail_offer_enabled',
    'offers.cfu_sponsored_torrent_offer_enabled',
    'offers.content_offer_autoexec',
    'offers.dlive_enabled',
    'offers.featured_content_badge_enabled',
    'offers.featured_content_notifications_enabled',
    'offers.featured_content_rss_enabled',
    'offers.ftEnabled',
    'offers.gdpr_consent_enabled',
    'offers.left_rail_offer_enabled',
    'offers.lrecEnabled',
    'offers.onboard_enabled',
    'offers.show_gdpr_consent',
    'offers.show_tip_now',
    'offers.sponsored_torrent_offer_enabled',
    'offers.superad_enabled',
    'offers.superad_adson',
    'offers.tronTV_enabled',
    'offers.upgrade_toolbar',
    'offers.wallet_ui_enabled',
    #'wallet_enabled',
)]

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

    _TYPES = {
        'TORRENT': {
            'HASH': 0,
            'STATUS': 1,
            'NAME': 2,
            'SIZE': 3,
            'PROGRESS': 4,
            'DOWNLOADED': 5,
            'UPLOADED': 6,
            'RATIO': 7,
            'UPSPEED': 8,
            'DOWNSPEED': 9,
            'ETA': 10,
            'LABEL': 11,
            'PEERS_CONNECTED': 12,
            'PEERS_SWARM': 13,
            'SEEDS_CONNECTED': 14,
            'SEEDS_SWARM': 15,
            'AVAILABILITY': 16,
            'QUEUE_POSITION': 17,
            'REMAINING': 18,
            'DOWNLOAD_URL': 19,
            'RSS_FEED_URL': 20,
            'STATUS_MESSAGE': 21,
            'STREAM_ID': 22,
            'DATE_ADDED': 23,
            'DATE_COMPLETED': 24,
            'APP_UPDATE_URL': 25,
            'SAVE_PATH': 26
        },
        'FILE': {
            'NAME': 0,
            'SIZE': 1,
            'DOWNLOADED': 2,
            'PRIORITY': 3,
            'FIRST_PIECE': 4,
            'NUM_PIECES': 5,
            'STREAMABLE': 6,
            'ENCODED_RATE': 7,
            'DURATION': 8,
            'WIDTH': 9,
            'HEIGHT': 10,
            'STREAM_ETA': 11,
            'STREAMABILITY': 12
        },
        'PEER': {
            'COUNTRY': 0,
            'IP': 1,
            'REVDNS': 2,
            'UTP': 3,
            'PORT': 4,
            'CLIENT': 5,
            'FLAGS': 6,
            'PROGRESS': 7,
            'DOWNSPEED': 8,
            'UPSPEED': 9,
            'REQS_OUT': 10,
            'REQS_IN': 11,
            'WAITED': 12,
            'UPLOADED': 13,
            'DOWNLOADED': 14,
            'HASHERR': 15,
            'PEERDL': 16,
            'MAXUP': 17,
            'MAXDOWN': 18,
            'QUEUED': 19,
            'INACTIVE': 20,
            'RELEVANCE': 21
        }
    }

    def __init__(self, list:List[Union[int, str]], type:str) -> None:
        object.__setattr__(self, '_list', list)
        object.__setattr__(self, '_type', self._TYPES[type.upper()])

    def __getattr__(self, name:str) -> Union[int, float, str]:
        name = name.upper()
        value = self._list[self._type[name]]
        if name == 'IP' and ':' in value:
            return f'[{value}]'
        elif name == 'CLIENT' and value[:1] == '-':
            return value.split('-')[1]
        elif name == 'AVAILABILITY':
            return value / 65536
        return value

    def __setattr__(self, name:str, value:Union[int, str]) -> None:
        name = name.upper()
        if name == 'IP' and value[:1] == '[':
            value = value[1:-1]
        elif name == 'AVAILABILITY':
            value = int(value * 65536)
        self._list[self._type[name]] = value


class UTorrentWebAPI:
    def __init__(self,
                ipfilter:Optional[str], host:str='127.0.0.1', port:int=8080,
                username:Optional[str]='', password:Optional[str]='',
                expire:int=3600*12, log_header_fmt:str='%H:%M:%S',
                xunlei_reprieve:bool=True, check_fake_progress:bool=True,
                check_serious_leech:bool=True, check_private:bool=False,
                log_unknown=False) -> None:
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
        self.log_unknown = log_unknown
        self.log_header_fmt = log_header_fmt
        self._params_list = {'list': 1, 'cid': 0, 'getmsg': 1}
        self._seeds_private = {}
        self._statistics = {}
        self._statistics_progress = collections.defaultdict(dict)
        self._statistics_uploaded = collections.defaultdict(dict)
        self._statistics_str = ''
        self._need_save = False
        self.running = False
        self.log_ip = {}
        self.init_ipfilter()
        self.init_opener()
        self.get_token()

    def init_ipfilter(self) -> None:
        self.ipfilter = ipfilter = {}
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
        ), len(self.ipfilter_range) + 2)  # at least 2, 1 is line buffering
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
        self._opener = opener = OpenerDirector()
        for handler_name in ['HTTPCookieProcessor', 'HTTPHandler',
                             'HTTPDefaultErrorHandler', 'HTTPRedirectHandler']:
            handler = getattr(urllib.request, handler_name)()
            if handler_name == 'HTTPCookieProcessor':
                self._cookiejar = handler.cookiejar
            opener.add_handler(handler)

    def set_authorization(self, username:Optional[str], password:Optional[str]) -> None:
        if username or password:
            self._req.add_header('Authorization',
                                'Basic ' + base64.b64encode(
                                f'{username or ""}:{password or ""}'.encode()
                                ).decode('ascii'))


    def request(self, path:str='', params:Optional[Mapping[str, Union[int, str]]]=None
                ) -> Union[HTTPResponse, NoReturn]:
        if params:
            params_str = urlencode({
                'token': self._token,
                **params,
                't': int(time.time())
            })
            url = f'{self._url_root}{path}?{params_str}'
        else:
            url = f'{self._url_root}{path}'
        if self._req.full_url != url:
            self._req.full_url = url
        response = self._opener.open(self._req)
        while response.code == 401:
            if path == 'pair/':
                raise HTTPError(url, response.code, response.msg, response.headers, response)
            self.set_authorization(input(LANG_INPUT_USERNAME),
                                   input(LANG_INPUT_PASSWORD))
            response = self._opener.open(self._req)
        if response.code == 400 and path != 'token.html':
            time.sleep(1)  # Waite 1s, or still 401 for pairing
            self.get_token()
        if response.code != 200:
           raise HTTPError(url, response.code, response.msg, response.headers, response)
        return response

    def get_token(self) -> None:
        self._req.remove_header('Cookie')
        self._cookiejar.clear()
        html = self.request(path='token.html').read().decode()
        self._token = TOKEN.search(html).group(1)

    def is_private(self, hash:str) -> bool:
        try:
            return self._seeds_private[hash]
        except KeyError:
            result = json.load(self.request(params={
                'action': 'getprops',
                'hash': hash
            }))
            self._seeds_private[hash] = private = \
                    result['props'][0]['pex'] == -1
            return private

    def get_torrents(self) -> Iterable[List2Attr]:
        torrents = json.load(self.request(params=self._params_list))
        if 'torrentc' in torrents:
            self._params_list['cid'] = torrents['torrentc']
        for hash in torrents.get('torrentm', []):
            self._seeds_private.pop(hash, None)
            self._statistics_progress.pop(hash, None)
            self._statistics_uploaded.pop(hash, None)
        for torrent in torrents.get('torrents') or torrents.get('torrentp', []):
            torrent = List2Attr(torrent, 'torrent')
            if torrent.peers_connected and (self.check_private or
                     not self.is_private(torrent.hash)):
                yield torrent

    def get_files(self, hash:str) -> Iterable[List2Attr]:
        result = json.load(self.request(params={
            'action': 'getfiles',
            'hash': hash
        }))
        return (List2Attr(peer, 'file') for peer in result['files'][1])

    def get_peers(self, hash:str) -> Iterable[List2Attr]:
        result = json.load(self.request(params={
            'action': 'getpeers',
            'hash': hash
        }))
        return (List2Attr(peer, 'peer') for peer in result['peers'][1])

    def set_setting(self, s:str, v:Union[int, str, bool], log:bool=True) -> None:
        self.request(params={
            'action': 'setsetting',
            's': s,
            'v': v
        })
        if log:
            print(f'{self.log_header}{LANG_SET_SETTING} {s!r} {LANG_TO} {v}')

    def ban_peers(self) -> None:
        ct = int(time.time())
        expire = ct - self.expire
        expire_interim = ct - 3600
        expire_ips = list(ip
            for ip, (_, reason, _, timestamp) in self.ipfilter.items()
            if timestamp < expire or timestamp < expire_interim and \
                reason.startswith((b'Seeding', b'Suspected'))
        )
        if self._need_save or expire_ips:
            for ip in expire_ips:
                del self.ipfilter[ip]
            self.save_ipfilter()
            self.set_setting('ipfilter.enable', True, False)
        if self._need_save:
            self.collect_statistics()
            self._need_save = False

    def ban_push(self, hash:str, peer:List2Attr, reason:str='') -> None:
        ct = int(time.time())
        ip = peer.ip
        try:
            d = self._statistics.pop(ip)
        except KeyError:
            d = {}
        d[hash] = peer.downloaded, peer.uploaded
        self._statistics[ip] = d
        limit_dict_lenght(self._statistics, 1024)
        reason = f'{reason} [{peer.client}]'
        self.log_ip.pop(ip, None)
        self.ipfilter.pop(ip, None)
        self.ipfilter[ip] = ip.encode(), reason.encode(), str(ct).encode(), ct
        self._need_save = True
        print(f'{self.log_header}{LANG_BANNED} '
              f'{ip}:{peer.port}@{peer.country}：{reason}, '
              f'{LANG_DOWNLOADED}: {make_size_human(peer.downloaded)}, '
              f'{LANG_UPLOADED}: {make_size_human(peer.uploaded)} ')

    def check_peers(self) -> None:
        def log(msg):
            ip = peer.ip
            try:
                self.log_ip.pop(ip)
            except KeyError:
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
                size_todl_tenth = int(sum(file.size for file in files
                                     if file.priority) / 10)
                size_last_downloaded = torrent.downloaded - sum(
                                       file.downloaded for file in files)
            for peer in self.get_peers(hash):
                if peer.ip in self.ipfilter:
                    continue
                ip_port = f'{peer.ip}:{peer.port}'
                if peer.progress >= 1000:
                    if 'u' in peer.flags.lower():
                        # This is not a check, should not be skipped
                        reasons.append('Progress')
                elif not self.check_fake_progress:
                    pass
                elif peer.uploaded > torrent.size:
                    reasons.append('Suspected')
                    reasons.append('Progress')
                elif seeding or peer.downloaded == 0:
                    try:
                        last_progress, last_uploaded, t = \
                                self._statistics_progress[hash][ip_port]
                        fo = None
                    except KeyError:
                        fo = True
                    if fo or peer.progress < last_progress:
                        last_progress = peer.progress
                        last_uploaded = peer.uploaded
                        t = None
                    elif peer.inactive < 10 and \
                            (peer.uploaded - last_uploaded) > \
                            (peer.progress - last_progress + 1) * size_millesimal:
                        ct = time.monotonic()
                        if t is None:
                            t = ct
                        elif ct - t > 60:  # Did not recovered within one minute
                            if seeding:
                                reasons.append('Seeding')
                            reasons.append('Progress')
                            t = None
                    else:
                        t = None
                    self._statistics_progress[hash][ip_port] = \
                            last_progress, last_uploaded, t
                if reasons:
                    log(f'{LANG_FACK_PROGRESS} [{peer.progress/10}%]')
                if peer.port >= 65000 and \
                        peer.country == 'CN' and \
                        'Transmission' in peer.client and \
                        peer.downloaded == peer.relevance == 0:
                    # Chinese Offline Download Servers, almost are leech clients
                    log(LANG_OFFLINE_SERVER)
                    if reasons and reasons[0] != 'Progress':
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
                        if reasons and reasons[0] != 'Progress':
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
                    # uTorrent identification
                    # It mistook uTorrent Android versions, so foolish
                    # I would never to feedback this issue to official
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
                if self.check_serious_leech:
                    try:
                        luploaded, suploaded, _suploaded, t = \
                                self._statistics_uploaded[hash][ip_port]
                    except KeyError:
                        luploaded = suploaded = _suploaded = 0
                        t = None
                        if size_last_downloaded > _10m:
                            # May has been seeding before
                            _suploaded = peer.uploaded
                    if seeding:
                        _suploaded = peer.uploaded - luploaded
                        uploaded = 0
                    else:
                        luploaded = peer.uploaded
                        if _suploaded:
                            suploaded += _suploaded
                            _suploaded = 0
                        uploaded = luploaded - suploaded
                    if not reasons and uploaded and peer.progress < 1000 and \
                            ('d' in peer.flags or peer.waited > 60) and \
                            peer.relevance > 0 and \
                            uploaded > min(max(size_todl_tenth, _10m), _100m) and \
                            peer.downloaded * 10 < uploaded and \
                            peer.downloaded * 10 / size_millesimal < peer.relevance:
                        ct = time.monotonic()
                        if t is None:
                            t = ct
                        elif ct - t > peer.downloaded / _1m * 10:
                            # Did not reached conditions within 10X seconds
                            # X means it had downloaded X MiB from peer
                            log(LANG_LEECHER_SUSPECTED)
                            reasons.append('Suspected')
                            reasons.append('Leecher')
                            t = None
                    else:
                        t = None
                    self._statistics_uploaded[hash][ip_port] = \
                            luploaded, suploaded, _suploaded, t
                if self.log_unknown and CLIENT_UNKNOWN.search(peer.client):
                    log(LANG_UNKNOWN_CLIENT)
                if reasons:
                    try:
                        self.ban_push(hash, peer, ' '.join(reasons))
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

    def run(self, pair=None, show_operations:bool=True) -> None:
        def log(msg):
            print(f'{self.log_header}uTorrent {LANG_A_NAME}{msg}{LANG_RUNNING}')

        if self.running:
            return
        self.running = True
        disconnected = False
        pause = False
        ss = False
        self.set_setting('bt.use_rangeblock', False)
        self.set_setting('ipfilter.enable', True)
        log(LANG_START)
        while True:
            if not self.running:
                break
            err_cr = None
            if not pause:
                try:
                    self.check_peers()
                    self.ban_peers()
                except URLError as e:
                    if isinstance(e.reason, ConnectionRefusedError):
                        if not disconnected:
                            print(f'{self.log_header}uTorrent {LANG_DISCONNECTED}')
                            # Don't clear `self._statistics`
                            self._statistics_progress.clear()
                            self._statistics_uploaded.clear()
                        print(f'{self.log_header}{LANG_CONNECTION_REFUSED} '
                              f'WebUI@{self._url_root}', end='\r')
                        disconnected = err_cr = True
                        time.sleep(10)
                    elif not (disconnected and isinstance(e, HTTPError)):
                        print(f'{self.log_header}{LANG_ERROR_OCCURRED}: '
                              f'{e}, {e.filename}')
                except Exception as e:
                    logging.exception(f'{self.log_header}{LANG_ERROR_OCCURRED}: {e}')
                if disconnected and err_cr is None:
                    # Reconnected
                    print(f'{self.log_header}uTorrent {LANG_RECONNECTED}')
                    if isinstance(pair, UTorrentPairing):
                        with pair:
                            # Remove upsell tip in the sidebar
                            pair.set_setting('gui.show_plus_upsell_nodes', False)
                    disconnected = False
            for _ in range(5):
                if show_operations:
                    print(CLL, end='')
                    msgs = ss and self.statistics or LANG_OPERATES_TIP,
                    if err_cr:
                        msgs = LANG_DISCONNECTED.upper(), *msgs
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


class UTorrentPairing:
    def __init__(self, utweb:UTorrentWebAPI, close_pairing:bool=False) -> None:
        self._utweb = utweb
        self._close_pairing = close_pairing
        self._url_root = utweb._url_root.replace('/gui/', '/btapp/')
        self._req = Request(self._url_root)
        self._opener = utweb._opener
        self._pairing = None
        self._session = None

    def request(self, params:Mapping[str, Union[int, str]]) -> Union[HTTPResponse, NoReturn]:
        params_str = urlencode({
            'pairing': self._pairing,
            **params
        })
        url = f'{self._url_root}?{params_str}'
        if self._req.full_url != url:
            self._req.full_url = url
        response = self._opener.open(self._req)
        if response.code == 400:
            if 'session' in params:
                self.get_session()
            else:
                self.get_pairing()
        if response.code != 200:
           raise HTTPError(url, response.code, response.msg, response.headers, response)
        return response

    def get_pairing(self) -> Optional[NoReturn]:
        self._utweb.set_setting('webui.allow_pairing', True)
        try:
            self._pairing = self._utweb.request('pair/',
                                {'name': f'{__app_name__} {__version__}'}
                                ).read().decode('ascii')
        except Exception as e:
            if isinstance(e, HTTPError) and e.code == 401:
                print(f'{self.log_header}{LANG_PAIRING_REJECTED}')
            if self._close_pairing:
                self._utweb.set_setting('webui.allow_pairing', False)
            self._pairing = None
            raise

    def get_session(self) -> None:
        if self._pairing is None:
            self.get_pairing()
        result = json.load(self.request({
            'type': 'state',
            'queries': '[[btapp]]'
        }))
        self._session = result['session']

    def set_setting(self, s:str, v:Union[int, str, bool]) -> Optional[NoReturn]:
        if self._session is None:
            self.get_session()
        while True:
            result = json.load(self.request({
                'session': self._session,
                'type': 'function',
                'path': '["btapp","settings","set"]',
                'args': json.dumps([s, v])
            }))
            error = result.get('error')
            if error is None:
                self._session = result['session']
                break
            elif error == 'session has expired':
                self.get_session()
            else:
                print(f'{self.log_header}set_setting({s!r}, {v}) {LANG_FAIL}: {error}')
                return
        print(f'{self.log_header}{LANG_SET_SETTING} {s!r} {LANG_TO} {v}')

    @property
    def log_header(self) -> str:
        return self._utweb.log_header

    def __enter__(self):
        return self

    def __exit__(self, etype, value, tb) -> Literal[True]:
        if self._pairing and self._close_pairing:
            self._utweb.set_setting('webui.allow_pairing', False)
        self._pairing = None
        self._session = None
        if value and not (etype is HTTPError and value.code == 401):
            logging.exception(f'{self.log_header}{LANG_ERROR_OCCURRED}: {value}')
        return True  # Make no Exception would be raised


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
    LANG_FAIL = '失败'
    LANG_ERROR_OCCURRED = '发生错误'
    LANG_CONNECTION_REFUSED = '无法连接'
    LANG_RECONNECTED = '已重新连接'
    LANG_DISCONNECTED = '已断开连接'
    LANG_BANNED = '已屏蔽'
    LANG_FOUND = '发现'
    LANG_FACK_PROGRESS = '汇报虚假进度'
    LANG_XUNLEI = '迅雷'
    LANG_PLAYER = '播放器'
    LANG_FACK_CLIENT = '假冒客户端'
    LANG_OFFLINE_SERVER = '离线下载服务器'
    LANG_LEECHER_CLIENT = '吸血客户端'
    LANG_LEECHER_SUSPECTED = '高度疑似吸血'
    LANG_UNKNOWN_CLIENT = '未知客户端'
    LANG_STATISTICS = '统计'
    LANG_DOWNLOADED = '已下载'
    LANG_UPLOADED = '已上传'
    LANG_OPERATES_TIP = ('请选择你要执行的操作: '
                         '(Q)退出，(S)停止，(R)重新开始，(P)暂停/恢复')
    LANG_PAIRING_REJECTED = '配对请求已被拒绝!'
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
    LANG_HELP_HEADER = '日志头格式，参见 time.strftime，默认'
    LANG_HELP_RESOLVE_COUNTRY = '启动时，设置 uTorrent 解析对端国家代码'
    LANG_HELP_NO_XUNLEI_REPRIEVE = '直接屏蔽迅雷，不进行更多的检查'
    LANG_HELP_NO_FAKE_PROGRESS_CHECK = '不进行虚假进度检查'
    LANG_HELP_NO_SERIOUS_LEECH_CHECK = '不进行严重吸血检查'
    LANG_HELP_PRIVATE_CHECK = '启用对私人种子的检查'
    LANG_HELP_LOG_UNKNOWN = '将未知客户端记入日志'
    LANG_HELP_REMOVE_ADS = ('通过高级设置移除广告，仅工作于本地主机，'
                            '也无法工作于较旧版本的 uTorrent')
    LANG_HELP_NO_CLOSE_PAIRING = '移除广告后，不关闭网络配对配置项'
    __doc__ = '通过网页 API 检查并屏蔽 BitTorrent 吸血对端，移除广告，工作于 uTorrent。'
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
    LANG_FAIL = 'fail'
    LANG_ERROR_OCCURRED = 'error occurred'
    LANG_CONNECTION_REFUSED = 'unable to connect'
    LANG_RECONNECTED = 'reconnected'
    LANG_DISCONNECTED = 'disconnected'
    LANG_BANNED = 'banned'
    LANG_FOUND = ' found '
    LANG_FACK_PROGRESS = 'report fack progress'
    LANG_XUNLEI = 'XunLei'
    LANG_PLAYER = 'player'
    LANG_FACK_CLIENT = 'fack client'
    LANG_OFFLINE_SERVER = 'offline download server'
    LANG_LEECHER_CLIENT = 'leecher client'
    LANG_LEECHER_SUSPECTED = 'highly suspected of leecher'
    LANG_UNKNOWN_CLIENT = 'unknown client'
    LANG_STATISTICS = 'Statis'
    LANG_DOWNLOADED = 'D'
    LANG_UPLOADED = 'U'
    LANG_OPERATES_TIP = ('Choose your operation: '
                         '(Q)uit, (S)top, (R)estart, (P)ause/Proceed')
    LANG_PAIRING_REJECTED = 'Pairing request has been rejected!'
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
    LANG_HELP_HEADER = 'Format of log header, see time.strftime, default'
    LANG_HELP_RESOLVE_COUNTRY = 'Set uTorrent to resolved peer\'s country code at start-up'
    LANG_HELP_NO_XUNLEI_REPRIEVE = 'Banned XunLei directly, no more checking'
    LANG_HELP_NO_FAKE_PROGRESS_CHECK = 'Don\'t checking fake progress'
    LANG_HELP_NO_SERIOUS_LEECH_CHECK = 'Don\'t checking serious leech'
    LANG_HELP_PRIVATE_CHECK = 'Enable checking for private seeds'
    LANG_HELP_LOG_UNKNOWN = 'Logging unknown clients'
    LANG_HELP_REMOVE_ADS = ('Remove ads via set Advanced Settings, '
                            'only working for localhost, '
                            'and to fail in older uTorrent')
    LANG_HELP_NO_CLOSE_PAIRING = 'Don\'t turn off Web Pairing setting after remove ads'

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
    parser.add_argument('-U', '--log-unknown', action='store_true',
                        help=LANG_HELP_LOG_UNKNOWN)
    parser.add_argument('-A', '--remove-ads', action='store_true',
                        help=LANG_HELP_REMOVE_ADS)
    parser.add_argument('-O', '--no-close-pairing', action='store_true',
                        help=LANG_HELP_NO_CLOSE_PAIRING)
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
    if args.log_unknown:
        kwargs['log_unknown'] = True

    ut = UTorrentWebAPI(args.ipfilter, **kwargs)
    utp = None
    if all(ipaddr[4][0] in ('127.0.0.1', '::1')
            for ipaddr in getaddrinfo(kwargs['host'], None)):
        utp = UTorrentPairing(ut, not args.no_close_pairing)
        with utp:
            if args.remove_ads:
                for kv in ANTI_ADS_SETTINGS:
                    utp.set_setting(*kv)
            else:
                # Remove upsell tip in the sidebar, for free release versions,
                # uTorrent reset this setting to True every start-up
                utp.set_setting('gui.show_plus_upsell_nodes', False)
    if args.resolve_country:
        ut.set_setting('peer.resolve_country', True)
        ut.set_setting('resolve_peerips', True)
    ut.run(utp)


if __name__ == '__main__':
    main()

#!/usr/bin/python3
# -*- coding: utf-8 -*-

_ = lambda s: s

__doc__ = _("""\
Checking & banning BitTorrent leech peers via Web API, remove ads, working for
uTorrent.
""")
__app_name__ = 'Ban-Peers'
__version__ = '0.9.2'
__author__ = 'SeaHOH'
__email__ = 'seahoh@gmail.com'
__license__ = 'MIT'
__copyright__ = '2020 SeaHOH'
__py_min__ = '3.7'
__py_max__ = '3.9'
__webpage__ = 'https://github.com/SeaHOH/ban-peers'
# END OF METADATA *** DON'T MODIFY OR DELETE THIS LINE ***


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


try:
    from .i18n.gettext import translation
except ImportError:
    print('Import .i18n.gettext fail, can not load localization function!')
else:
    try:
        _ = translation(re.sub('[^a-z]', '', __app_name__.lower())).gettext
    except FileNotFoundError:
        pass

description = __doc__ = _(__doc__)
__doc__ = f'''\
{__app_name__} {__version__}

{__doc__}

{__license__} License Copyright (c) {__copyright__}

Python Version: {__py_min__} - {__py_max__}

Web Page: {__webpage__}
'''


_linesep = os.linesep.replace('\r\n', '\n').encode()
_default_columns = 80
_max_columns = get_terminal_size().columns
if _max_columns < _default_columns and (
        os.name == 'nt' and os.system(f'mode con: cols={_default_columns}') == 0 or
        os.name != 'nt' and os.system(f'stty columns {_default_columns}') == 0):
    _max_columns = _default_columns
_max_columns -= 1

CLL = f'\r{" " * _max_columns}\r'

_1m = 1024 * 1024
_10m = _1m * 10
_100m = _1m * 100
_500m = _1m * 500
_1g = _1m * 1024
_2g = _1g * 2
_4g = _1g * 4
_10g = _1g * 10

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
    BI                | # BiglyBT
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
    from msvcrt import kbhit, getch  # type: ignore

    def get_keyhit() -> Optional[bytes]:
        if kbhit():
            return getch()
        return None

except ImportError:
    import select

    def get_keyhit() -> Optional[bytes]:
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.buffer.read(1)
        return None


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
    
    hash:str
    status:int
    name:str
    size:int
    progress:int
    downloaded:int
    uploaded:int
    ratio:int
    upspeed:int
    downspeed:int
    eta:int
    label:str
    peers_connected:int
    peers_swarm:int
    seeds_connected:int
    seeds_swarm:int
    availability:float
    queue_position:int
    remaining:int
    download_url:str
    rss_feed_url:str
    status_message:str
    stream_id:str
    date_added:int
    date_completed:int
    app_update_url:str
    save_path:str

    priority:int
    first_piece:int
    num_pieces:int
    streamable:int
    encoded_rate:int
    duration:int
    width:int
    height:int
    stream_eta:int
    streamability:int

    country:str
    ip:str
    revdns:str
    utp:int
    port:int
    client:str
    flags:str
    reqs_out:str
    reqs_in:str
    waited:int
    hasherr:int
    peerdl:int
    maxup:int
    maxdown:int
    queued:int
    inactive:int
    relevance:int

    _cache:dict
    _list:list
    _type:dict

    _32bit1 = ~(-1 << 32)
    _32bit_signed_mini = -1 << 31

    def __init__(self, list:List[Union[int, str]], type:str) -> None:
        object.__setattr__(self, '_cache', {})
        object.__setattr__(self, '_list', list)
        object.__setattr__(self, '_type', self._TYPES[type.upper()])

    def __getattr__(self, name:str) -> Union[int, float, str]:
        name = name.upper()
        try:
            return self._cache[name]
        except KeyError:
            value = self._list[self._type[name]]
        if isinstance(value, int) and 0 > value >= self._32bit_signed_mini:
            # [PEER] Overflow 32bit signed (2G - 4G)
            value &= self._32bit1
        if name == 'IP' and ':' in value:
            value = f'[{value}]'
        elif name == 'CLIENT' and value[:1] == '-':
            value = value.split('-')[1]
        elif name == 'AVAILABILITY':
            value = value / 65536
        self._cache[name] = value
        return value

    def __setattr__(self, name:str, value:Union[int, float, str]) -> None:
        name = name.upper()
        self._list[self._type[name]]
        if name == 'IP' and isinstance(value, str) and value[:1] == '[':
            value = value[1:-1]
        elif name == 'AVAILABILITY':
            value = int(value * 65536)
        self._cache[name] = value

    def getraw(self, name:str) -> Union[int, float, str]:
        return self._list[self._type[name.upper()]]


class UTorrentWebAPI:
    def __init__(self,
                ipfilter:Optional[str], host:str='127.0.0.1', port:int=8080,
                username:Optional[str]=None, password:Optional[str]=None,
                expire:int=3600*12, time_allowed_refuse:int=600,
                log_header_fmt:str='%H:%M:%S', xunlei_reprieve:bool=True,
                check_fake_progress:bool=True, check_serious_leech:bool=True,
                check_refused_upload:bool=True, check_private:bool=False,
                log_unknown:bool=False) -> None:
        while not ipfilter:
            ipfilter = input(_('Please input uTorrent settings folder path '
                               'or ipfilter file path:\n'))
        if os.path.isdir(ipfilter):
            ipfilter = os.path.join(ipfilter, 'ipfilter.dat')
        try:
            socket().connect((host, port))
        except:
            raise ValueError(_('Unable to connect %(host)s:%(port)d') % vars())
        self.file_ipfilter = ipfilter
        self._url_root = f'http://{host}:{port}/gui/'
        self._req = Request(self._url_root)
        self.set_authorization(username, password)
        self.expire = expire
        self.time_allowed_refuse = max(time_allowed_refuse, 300)
        self.xunlei_reprieve = xunlei_reprieve
        self.check_fake_progress = check_fake_progress
        self.check_serious_leech = check_serious_leech
        self.check_refused_upload = check_refused_upload
        self.check_private = check_private
        self.log_unknown = log_unknown
        self.log_header_fmt = log_header_fmt
        self._params_list = {'list': 1, 'cid': 0, 'getmsg': 1}
        self._high_level:Set[str] = set()
        self._torrents_private:Dict[str, bool] = {}
        self._statistics:Dict[str, Dict[str, Tuple[int, int]]] = {}
        self._statistics_started:Dict[str, float] = {}
        self._statistics_overflow:MutableMapping \
                [str, Dict[str, Tuple[int, ...]]] = collections.defaultdict(dict)
        self._statistics_progress:MutableMapping \
                [str, Dict[str, Union[float, Tuple[int, int, Optional[float]]]]] \
                = collections.defaultdict(dict)
        self._statistics_uploaded:MutableMapping \
                [str, Dict[str, Tuple[int, int, int, Optional[float]]]] \
                = collections.defaultdict(dict)
        self._statistics_refused:MutableMapping \
                [str, Dict[str, Optional[float]]] = collections.defaultdict(dict)
        self._statistics_str = ''
        self._need_save = False
        self.running = False
        self.log_ip:Dict[str, Literal[True]] = {}
        self.init_ipfilter()
        self.init_opener()
        self.get_token()

    def init_ipfilter(self) -> None:
        ipfilter:Dict[str, Tuple[bytes, bytes, bytes, int]] = {}
        self.ipfilter = ipfilter
        ipfilter_range = []
        ct = int(time.time())
        ct_bytes = str(ct).encode()
        for line in (os.path.exists(self.file_ipfilter) and
                     open(self.file_ipfilter, 'rb') or ()):
            ip, _, rest = [p.strip() for p in line.partition(b'#')]
            if b'-' in ip:
                # Store IP range as is
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
                ) -> HTTPResponse:
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
            self.set_authorization(input(_('Please input WebUI username: ')),
                                   input(_('Please input WebUI password: ')))
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
        m = TOKEN.search(html)
        self._token = m and m.group(1)

    def is_private(self, hash:str) -> bool:
        try:
            return self._torrents_private[hash]
        except KeyError:
            props = self.get_props(hash)
            self._torrents_private[hash] = private = \
                    props['dht'] == props['pex'] == -1 and (
                    props['trackers'].find('?') > 0 or
                    props['trackers'].count('://') < 3)  # Maybe flag by mistake
            return private

    def get_torrents(self) -> Iterable[List2Attr]:
        torrents = json.load(self.request(params=self._params_list))
        if 'torrentc' in torrents:
            self._params_list['cid'] = torrents['torrentc']
        for hash in torrents.get('torrentm', []):
            self._high_level.discard(hash)
            self._torrents_private.pop(hash, None)
            self._statistics_started.pop(hash, None)
            self._statistics_overflow.pop(hash, None)
            self._statistics_progress.pop(hash, None)
            self._statistics_uploaded.pop(hash, None)
            self._statistics_refused.pop(hash, None)
        for torrent in torrents.get('torrents') or torrents.get('torrentp', []):
            torrent = List2Attr(torrent, 'torrent')
            if (torrent.peers_connected or torrent.seeds_connected) and \
                    (self.check_private or not self.is_private(torrent.hash)):
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
            self.log(_('Set uTorrent setting %(name)r to %(value)s')
                     % {'name': s, 'value': v})

    def get_props(self, hash:str) -> dict:
        result = json.load(self.request(params={
            'action': 'getprops',
            'hash': hash
        }))
        return result['props'][0]

    def set_props(self, hash:str, s:str, v:Union[int, str, bool]) -> None:
        self.request(params={
            'action': 'setprops',
            'hash': hash,
            's': s,
            'v': v
        })
        self.log(_('[%(hash)s] set property %(name)r to %(value)s')
                 % {'hash': hash, 'name': s, 'value': v})

    def ban_peers(self) -> None:
        ct = int(time.time())
        expire = ct - self.expire
        expire_interim = ct - 3600
        expire_ips = list(ip
            for ip, (_, reason, _, timestamp) in self.ipfilter.items()
            if timestamp < expire or timestamp < expire_interim and \
                reason.startswith((b'Seeding', b'Suspected', b'Refused'))
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
        self.log(_('Banned %(ip)s:%(port)d@%(country)s: %(reason)s, '
                   'downloaded: %(dlsize)s, uploaded: %(ulsize)s')
                 % {'ip': ip, 'port': peer.port,
                    'country': peer.country, 'reason': reason,
                    'dlsize': make_size_human(peer.downloaded),
                    'ulsize': make_size_human(peer.uploaded)})

    def check_peers(self) -> None:
        def log(msg):
            ip = peer.ip
            try:
                self.log_ip.pop(ip)
            except KeyError:
                self.log(_('[%(hash)s][%(torrent)s] found %(message)s: '
                           '[%(client)s]@%(ip&port)s')
                         % {'hash': hash, 'torrent': torrent.name,
                            'message': msg, 'client': peer.client,
                            'ip&port': ip_port})
            self.log_ip[ip] = True
            limit_dict_lenght(self.log_ip, 32)

        reasons = []
        ct = time.monotonic()
        for torrent in self.get_torrents():
            size_millesimal = torrent.size // 1000
            seeding = torrent.progress >= 1000  # uTorrent bug?
            hash = torrent.hash
            if seeding:
                self._statistics_started.pop(hash, None)
            else:
                started = self._statistics_started.setdefault(hash, ct)
            if self.check_fake_progress or self.check_serious_leech:
                files = list(self.get_files(hash))
                size_todl = sum(file.size for file in files if file.priority)
                size_todl_tenth = size_todl // 10
                size_downloaded = sum(file.downloaded for file in files)
                size_last_downloaded = torrent.downloaded - size_downloaded
                time_fp = 60
                ratio_sl = 10
                # High level thresholds are used for older/weaker Torrents
                if hash in self._high_level:
                    if torrent.availability < 10:
                        time_fp = 300
                        ratio_sl = 30
                elif not seeding and ct - started > 300 and \
                        torrent.eta * _10g > torrent.remaining * 86400:
                        # Less than 10 GiB/day
                    time_fp = 300
                    ratio_sl = 30
                    self.log(_('[%(hash)s][%(torrent)s] '
                               'increase additional check threshold')
                             % {'hash': hash, 'torrent': torrent.name})
                    self._high_level.add(hash)
                    if size_todl > _1g:
                        # Limit upload rate to increase read cache hits
                        # and availability (helps complete download)
                        self.set_props(hash, 'ulrate',
                                       _1m // 2 if size_todl > _10g else _1m)
            allow_banned_refused_upload = torrent.availability > 10
            for peer in self.get_peers(hash):
                if peer.ip in self.ipfilter or peer.upspeed < 256 and \
                        peer.progress == peer.relevance == peer.downspeed == 0:
                    continue
                ip_port = f'{peer.ip}:{peer.port}'
                # Relieve integer overflow 32bit in peer data
                try:
                    last_uploaded, last_downloaded, up_ot, down_ot = \
                            self._statistics_overflow[hash][ip_port]
                except KeyError:
                    last_uploaded, last_downloaded, up_ot, down_ot = \
                            peer.uploaded, peer.downloaded, 0, 0
                if last_uploaded > peer.uploaded + _2g:
                    up_ot += 1
                if last_downloaded > peer.downloaded + _2g:
                    down_ot += 1
                self._statistics_overflow[hash][ip_port] = \
                            peer.uploaded, peer.downloaded, up_ot, down_ot
                if up_ot:
                    peer.uploaded += up_ot * _4g
                if down_ot:
                    peer.downloaded += down_ot * _4g
                relevance = size_millesimal * peer.relevance + peer.downloaded
                if peer.downloaded > 0:
                    self._statistics_progress[hash].pop(ip_port, None)
                elif peer.progress >= 1000:
                    uct = self._statistics_progress[hash].pop(ip_port, None)
                    if 'u' in peer.flags.lower():
                        # This is not a check, should not be skipped
                        if uct is None or isinstance(uct, tuple):
                            self._statistics_progress[hash][ip_port] = ct
                        elif ct - uct < 20:
                            reasons.append('Progress')
                elif not self.check_fake_progress:
                    pass
                elif peer.uploaded > torrent.size:
                    reasons.append('Suspected')
                    reasons.append('Progress')
                else:
                    try:
                        _sp = self._statistics_progress[hash][ip_port]
                        assert isinstance(_sp, tuple)
                        last_progress, last_uploaded, t = _sp
                        fo = None
                    except (KeyError, AssertionError):
                        fo = True
                    if fo or peer.progress < last_progress:
                        last_progress = peer.progress
                        last_uploaded = peer.uploaded
                        t = None
                    elif peer.inactive < 10 and \
                            peer.progress - last_progress < 50 and \
                            (peer.uploaded - last_uploaded) > \
                            (peer.progress - last_progress + 1) * size_millesimal:
                        if t is None:
                            t = ct
                        elif ct - t > time_fp:  # Did not recovered within a few minutes
                            if seeding:
                                reasons.append('Seeding')
                            reasons.append('Progress')
                            t = None
                    else:
                        t = None
                    self._statistics_progress[hash][ip_port] = \
                            last_progress, last_uploaded, t
                if reasons:
                    log(_('report fack progress [%(progress).1f%%]')
                        % {'progress': peer.progress / 10})
                ### Start check client name
                anonymous = False
                if sum(1 if ord(c) < 128 else -1 for c in peer.client) < 0:
                    anonymous = True
                    peer.client = repr(peer.client)  # For better print
                elif peer.port >= 65000 and 'd' in peer.flags and \
                        relevance == 0 and peer.country == 'CN' and \
                        'Transmission' in peer.client:
                    # Chinese Offline Download Servers, almost are leech clients
                    log(_('offline download server'))
                    if reasons and reasons[0] != 'Progress':
                        del reasons[0]
                    reasons.append('Offline')
                elif LEECHER_XUNLEI.search(peer.client):
                    log(_('XunLei'))
                    if not self.xunlei_reprieve or \
                            peer.port in [12345, 15000] or not seeding and (
                            180 < peer.waited < 3600 or
                            peer.downloaded < _1m and peer.relevance == 0 or
                            peer.uploaded > min(size_millesimal, _10m) and (
                            peer.downloaded * 5 < peer.uploaded or
                            peer.downloaded * 10 < relevance)):
                        if reasons and reasons[0] != 'Progress':
                            del reasons[0]
                        reasons.append('XunLei')
                    elif seeding:
                        reasons.append('Seeding')
                        reasons.append('XunLei')
                elif LEECHER_PLAYER.search(peer.client):
                    log(_('player'))
                    if seeding:
                        reasons.append('Seeding')
                        reasons.append('Player')
                    elif peer.uploaded > peer.downloaded and (
                            peer.relevance == 0 or
                            peer.downspeed < 32768 or
                            peer.downspeed * 10 < peer.upspeed):
                        reasons.append('Player')
                elif peer.client.startswith('[FAKE]'):
                    # uTorrent identification
                    # It mistook uTorrent Android versions, so foolish
                    # I would never to feedback this issue to official
                    log(_('fack client'))
                    if seeding:
                        reasons.append('Seeding')
                        reasons.append('Fake')
                    elif peer.downloaded < peer.uploaded > \
                            min(size_millesimal, _10m) and (
                            peer.relevance == 0 or
                            peer.downspeed < 32768 or
                            peer.downspeed * 10 < peer.upspeed):
                        reasons.append('Fake')
                elif LEECHER_OTHER.search(peer.client):
                    log(_('leecher client'))
                    if seeding:
                        reasons.append('Seeding')
                        reasons.append('Leecher')
                    elif peer.uploaded > min(size_millesimal, _10m) and (
                            peer.downloaded * 5 < peer.uploaded or
                            peer.downloaded * 10 < relevance):
                        reasons.append('Leecher')
                ### End check client name
                if self.check_serious_leech or anonymous:
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
                    if not reasons and uploaded and peer.progress < 1000 and (
                            relevance == 0 and peer.uploaded > _500m or
                            peer.relevance == 0 and
                            peer.uploaded > max(peer.downloaded * 10, _1g) or
                            peer.relevance > 0 and
                            ('d' in peer.flags or peer.waited > 60 or
                            0 < peer.downspeed * 100 < peer.upspeed) and
                            uploaded > min(max(size_todl_tenth, _10m), _100m) and
                            uploaded > peer.downloaded * ratio_sl < relevance):
                        if t is None:
                            t = ct
                        elif peer.relevance == 0 or \
                                ct - t > peer.downloaded / _1m * 10:
                            # Did not reached conditions within 10X seconds
                            # X means it had downloaded X MiB from peer
                            log(_('highly suspected of leecher'))
                            reasons.append('Suspected')
                            reasons.append('Leecher')
                            t = None
                    else:
                        t = None
                    self._statistics_uploaded[hash][ip_port] = \
                            luploaded, suploaded, _suploaded, t
                if self.check_refused_upload and \
                        not seeding and peer.downloaded == 0:
                    t = self._statistics_refused[hash].get(ip_port)
                    if reasons:
                        t = None
                    elif t is None:
                        if 'd' in peer.flags:  # Start time counting
                            t = ct
                    elif allow_banned_refused_upload and \
                            ct - t > self.time_allowed_refuse:
                        log(_('refused upload [%(availability).3f]')
                            % {'availability': torrent.availability})
                        reasons.append('Refused')
                        allow_banned_refused_upload = False  # One peer a loop
                        t = None
                    self._statistics_refused[hash][ip_port] = t
                if self.log_unknown and CLIENT_UNKNOWN.search(peer.client):
                    log(_('unknown client'))
                if reasons:
                    try:
                        self.ban_push(hash, peer, ' '.join(reasons))
                    finally:
                        reasons.clear()

    def collect_statistics(self) -> None:
        statistics = self._statistics
        if len(statistics) == 0:
            return
        hashes:list = sum((list(hash.items()) for hash in statistics.values()), [])
        hashes, downloaded, uploaded = zip(*((h, d, u) for h, (d, u) in hashes))
        self._statistics_str = _(
            'Statis: %(ipsc)d IPs, %(torrentsuc)d/%(torrentsc)d Torrents, '
            'D: %(dlsize)s, U: %(ulsize)s') % {
            'ipsc': len(statistics),
            'torrentsuc': len(set(hashes)),
            'torrentsc': len(hashes),
            'dlsize': make_size_human(sum(downloaded)),
            'ulsize': make_size_human(sum(uploaded))
        }

    @property
    def statistics(self) -> str:
        return self._statistics_str[:_max_columns]

    @property
    def log_header(self) -> str:
        return f'{CLL}{time.strftime(self.log_header_fmt, time.localtime())}'

    def log(self, *args, **kwargs) -> None:
        print(self.log_header, *args, **kwargs)

    def run(self, pair=None, show_operations:bool=True) -> None:
        def log(state):
            self.log(_('Auto-banning script %(state)s running') % vars())

        if self.running:
            return
        self.running = True
        disconnected = False
        pause = False
        ss = False
        self.set_setting('bt.use_rangeblock', False)
        self.set_setting('ipfilter.enable', True)
        log(_('start'))
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
                            self.log(_('uTorrent has disconnected'))
                            # Don't clear `self._statistics`
                            self._high_level.clear()
                            self._statistics_started.clear()
                            self._statistics_overflow.clear()
                            self._statistics_progress.clear()
                            self._statistics_uploaded.clear()
                            self._statistics_refused.clear()
                        self.log(_('Unable to connect WebUI: %(url)s')
                                 % {'url': self._url_root}, end='\r')
                        disconnected = err_cr = True
                        time.sleep(10)
                    elif not (disconnected and isinstance(e, HTTPError)):
                        self.log(_('Error occurred: %(error)s, %(url)s')
                                 % {'error': e, 'url': e.filename})
                except Exception as e:
                    logging.exception(_('%(logheader)s Error occurred: %(error)s')
                                      % {'logheader': self.log_header, 'error': e})
                if disconnected and err_cr is None:
                    # Reconnected
                    self.log(_('uTorrent has reconnected'))
                    if isinstance(pair, UTorrentPairing):
                        with pair:
                            # Remove upsell tip in the sidebar
                            pair.set_setting('gui.show_plus_upsell_nodes', False)
                    disconnected = False
            for __ in range(5):
                if show_operations:
                    print(CLL, end='')
                    msgs = [ss and self.statistics or _('Choose your operation: '
                                   '(Q)uit, (S)top, (R)estart, (P)ause/Proceed')]
                    if err_cr:
                        msgs.insert(0, _('DISCONNECTED'))
                    print(*msgs, end='\r')
                    ss = not ss
                    k = get_keyhit()
                    if k is None:
                        pass
                    elif k in b'qQ':
                        log(_('quit'))
                        sys.exit()
                    elif k in b'sS':
                        self.running = False
                        if __name__ == '__main__' or sys.argv[0].endswith(__name__):
                            log(_('quit'))
                        else:
                            log(_('stop'))
                    elif k in b'rR':
                        self.init_ipfilter()
                        self.get_token()
                        self.running = True
                        pause = False
                        log(_('restart'))
                        self.set_setting('ipfilter.enable', True)
                    elif k in b'pP':
                        pause = not pause
                        if pause:
                            log(_('pause'))
                        else:
                            log(_('proceed'))
                time.sleep(2)


class UTorrentPairing:
    def __init__(self, utweb:UTorrentWebAPI, close_pairing:bool=False) -> None:
        self._utweb = utweb
        self._close_pairing = close_pairing
        self._url_root = utweb._url_root.replace('/gui/', '/btapp/')
        self._req = Request(self._url_root)
        self._opener = utweb._opener
        self._pairing:Optional[str] = None
        self._session:Optional[str] = None

    def request(self, params:Mapping[str, str]) -> HTTPResponse:
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

    def get_pairing(self) -> None:
        self._utweb.set_setting('webui.allow_pairing', True)
        try:
            self._pairing = self._utweb.request('pair/',
                                {'name': f'{__app_name__} {__version__}'}
                                ).read().decode('ascii')
        except Exception as e:
            if isinstance(e, HTTPError) and e.code == 401:
                self.log(_('Pairing request has been rejected!'))
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

    def set_setting(self, s:str, v:Union[int, str, bool]) -> None:
        while self._session is None:
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
                self.log(_('set_setting(%(name)r, %(value)s) fail: %(error)s')
                         % {'name': s, 'value': v, 'error': error})
                return
        self.log(_('Set uTorrent setting %(name)r to %(value)s')
                 % {'name': s, 'value': v})

    @property
    def log(self) -> Callable:
        return self._utweb.log

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
            logging.exception(_('%(logheader)s Error occurred: %(error)s')
                              % {'logheader': self.log_header, 'error': value})
        return True  # Make no Exception would be raised


def main(argv=None):
    import inspect
    import argparse
    from . import config

    try:
        tr = translation('argparse')
        argparse._ = tr.gettext
        argparse.ngettext = tr.ngettext
    except (NameError, FileNotFoundError):
        pass

    kwargs = {
        k: v.default
        for k, v in inspect.signature(UTorrentWebAPI.__init__).parameters.items()
        if v.default is not v.empty
    }

    def formatter_class(prog:str, *args, **kwargs) -> argparse.HelpFormatter:
        return argparse.HelpFormatter(prog, indent_increment=4,
                                      max_help_position=20, width=79)

    parser = argparse.ArgumentParser(description=description, add_help=False,
                                     formatter_class=formatter_class)
    parser.add_argument('ipfilter', nargs='?',
                        metavar=_('IPFILTER-PATH'),
                        help=_(
                        'Path of ipfilter dir/file, will try load from config '
                        'file or wait input if empty. IMPORTANT NOTICE: must be '
                        'the uTorrent settings path!'))
    parser.add_argument('-H', '--host', type=str,
                        metavar=_('IP|DOMAIN'),
                        help=_(
                        'WebUI host, default %(host)s') % kwargs)
    parser.add_argument('-p', '--port', type=int,
                        metavar=_('PORT'),
                        help=_(
                        'WebUI port, default %(port)s') % kwargs)
    parser.add_argument('-a', '--authorization', type=str, default='',
                        metavar=_('USERNAME:PASSWORD'),
                        help=_(
                        'WebUI authorization, wait input if required'))
    parser.add_argument('-e', '--expire', type=int,
                        metavar=_('HOURS'),
                        help=_(
                        'Ban expire time for peers, default %(time)s hours')
                        % {'time': kwargs['expire'] // 3600})
    parser.add_argument('-t', '--time-allowed-refuse', type=int,
                        metavar=_('MINUTES'),
                        help=_(
                        'How much time to keep connecting before temporary '
                        'banned refused upload peers, at least 5 minutes, '
                        'default %(time)s minutes')
                        % {'time': kwargs['time_allowed_refuse'] // 60})
    parser.add_argument('-f', '--log-header', type=str,
                        metavar=_('FORMAT'),
                        help=_(
                        'Format of log header, see time.strftime, '
                        'default %(header)s')
                        % {'header': kwargs['log_header_fmt'].replace("%", "%%")})
    parser.add_argument('-C', '--resolve-country',
                        action='store_true',
                        help=_(
                        'Set uTorrent to resolved peer\'s country code '
                        'at start-up'))
    parser.add_argument('-X', '--no-xunlei-reprieve',
                        action='store_true',
                        help=_(
                        'Banned XunLei directly, no more checking'))
    parser.add_argument('-P', '--no-fake-progress-check',
                        action='store_true',
                        help=_(
                        'Don\'t checking fake progress'))
    parser.add_argument('-L', '--no-serious-leech-check',
                        action='store_true',
                        help=_(
                        'Don\'t checking serious leech, except anonymous peers'))
    parser.add_argument('-N', '--no-refused-upload-check',
                        action='store_true',
                        help=_(
                        'Don\'t checking refused upload, this checking is '
                        'useful to connect potential active peers'))
    parser.add_argument('-R', '--private-check',
                        action='store_true',
                        help=_(
                        'Enable checking for private torrents'))
    parser.add_argument('-U', '--log-unknown',
                        action='store_true',
                        help=_(
                        'Logging unknown clients'))
    parser.add_argument('-A', '--remove-ads',
                        action='store_true',
                        help=_(
                        'Remove ads via set Advanced Settings, only working '
                        'for localhost, and to fail in older uTorrent'))
    parser.add_argument('-O', '--no-close-pairing',
                        action='store_true',
                        help=_(
                        'Don\'t turn off Web Pairing setting after'))
    cgroup = parser.add_mutually_exclusive_group()
    cgroup.add_argument('-s', '--save-config', nargs='?', dest='config',
                        type=config.FileType('w'),
                        const=config._default_config_file,
                        metavar=_('CONFIG-FILE'),
                        help=_(
                        'Save current arguments to a config file except '
                        '"--remove-ads", "--help" and "--version". Save to '
                        'default location "%(config)s" if empty input')
                        % {'config': config._default_config_file})
    cgroup.add_argument('-l', '--load-config', nargs='?', dest='config',
                        type=config.FileType('r'),
                        const=config.current_dir_config_file() or
                              config._default_config_file,
                        metavar=_('CONFIG-FILE'),
                        help=_(
                        'Load arguments from a config file, will not overlaid '
                        'the inputted arguments. Load from current directory '
                        '(use conf/ini/cfg as extension name) or default '
                        'location if empty input'))
    parser.add_argument('-h', '--help',
                        action='store_true',
                        help=_(
                        'Show this help message and exit'))
    parser.add_argument('-v', '--version',
                        action='store_true',
                        help=_(
                        'Show version and exit'))
    args = parser.parse_args(argv)

    if args.version:
        print(__app_name__, __version__)
        sys.exit()
    print(_("Welcome using"), __app_name__, __version__)
    if args.help:
        try:
            from . import monkey
            monkey.patch()
        except ImportError:
            pass
        print()
        parser.print_help()
        sys.exit()

    def get_logger(action):
        def log(name, value):
            action
            print(_('%(action)s argument "%(name)s = %(value)s"') % vars())
        return log

    auto_loaded = False
    if args.ipfilter is None and args.config is None:
        print(_('No ipfilter has be inputted, try load from config file'))
        # An automatic try, ignore errors
        parser.error = lambda m: None
        try:
            parser.parse_args(['-l'], args)
        except TypeError:
            pass
        finally:
            auto_loaded = True
    if args.config:
        if args.config.writable():
            print(_('Start saving config file "%(name)s"') % {'name': args.config.name})
            config.save(vars(args), args.config, get_logger(_('Save')))
        else:
            print(_('Start loading config file "%(name)s"') % {'name': args.config.name})
            config.load(vars(args), args.config, get_logger(_('Load')))
        args.config.close()
    if args.ipfilter is None and auto_loaded:
        print(_('Load ipfilter from config file fail, found nothing'))

    if args.host:
        kwargs['host'] = args.host
    if args.port:
        kwargs['port'] = args.port
    if args.authorization.count(':') == 1:
        kwargs['username'], kwargs['password'] = args.authorization.split(':')
    if args.expire:
        kwargs['expire'] = args.expire * 3600
    if args.time_allowed_refuse:
        kwargs['time_allowed_refuse'] = args.time_allowed_refuse * 60
    if args.log_header:
        kwargs['log_header_fmt'] = args.log_header
    if args.no_xunlei_reprieve:
        kwargs['xunlei_reprieve'] = False
    if args.no_fake_progress_check:
        kwargs['check_fake_progress'] = False
    if args.no_serious_leech_check:
        kwargs['check_serious_leech'] = False
    if args.no_refused_upload_check:
        kwargs['check_refused_upload'] = False
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

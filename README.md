# Ban-Peers (English/[中文](https://github.com/SeaHOH/ban-peers/blob/master/README_zh.md))
[![release status](https://img.shields.io/github/v/release/SeaHOH/ban-peers?include_prereleases&sort=semver)](https://github.com/SeaHOH/ban-peers/releases)
[![code size](https://img.shields.io/github/languages/code-size/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers)

Ban-Peers is checking & banning BitTorrent leech peers via Web API, working for μTorrent 3. The main banned are XunLei, Baidu, QQDownload, Offline download servers, other infamous leech clients, and BT players, fake clients, who reported fake progress, the fact in serious leech.

Execute checking per 10 seconds, the banned time can be specified by the start-up parameters, default is 12 hours. In some cases，only banned for 1 hour if the torrent is seeding. At the same time, this script will not broke the existing IP ranges in ipfilter, they will be stored as-is.

**Please use this script in local network**, μTorrent Web API does not support HTTPS connections, it is not safe.

# Installation
Install from 
[![version](https://img.shields.io/pypi/v/ban-peers)](https://pypi.org/project/ban-peers/)
[![package format](https://img.shields.io/pypi/format/ban-peers)](https://pypi.org/project/ban-peers/#files)
[![monthly downloads](https://img.shields.io/pypi/dm/ban-peers)](https://pypi.org/project/ban-peers/#files)

    pip3 install ban-peers

Or download and Install from source code

    python setup.py install

# Compatibility
- Python >= 3.6

# Usage
```
$ ban_peers -h
Welcome using ban_peers 0.1.4

Usage:
        ban_peers       [-H IP|DOMAIN] [-p PORT] [-a USERNAME:PASSWORD]
                        [-e HOURS] [-f FORMAT] [-P] [-L] [-h] [-v]
                        [IPFILTER-PATH]

Checking & banning BitTorrent leech peers via Web API, working for uTorrent 3.

Positional Arguments:
        IPFILTER-PATH   Path of ipfilter dir/file, wait input if empty.
                        IMPORTANT NOTICE: must be the uTorrent setting path!

Optional Arguments:
        -H IP|DOMAIN, --host IP|DOMAIN
                        WebUI host, default 127.0.0.1
        -p PORT, --port PORT
                        WebUI port, default 8080
        -a USERNAME:PASSWORD, --authorization USERNAME:PASSWORD
                        WebUI authorization, wait input if required
        -e HOURS, --expire HOURS
                        Ban expire time for peers, default 12 HOURS
        -f FORMAT, --log-header FORMAT
                        Format of log header, default %H:%M:%S
        -P, --no-fake-progress-check
                        Don't checking fake progress
        -L, --no-serious-leech-check
                        Don't checking serious leech
        -h, --help      Show this help message and exit
        -v, --version   Show version and exit
```

```
$ ban_peers ~/utorrent -p 12345 -a username:password
Welcome using ban_peers 0.1.4
19:44:35 uTorrent auto-banning script start running
Choose your operation: (Q)uit, (S)top, (R)estart, (P)ause/Proceed
```

or

```
$ ban-peers
Welcome using ban_peers 0.1.4
Please input uTorrent setting folder path or ipfilter file path:
~/utorrent
Please input WebUI username: username
Please input WebUI password: password  # No cover
19:44:35 uTorrent auto-banning script start running
Choose your operation: (Q)uit, (S)top, (R)estart, (P)ause/Proceed
```

- Quit: exit the script.
- Stop: same as Quit if run script direct, or stop checking.
- Restart: reload ipfilter, it is useful when manually modify ipfilter.
- Pause: pause checking, it is useful when manually modify ipfilter.
- Proceed: just proceed checking.

# Related projects
- μTorrent

    https://github.com/ShenHongFei/utorrent-block-xunlei  
    https://github.com/iHamsterball/utorrent_block_thunder  

- qBittorrent

    https://github.com/c0re100/qBittorrent-Enhanced-Edition  
    https://github.com/originqtum/banned-xunlei-for-qbittorrent  
    https://github.com/jinliming2/qbittorrent-ban-xunlei  
    https://github.com/Od1gree/btDownloadManager  
    https://github.com/outline941/qb-ban-xunlei  

# Thanks
[c0re100](https://github.com/c0re100/qBittorrent-Enhanced-Edition)  
[ShenHongFei](https://github.com/ShenHongFei/utorrent-block-xunlei)  

# License
Ban-Peers is released under the [![license](https://img.shields.io/github/license/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers/blob/master/LICENSE).

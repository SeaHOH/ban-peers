# Ban-Peers (English/[中文](https://github.com/SeaHOH/ban-peers/blob/master/README_zh.md))
[![release status](https://img.shields.io/github/v/release/SeaHOH/ban-peers?include_prereleases&sort=semver)](https://github.com/SeaHOH/ban-peers/releases)
[![code size](https://img.shields.io/github/languages/code-size/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers)

Ban-Peers wrote in Python, it is checking & banning BitTorrent leech peers via
Web API, remove ads, working for μTorrent. The main banned are XunLei, Baidu,
QQDownload, Offline download servers, other infamous leech clients, and BT
players, fake clients, who reported fake progress, the fact in serious leech.

Execute checking per 10 seconds, the banned time can be specified by the start-up
parameters, default is 12 hours. In some cases, temporary banned for 1 hour if
the torrent is seeding. Also can temporary banned peers which refused upload
10 minutes in downloading torrents if AVAILABILITY greater than 10. At the same
time, this script will not broke the existing IP ranges (non-single IP) in
ipfilter, they will be stored as-is.

[A gift](https://github.com/SeaHOH/ban-peers/issues/1) to the users of
μTorrent 3 classic desktop free version, it wrote in Chinese, you can read via
a translator. e.g. translate.google.com

Resist leech strongly, this is our own rights. If you feels Ban-Peers a good
work, please recommend it to your friends, Thanks.

# Notices
- Does not work in old versions of μTorrent which did not provided API `getpeers`.
- **Please use this script in local network**, μTorrent Web API does not
  support HTTPS connections, it is not safe.
- If you can not accept read/write the ipfilter.dat file frequently, it can be
  soft/symbolic link to a RAM disk.
- I took preventive measures, if you stiil found a normal peer has been banned,
  please tell us via [issues board](https://github.com/SeaHOH/ban-peers/issues).

# Installation
Install from 
[![version](https://img.shields.io/pypi/v/ban-peers)](https://pypi.org/project/ban-peers/)
[![package format](https://img.shields.io/pypi/format/ban-peers)](https://pypi.org/project/ban-peers/#files)
[![monthly downloads](https://img.shields.io/pypi/dm/ban-peers)](https://pypi.org/project/ban-peers/#files)

    pip3 install ban-peers

Or download and Install from source code, this will install as egg archive

    python setup.py install

Or download and package into .pyz (Zip App), support three arguments of zipapp
module (output/python/compress)

    python setup.py bdist_pyz -compress

    python setup.py bdist_pyz -compress -output ban_peers -python python38

# Compatibility
- Python >= 3.7
- Zip safe
- Support call with `python -m`
- Support I18N，welcome [helps localization](https://github.com/SeaHOH/ban-peers/blob/master/src/ban_peers/i18n/locale)

# Usage
First, Web UI must be enabled in μTorrent settings; then running Ban-Peers for
specified ipfilter.dat file.

Setting file ipfilter.dat, it is generally located in the path corresponding to
the following cases.
```
Mac:
        ~/Library/Application Support/uTorrent
        or
        /Applications/uTorrent.app/Contents/MacOS
Unix utserver:
        use utserver argument "-settingspath" to specify settings folder path.
Win XP:
        C:\Documents and Settings\<username>\Application Data\uTorrent
Win 7 & above:
        C:\Users\<username>\AppData\Roaming\uTorrent
Portable mode:
        μTorrent installation folder path. To enable this mode, first put file
        settings.dat into it.
PortableApps:
        <PortableApps folder>\App\uTorrent
Android:
        I don't know any informations about it, welcome to help add those informations,
        even Android is unavailable.
Network File:
        run μTorrent at other machine, setup the settings folder as a network file path.
        e.g.
        NFS       mount –t nfs 192.168.1.20:/var/lib/utserver /mnt/utserver
                  /mnt/utserver
        SMB/CIFS  //machine1/share/uTorrent
```

```
$ ban_peers -h
Welcome using Ban-Peers 0.9.2

usage: ban_peers.pyz [-H IP|DOMAIN] [-p PORT] [-a USERNAME:PASSWORD] [-e HOURS]
                     [-t MINUTES] [-f FORMAT] [-C] [-X] [-P] [-L] [-N] [-R]
                     [-U] [-A] [-O] [-s [CONFIG-FILE] | -l [CONFIG-FILE]] [-h]
                     [-v]
                     [IPFILTER-PATH]

Checking & banning BitTorrent leech peers via Web API, remove ads, working for
uTorrent.

Positional Arguments:
    IPFILTER-PATH   Path of ipfilter dir/file, will try load from config file
                    or wait input if empty. IMPORTANT NOTICE: must be the
                    uTorrent settings path!

Optional Arguments:
    -H IP|DOMAIN, --host IP|DOMAIN
                    WebUI host, default 127.0.0.1
    -p PORT, --port PORT
                    WebUI port, default 8080
    -a USERNAME:PASSWORD, --authorization USERNAME:PASSWORD
                    WebUI authorization, wait input if required
    -e HOURS, --expire HOURS
                    Ban expire time for peers, default 12 hours
    -t MINUTES, --time-allowed-refuse MINUTES
                    How much time to keep connecting before temporary banned
                    refused upload peers, at least 5 minutes, default 10
                    minutes
    -f FORMAT, --log-header FORMAT
                    Format of log header, see time.strftime, default %H:%M:%S
    -C, --resolve-country
                    Set uTorrent to resolved peer's country code at start-up
    -X, --no-xunlei-reprieve
                    Banned XunLei directly, no more checking
    -P, --no-fake-progress-check
                    Don't checking fake progress
    -L, --no-serious-leech-check
                    Don't checking serious leech, except anonymous peers
    -N, --no-refused-upload-check
                    Don't checking refused upload, this checking is useful to
                    connect potential active peers
    -R, --private-check
                    Enable checking for private torrents
    -U, --log-unknown
                    Logging unknown clients
    -A, --remove-ads
                    Remove ads via set Advanced Settings, only working for
                    localhost, and to fail in older uTorrent
    -O, --no-close-pairing
                    Don't turn off Web Pairing setting after
    -s [CONFIG-FILE], --save-config [CONFIG-FILE]
                    Save current arguments to a config file except "--remove-
                    ads", "--help" and "--version". Save to default location
                    "<YOUR CONFIG DIR>/BanPeers/ban_peers.conf" if empty input
    -l [CONFIG-FILE], --load-config [CONFIG-FILE]
                    Load arguments from a config file, will not overlaid the
                    inputted arguments. Load from current directory (use
                    conf/ini/cfg as extension name) or default location if
                    empty input
    -h, --help      Show this help message and exit
    -v, --version   Show version and exit
```

```markdown
$ ban-peers
Welcome using Ban-Peers 0.9.2
No ipfilter has be inputted, try load from config file
Load ipfilter from config file fail, found nothing
Please input uTorrent settings folder path or ipfilter file path:
/var/lib/utserver
Please input WebUI username: username
Please input WebUI password: password  **_No cover_**
19:44:33 Set uTorrent setting 'webui.allow_pairing' to True
19:44:35 Set uTorrent setting 'gui.show_plus_upsell_nodes' to False  **_Remove upsell tip in the sidebar_**
19:44:35 Set uTorrent setting 'webui.allow_pairing' to False  **_disallow pairing_**
19:44:35 Set uTorrent setting 'bt.use_rangeblock' to False  **_Won't restore after quit_**
19:44:35 Set uTorrent setting 'ipfilter.enable' to True
19:44:35 Auto-banning script start running
Choose your operation: (Q)uit, (S)top, (R)estart, (P)ause/Proceed
19:44:36 Auto-banning script quit running
...

...
$ ban_peers -p 12345 -a username:password /var/lib/utserver --save-config
Welcome using Ban-Peers 0.9.2
Start saving config file "<YOUR CONFIG DIR>/BanPeers/ban_peers.conf"
Save argument "ipfilter = /var/lib/utserver"
Save argument "port = 12345"
Save argument "authorization = username:password"
...

...
$ ban-peers -p 54321
Welcome using Ban-Peers 0.9.2
No ipfilter has be inputted, try load from config file
Start loading config file "<YOUR CONFIG DIR>/BanPeers/ban_peers.conf"
Load argument "ipfilter = /var/lib/utserver"
**_Doesn't load inputted argument port_**
Load argument "authorization = username:password"
...
```

- Quit: exit the script.
- Stop: stop checking if run script via import as package, or same as Quit.
- Restart: reload ipfilter.dat, it is useful when manually modify ipfilter.dat.
- Pause: pause checking, it is useful when manually modify ipfilter.dat.
- Proceed: just proceed checking.

# Got troubles/ideas
Visit the [issues board](https://github.com/SeaHOH/ban-peers/issues) and post
them, maybe someone can help you.

# What μTorrent settings should have been modified
- Global

    **bt.use_rangeblock**, using this tool, build-in range block (by hash error)
    should be disabled.  
    `False` when start-up

    **ipfilter.enable**, enable/flush ipfilter.  
    `True` when start-up, adding banned

    **webui.allow_pairing**, modify more settings have to got pairing, μTorrent
                             will show a pop-up of pairing request, please
                             confirm carefully.  
    `True` before modify ads settings  
    `False` after modify ads settings, can also use parameters `-O` or
            `--no-close-pairing` to do not disable it

    **gui.show_plus_upsell_nodes**, μTorrent sidebar upgrade tips will be reset
                                    at start-up.  
    `True` when start-up, μTorrent re-started

    **peer.resolve_country, resolve_peerips**, resolve country code of peer IPs.  
    `True` when start-up，need to use parameters `-C` or `--resolve-country`,
           not every time

    **Other ads settings**, modify some settings have to got pairing.  
    For specific values see the part of `ANTI_ADS_SETTINGS` in source code, when
    start-up, modify all settings at once after got pairing, need to use
    parameters `-A` or `--remove-ads`, not every time

- Torrent

    **ulrate**, for older/weaker Torrents (in terms of E.T.A, less than
                10 GiB/day), limit its upload rate helps complete download, and
                increase read cache hits in passing.  
    `1048576` download size less than 1 GiB, limit to 1 MiB/s  
    `524288` download size less than 10 GiB, limit to 512 KiB/s

# Related projects
- μTorrent

    https://github.com/ShenHongFei/utorrent-block-xunlei  
    https://github.com/iHamsterball/utorrent_block_thunder  
    https://github.com/isimonov/disable-uTorrent-ads  
    https://github.com/SchizoDuckie/PimpMyuTorrent  

- qBittorrent

    https://github.com/c0re100/qBittorrent-Enhanced-Edition  
    https://github.com/originqtum/banned-xunlei-for-qbittorrent  
    https://github.com/jinliming2/qbittorrent-ban-xunlei  
    https://github.com/Od1gree/btDownloadManager  
    https://github.com/outline941/qb-ban-xunlei  

# Thanks
[c0re100](https://github.com/c0re100/qBittorrent-Enhanced-Edition)  
[ShenHongFei](https://github.com/ShenHongFei/utorrent-block-xunlei)  
[isimonov](https://github.com/isimonov/disable-uTorrent-ads)  
[SchizoDuckie](https://github.com/SchizoDuckie/PimpMyuTorrent)  

# License
Ban-Peers is released under the [![license](https://img.shields.io/github/license/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers/blob/master/LICENSE).

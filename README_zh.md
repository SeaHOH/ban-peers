# Ban-Peers ([English](https://github.com/SeaHOH/ban-peers/blob/master/README.md)/中文)
[![release status](https://img.shields.io/github/v/release/SeaHOH/ban-peers?include_prereleases&sort=semver)](https://github.com/SeaHOH/ban-peers/releases)
[![code size](https://img.shields.io/github/languages/code-size/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers)

这是一个用 Python 写的工具，通过网页 API 检查并屏蔽 BitTorrent 吸血对端，移除广告，
工作于 μTorrent。主要屏蔽迅雷、百毒、QQ、离线下载服务器等臭名昭著的吸血客户端，
还有 BT 播放器、假冒客户端、虚假进度，以及事实上的严重吸血对端。

每 10 秒进行一次检查，屏蔽时间可以由启动参数指定，默认为 12 小时。屏蔽吸血并不是
一刀切完全屏蔽，个别会有回传且处于容忍度以内，这时不会马上屏蔽它。这是个反向吸血
措施，如果此下载在本机处于做种状态，那么就会马上屏蔽它们，其中判断为恶性吸血的
仍然屏蔽 12 小时，无法确定的则只临时屏蔽 1 小时。还可临时屏蔽下载状态任务中拒绝
上传 10 分钟的对端，如果健康度大于 10。同时，此脚本不会影响已有的 ipfilter 范围
格式屏蔽 (非单 IP 格式)，它们会被原样保存。

给 μTorrent 3 经典桌面版免费版本用户的[一份礼物](https://github.com/SeaHOH/ban-peers/issues/1)。

极力抵制吸血，这是我们应有的权利。如果你觉得 Ban-Peers 还不错，请向朋友推荐它，谢谢。

# 注意事项
- 无法在未提供 `getpeers` API 的旧版本 μTorrent 中正常工作。
- **请在本地网络内使用此脚本**，μTorrent 网页 API 不支持 HTTPS 连接，它并不安全。
- 如果无法接受频繁读写 ipfilter.dat 文件，可以将它软链接到内存盘。
- 虽然已采取一些预防措施，如果你仍然发现有正常的对端被错误屏蔽，
  请反馈到 [issues 板块](https://github.com/SeaHOH/ban-peers/issues)。

# 安装
安装自
[![version](https://img.shields.io/pypi/v/ban-peers)](https://pypi.org/project/ban-peers/)
[![package format](https://img.shields.io/pypi/format/ban-peers)](https://pypi.org/project/ban-peers/#files)
[![monthly downloads](https://img.shields.io/pypi/dm/ban-peers)](https://pypi.org/project/ban-peers/#files)

    pip3 install ban-peers

或者下载源码安装，这样将安装成 egg 包

    python setup.py install

或者下载源码打包成 .pyz (Zip App)，支持三个 zipapp 模块参数 (output/python/compress)

    python setup.py bdist_pyz -compress

    python setup.py bdist_pyz -compress -output ban_peers -python python38

# 兼容性
- Python >= 3.7
- Zip 安全
- 支持 `python -m` 调用
- 支持 I18N，欢迎[参与本地化](https://github.com/SeaHOH/ban-peers/blob/master/src/ban_peers/i18n/locale)

# 使用
首先，必须在 μTorrent 设置中启用网页界面；然后运行 Ban-Peers 于指定的 ipfilter.dat 文件。

IP 屏蔽配置文件 ipfilter.dat，其通常位于以下几种情况对应的路径。
```
Mac:
        ~/Library/Application Support/uTorrent
        或
        /Applications/uTorrent.app/Contents/MacOS
Unix utserver:
        使用 utserver 参数 "-settingspath" 指定配置文件夹路径。
Win XP:
        C:\Documents and Settings\<用户名>\Application Data\uTorrent
Win 7 及以上:
        C:\Users\<用户名>\AppData\Roaming\uTorrent
便携模式:
        μTorrent 安装文件夹路径。要启用此模式，先把 settings.dat 文件放入其中。
PortableApps:
        <PortableApps 文件夹>\App\uTorrent
Android:
        我不知道相关的一切信息，欢迎帮助补充此信息，包括 Android 可能是不适用的。
网络文件:
        在其它设备上运行 μTorrent，并配置其配置文件夹为网络路径。
        例如
        SMB/CIFS  //machine1/share/uTorrent
        NFS       mount –t nfs 192.168.1.20:/var/lib/utserver /mnt/utserver
                  /mnt/utserver
```

```
ban_peers -h
欢迎使用 Ban-Peers 0.9.2

用 法: ban_peers.pyz [-H IP|域名] [-p 端口] [-a 用户名:密码] [-e 小时]
                     [-t 分钟] [-f 格式] [-C] [-X] [-P] [-L] [-N] [-R] [-U]
                     [-A] [-O] [-s [配置文件] | -l [配置文件]] [-h] [-v]
                     [IP屏蔽配置路径]

通过网页 API 检查并屏蔽 BitTorrent 吸血对端，移除广告，工作于 uTorrent。

位置参数:
    IP屏蔽配置路径  ipfilter 目录或文件路径，留空将尝试从配置文件加载，或等待输
                    入。重要提示: 必须是 uTorrent 配置使用的路径!

可选参数:
    -H IP|域名, --host IP|域名
                    网页界面的主机，默认 127.0.0.1
    -p 端口, --port 端口
                    网页界面的端口，默认 8080
    -a 用户名:密码, --authorization 用户名:密码
                    网页界面的授权，如果需要将等待输入
    -e 小时, --expire 小时
                    屏蔽对端的过期时间，默认 12 小时
    -t 分钟, --time-allowed-refuse 分钟
                    临时屏蔽拒绝上传的对端前保持连接的时间，最少 5 分钟，默认
                    10 分钟
    -f 格式, --log-header 格式
                    日志头格式，参见 time.strftime，默认 %H:%M:%S
    -C, --resolve-country
                    启动时，设置 uTorrent 解析对端国家代码
    -X, --no-xunlei-reprieve
                    直接屏蔽迅雷，不进行更多的检查
    -P, --no-fake-progress-check
                    不进行虚假进度检查
    -L, --no-serious-leech-check
                    不进行严重吸血检查，匿名对端除外
    -N, --no-refused-upload-check
                    不进行拒绝上传检查，此检查有助于连接潜在的活跃对端
    -R, --private-check
                    启用对私有种子的检查
    -U, --log-unknown
                    将未知客户端记入日志
    -A, --remove-ads
                    通过高级设置移除广告，仅工作于本地主机，也无法工作于较旧版
                    本的 uTorrent
    -O, --no-close-pairing
                    移除广告后，不关闭网络配对配置项
    -s [配置文件], --save-config [配置文件]
                    保存当前参数到一个配置文件，不包括 "--remove-ads"、"--help"
                    和 "--version"，如果输入留空则保存到默认位置 "<你的配置目录>
                    \BanPeers\ban_peers.conf"
    -l [配置文件], --load-config [配置文件]
                    从一个配置文件加载参数，不会覆盖已输入的参数，如果输入留空
                    则尝试从当前目录 (使用 conf/ini/cfg 作为扩展名) 或默认位置
                    加载
    -h, --help      显示此帮助信息并退出
    -v, --version   显示版本信息并退出
```

```markdown
C:\Users\username>ban_peers
欢迎使用 Ban-Peers 0.9.2
没有输入 ipfilter，尝试从配置文件加载
从配置文件加载 ipfilter 失败，什么都没有找到
请输入 uTorrent 配置文件夹路径，或者 ipfilter 文件路径:
X:\uTorrent
请输入 WebUI 用户名: username
请输入 WebUI 密码: password  **_没有遮掩_**
19:44:33 设定 uTorrent 配置 'webui.allow_pairing' 到 True  **_允许配对_**
19:44:35 设定 uTorrent 配置 'gui.show_plus_upsell_nodes' 到 False  **_移除侧栏付费版升级提示_**
19:44:35 设定 uTorrent 配置 'webui.allow_pairing' 到 False  **_禁止配对_**
19:44:35 设定 uTorrent 配置 'bt.use_rangeblock' 到 False  **_脚本退出后不会自动恢复_**
19:44:35 设定 uTorrent 配置 'ipfilter.enable' 到 True
19:44:35 uTorrent 自动屏蔽脚本开始运行
请选择你要执行的操作: (Q)退出，(S)停止，(R)重新开始，(P)暂停/恢复
19:44:36 自动屏蔽脚本退出运行
...

...
C:\Users\username>ban_peers -p 12345 -a username:password X:\uTorrent --save-config
欢迎使用 Ban-Peers 0.9.2
开始保存配置文件 "<你的配置目录>\BanPeers\ban_peers.conf"
保存参数 "ipfilter = X:\uTorrent"
保存参数 "port = 12345"
保存参数 "authorization = username:password"
...

...
C:\Users\username>ban_peers -p 54321
欢迎使用 Ban-Peers 0.9.2
没有输入 ipfilter，尝试从配置文件加载
开始保存配置文件 "<YOUR CONFIG DIR>\BanPeers\ban_peers.conf"
加载参数 "ipfilter = X:\uTorrent"
**_没有加载已输入的 port 参数_**
加载参数 "authorization = username:password"
...
```

- 退出：退出此脚本。
- 停止：如果是通过导入模块方式运行此脚本，只是停止检查，否则等同退出。
- 重新开始：重新加载 ipfilter.dat，对于手动修改 ipfilter.dat 非常有用。
- 暂停：暂停检查，对于手动修改 ipfilter.dat 非常有用。
- 恢复：只是恢复检查。

# 遇到麻烦/有其它想法
访问 [issues 板块](https://github.com/SeaHOH/ban-peers/issues)并贴出它们，
也许有人能够帮到你。

# 修改了哪些 μTorrent 配置
- 全局

    **bt.use_rangeblock**，使用此工具时，可停用内建自动范围屏蔽 (根据校验错误)。  
    `False` 启动时

    **ipfilter.enable**，启用/刷新 ipfilter。  
    `True` 启动时、添加屏蔽时

    **webui.allow_pairing**，配对后可修改更多配置，μTorrent 会弹出配对请求窗口，
    请仔细确认。  
    `True` 修改广告配置前  
    `False` 修改完成后禁用，也可以使用参数 `-O` 或 `--no-close-pairing` 不禁用

    **gui.show_plus_upsell_nodes**，μTorrent 启动时会重置侧栏升级提示。  
    `True` 启动时、μTorrent 重启后

    **peer.resolve_country, resolve_peerips**，解析对端 IP 所属国家代码。  
    `True` 启动时，需使用参数 `-C` 或 `--resolve-country`，无需每次都使用

    **其它广告配置**，部分配置的修改需要配对。  
    具体值参见源代码的 `ANTI_ADS_SETTINGS` 部分，启动时，统一在配对后修改，需使用
    参数 `-A` 或 `--remove-ads`，无需每次都使用

- Torrent

    **ulrate**，对于旧的、健康度差的 Torrent (以剩余完成时间计，少于 10 GiB/天)，
    限制其上传速度有助于完成下载，顺带可提高读取缓存命中。  
    `1048576` 下载大小大于 1 GiB，限制 1 MiB/s  
    `524288` 下载大小大于 10 GiB，限制 512 KiB/s

# 相关项目
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

# 感谢
[c0re100](https://github.com/c0re100/qBittorrent-Enhanced-Edition)  
[ShenHongFei](https://github.com/ShenHongFei/utorrent-block-xunlei)  
[isimonov](https://github.com/isimonov/disable-uTorrent-ads)  
[SchizoDuckie](https://github.com/SchizoDuckie/PimpMyuTorrent)  

# License
Ban-Peers 以 [![license](https://img.shields.io/github/license/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers/blob/master/LICENSE) 许可发布。

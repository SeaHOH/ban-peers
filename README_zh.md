# Ban-Peers ([English](https://github.com/SeaHOH/ban-peers/blob/master/README.md)/中文)
[![release status](https://img.shields.io/github/v/release/SeaHOH/ban-peers?include_prereleases&sort=semver)](https://github.com/SeaHOH/ban-peers/releases)
[![code size](https://img.shields.io/github/languages/code-size/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers)

通过网页 API 检查并屏蔽 BitTorrent 吸血对端, 工作于 μTorrent 3。主要屏蔽迅雷、百毒、QQ、离线下载服务器等臭名昭著的吸血客户端，还有 BT 播放器、假冒客户端、虚假进度，以及事实上的严重吸血对端。

每 10 秒进行一次检查，屏蔽时间可以由启动参数指定，默认为 12 小时。屏蔽吸血并不是一刀切完全屏蔽，个别会有回传且处于容忍度以内，这时不会马上屏蔽它。这是个反吸血措施，如果此下载在本机处于做种状态，那么就会马上屏蔽它们，其中判断为恶性吸血的仍然屏蔽 12 小时，无法确定的则只屏蔽 1 小时。同时，此脚本不会影响已有的 ipfilter 范围格式屏蔽，它们会被原样保存。

**请在本地网络内使用此脚本**，μTorrent 网页 API 不支持 HTTPS 连接，它并不安全。

# 安装
安装自
[![version](https://img.shields.io/pypi/v/ban-peers)](https://pypi.org/project/ban-peers/)
[![package format](https://img.shields.io/pypi/format/ban-peers)](https://pypi.org/project/ban-peers/#files)
[![monthly downloads](https://img.shields.io/pypi/dm/ban-peers)](https://pypi.org/project/ban-peers/#files)

    pip3 install ban-peers

或者下载源码安装

    python setup.py install

# 兼容性
- Python >= 3.6

# 使用
```
ban_peers -h

用法:
       ban_peers       [-h] [-H IP|域名] [-p 端口] [-a 用户名:密码] [-e 小时]
                       [-f 格式] [IP屏蔽配置路径]

通过网页 API 检查并屏蔽 BitTorrent 吸血对端, 工作于 uTorrent 3。

位置参数:
       IP屏蔽配置路径  ipfilter 目录或文件路径, 留空将等待输入。重要提示:
                       必须是 uTorrent 配置使用的路径!

可选参数:
       -h, --help      显示此帮助信息并退出
       -H IP|域名, --host IP|域名
                       网页界面的主机, 默认 127.0.0.1
       -p 端口, --port 端口
                       网页界面的端口, 默认 8080
       -a 用户名:密码, --authorization 用户名:密码
                       网页界面的授权, 如果需要将等待输入
       -e 小时, --expire 小时
                       屏蔽对端的过期时间, 默认 12 小时
       -f 格式, --log-header 格式
                       日志头格式, 默认 %H:%M:%S
```

```
ban_peers X:\utorrent -p 12345 -a username:password
19:44:35 uTorrent 自动屏蔽脚本开始运行
请选择你要执行的操作: (Q)退出, (S)停止, (R)重新开始, (P)暂停/恢复
```

或者

```
ban_peers
请输入 uTorrent 配置文件夹路径，或者 ipfilter 文件路径:
X:\utorrent
请输入 WebUI 用户名: username
请输入 WebUI 密码: password  # 没有遮掩
19:44:35 uTorrent 自动屏蔽脚本开始运行
请选择你要执行的操作: (Q)退出, (S)停止, (R)重新开始, (P)暂停/恢复
```

- 退出：退出此脚本。
- 停止：如果是直接运行此脚本，则等同退出，否则只是停止检查。
- 重新开始：重新加载 ipfilter，对于手动修改 ipfilter 非常有用。
- 暂停：暂停检查，对于手动修改 ipfilter 非常有用。
- 恢复：只是恢复检查。

# 感谢
https://github.com/c0re100/qBittorrent-Enhanced-Edition
https://github.com/ShenHongFei/utorrent-block-xunlei

# License
Ban-Peers 以 [![license](https://img.shields.io/github/license/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers/blob/master/LICENSE) 许可发布。

# Ban-Peers ([English](https://github.com/SeaHOH/ban-peers/blob/master/README.md)/中文)
[![release status](https://img.shields.io/github/v/release/SeaHOH/ban-peers?include_prereleases&sort=semver)](https://github.com/SeaHOH/ban-peers/releases)
[![code size](https://img.shields.io/github/languages/code-size/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers)

通过网页 API 检查并屏蔽 BitTorrent 吸血对端, 工作于 uTorrent 3。

请在本地网络内使用此脚本，uTorrent 网页 API 不支持 HTTPS 连接。

# 安装
安装自
[![version](https://img.shields.io/pypi/v/ban-peers)](https://pypi.org/project/ban-peers/)
[![package format](https://img.shields.io/pypi/format/ban-peers)](https://pypi.org/project/ban-peers/#files)
[![monthly downloads](https://img.shields.io/pypi/dm/ban-peers)](https://pypi.org/project/ban-peers/#files)

    pip install ban-peers

或者下载源码安装

    python setup.py install

# 兼容性
- Python >= 3.6

# 使用
```
X:\ban-peers>ban_peers.py -h

用法:
       ban_peers.py [-h] [-H IP|域名] [-p 端口] [-a 用户名:密码] [-e 小时]
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
X:\ban-peers>ban_peers.py X:\utorrent -p 12345 -a username:password
19:44:35 uTorrent 自动屏蔽脚本开始运行
请选择你要执行的操作: (Q)退出, (S)停止, (R)重新开始, (P)暂停/恢复
```

or

```
X:\ban-peers>ban_peers.py
请输入 uTorrent 配置文件夹路径，或者 ipfilter 文件路径:
X:\utorrent
请输入 WebUI 用户名: username
请输入 WebUI 密码: password  # 没有遮掩
19:44:35 uTorrent 自动屏蔽脚本开始运行
请选择你要执行的操作: (Q)退出, (S)停止, (R)重新开始, (P)暂停/恢复
```

# License
Ban-Peers 以 [![license](https://img.shields.io/github/license/SeaHOH/ban-peers)](https://github.com/SeaHOH/ban-peers/blob/master/LICENSE) 许可发布。

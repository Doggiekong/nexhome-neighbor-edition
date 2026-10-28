#!/bin/sh
set -eu
source_url=https://github.com/Doggiekong/nexhome-neighbor-edition/releases/download/v0.1.0
fixture=
protocols='=https'
if [ "$#" -eq 2 ] && [ "$1" = --fixture-source ]; then
  source_url=$2
  fixture=--fixture
  protocols='=http,https'
elif [ "$#" -ne 0 ]; then
  echo '启动参数不符合固定入口，请复制完整命令。' >&2
  exit 2
fi
command -v python3 >/dev/null || { echo '请在运行HA的Linux/NAS终端执行；当前没有Python3。'; exit 2; }
command -v curl >/dev/null || { echo '当前终端没有curl，请让本机管理员准备基础下载工具。'; exit 2; }
work=$(mktemp -d)
trap 'rm -f "$work/terminal.py"; rmdir "$work"' EXIT HUP INT TERM
curl -fsSL --proto "$protocols" --proto-redir '=https' --max-redirs 3 --connect-timeout 10 --max-time 60 "$source_url/terminal.py" -o "$work/terminal.py"
echo 'd3800351106a24868dcb12b080cccb66a847e280544058c29fde94e4eb76d2b8  '"$work/terminal.py" | sha256sum -c - >/dev/null || { echo '启动器校验不一致，停止。'; exit 2; }
python3 "$work/terminal.py" --source "$source_url" $fixture

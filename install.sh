#!/usr/bin/env bash
# Download this file, then run it with sudo bash install.sh.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo '请使用 sudo bash install.sh 或 root 运行。' >&2; exit 1; }
[[ -r /dev/tty ]] || { echo '请在交互式 SSH 终端运行。' >&2; exit 1; }
# shellcheck disable=SC1091
source /etc/os-release
# shellcheck disable=SC2154
case "$ID" in ubuntu|debian) ;; *) echo '自动安装支持 Ubuntu / Debian。' >&2; exit 1 ;; esac
case "$(uname -m)" in x86_64|aarch64) ;; *) echo '应用镜像支持 amd64 / arm64。' >&2; exit 1 ;; esac
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git openssl python3 util-linux
target=/opt/vps-monitoring-stack
if [[ -e "$target" ]]; then
  [[ -d "$target/.git" ]] || { echo "$target 已存在且不是项目仓库，请先处理。" >&2; exit 1; }
  [[ "$(git -C "$target" remote get-url origin)" == 'https://github.com/zangwp/vps-monitoring-stack.git' ]] || exit 1
  git -C "$target" diff --quiet
  git -C "$target" diff --cached --quiet
  git -C "$target" pull --ff-only
else
  git clone https://github.com/zangwp/vps-monitoring-stack.git "$target"
fi
exec bash "$target/scripts/setup.sh"

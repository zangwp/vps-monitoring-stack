#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ $EUID -eq 0 ]] || { echo '请使用 root 或 sudo 运行。' >&2; exit 1; }
if ! command -v docker >/dev/null; then
  # shellcheck disable=SC1091
  source /etc/os-release
  # shellcheck disable=SC2154
  case "$ID" in ubuntu|debian) ;; *) exit 1 ;; esac
  for package in docker.io podman-docker containerd runc; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
      echo "检测到 $package，请先按 Docker 官方说明处理安装冲突。不会自动卸载。" >&2
      exit 1
    fi
  done
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker-monitoring.asc
  chmod a+r /etc/apt/keyrings/docker-monitoring.asc
  # Variables below come from /etc/os-release.
  # shellcheck disable=SC2154
  cat > /etc/apt/sources.list.d/docker-monitoring.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/$ID
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker-monitoring.asc
EOF
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi
docker info >/dev/null || { echo 'Docker 无法连接，请检查服务状态。' >&2; exit 1; }
docker compose version >/dev/null || { echo '已有 Docker 缺少 Compose v2，请安装插件后重试。' >&2; exit 1; }
bash scripts/init.sh
python3 scripts/configure.py
bash scripts/deploy.sh
echo '安装完成。请立即完成 Komari 初始化，并修改 Umami 默认 admin / umami 密码。'
echo '项目目录：/opt/vps-monitoring-stack；备份：sudo bash /opt/vps-monitoring-stack/scripts/backup.sh'

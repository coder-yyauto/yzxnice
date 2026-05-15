#!/bin/bash

set -e

echo "=== 初始化 yzxnice 项目 ==="

# 检测操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        EXT="osx-64"
        PLAT="osx-64"
    else
        EXT="osx-64"
        PLAT="osx-64"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    ARCH=$(uname -m)
    if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
        EXT="linux-aarch64"
        PLAT="linux-aarch64"
    else
        EXT="linux-64"
        PLAT="linux-64"
    fi
else
    echo "不支持的操作系统: $OSTYPE"
    exit 1
fi

echo "检测到操作系统: $OS ($EXT)"

# 设置安装目录
LOCAL_BIN="$HOME/.local/bin"
MAMBA_ROOT="$HOME/.mamba"

# 检测 micromamba
if command -v micromamba &> /dev/null; then
    echo "micromamba 已安装: $(micromamba --version)"
    MICROMAMBA_CMD="micromamba"
else
    echo "正在安装 micromamba..."

    # 从官方 API 获取最新版本
    case "$PLAT" in
        linux-64)
            DOWNLOAD_URL="https://micro.mamba.pm/api/micromamba/linux-64/latest"
            ;;
        linux-aarch64)
            DOWNLOAD_URL="https://micro.mamba.pm/api/micromamba/linux-aarch64/latest"
            ;;
        osx-64)
            DOWNLOAD_URL="https://micro.mamba.pm/api/micromamba/osx-64/latest"
            ;;
        osx-arm64)
            DOWNLOAD_URL="https://micro.mamba.pm/api/micromamba/osx-arm64/latest"
            ;;
    esac

    echo "下载: $DOWNLOAD_URL"

    mkdir -p "$LOCAL_BIN"
    curl -Ls "$DOWNLOAD_URL" | tar -xvj bin/micromamba -C /tmp
    mv /tmp/bin/micromamba "$LOCAL_BIN/micromamba"
    chmod +x "$LOCAL_BIN/micromamba"

    MICROMAMBA_CMD="$LOCAL_BIN/micromamba"
    echo "micromamba 安装完成: $($MICROMAMBA_CMD --version)"
fi

# 配置国内镜像源
export MAMBA_ROOT_PREFIX="$MAMBA_ROOT"
export PATH="$LOCAL_BIN:$PATH"

$MICROMAMBA_CMD config set channels conda-forge
$MICROMAMBA_CMD config prepend channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
$MICROMAMBA_CMD config prepend channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 创建环境
echo "创建 yzxnice 环境..."
cd "$SCRIPT_DIR"

if $MICROMAMBA_CMD env list | grep -q "^yzxnice "; then
    echo "环境 yzxnice 已存在，跳过创建"
else
    $MICROMAMBA_CMD env create -f environment.yml -y
fi

# 安装 playwright 浏览器
echo "安装 playwright 浏览器..."
$MICROMAMBA_CMD run -n yzxnice playwright install chromium

echo ""
echo "=== 初始化完成 ==="
echo "运行以下命令启动项目："
echo "  micromamba run -n yzxnice python main.py"

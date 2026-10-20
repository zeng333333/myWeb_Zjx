#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/hub"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"

log_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

log_warn() {
    echo -e "\033[33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

main() {
    echo "=========================================="
    echo "  Hub 平台 - 代码更新脚本"
    echo "=========================================="
    echo

    # 1. 拉取最新代码（丢弃服务器本地改动，强制与远程一致）
    log_info "拉取最新代码（丢弃本地改动）..."
    cd "$SCRIPT_DIR"
    git fetch origin main
    git reset --hard origin/main
    log_info "代码更新完成"

    # 2. 检查虚拟环境
    if [ ! -d "$VENV_DIR" ]; then
        log_error "虚拟环境不存在，请先运行 deploy_bt.sh 初始化"
        exit 1
    fi

    # 3. 检查/安装新依赖
    log_info "检查 Python 依赖..."
    if "$PYTHON_BIN" -c "import django" &> /dev/null; then
        log_info "Python 依赖已安装"
    else
        log_warn "Python 依赖未安装，正在安装..."
        "$VENV_DIR/bin/pip" install -i https://pypi.tuna.tsinghua.edu.cn/simple -r "$SCRIPT_DIR/requirements.txt"
    fi

    # 4. 数据库迁移
    log_info "执行数据库迁移..."
    cd "$PROJECT_DIR"
    "$PYTHON_BIN" manage.py migrate --noinput
    log_info "数据库迁移完成"

    # 5. 收集静态文件
    log_info "收集静态文件..."
    "$PYTHON_BIN" manage.py collectstatic --noinput
    log_info "静态文件收集完成"

    # 6. 构建前端（如果前端有更新）
    if [ -d "$SCRIPT_DIR/vue-frontend" ]; then
        log_info "检查前端依赖..."
        cd "$SCRIPT_DIR/vue-frontend"
        
        if [ ! -d "node_modules" ]; then
            log_warn "前端依赖未安装，正在安装..."
            npm install --registry=https://registry.npmmirror.com
        fi
        
        log_info "构建前端..."
        npm run build
        log_info "前端构建完成"
        cd "$SCRIPT_DIR"
    else
        log_warn "vue-frontend 目录不存在，跳过前端构建"
    fi

    # 7. 检查打卡同步密钥
    ENV_FILE="$PROJECT_DIR/.env"
    if [ -f "$ENV_FILE" ]; then
        log_info "检测到打卡同步密钥文件: $ENV_FILE"
    else
        log_warn "未检测到 $PROJECT_DIR/.env，小程序 login 接口将返回 401"
        log_warn "该文件含密钥、不入库，请在服务器执行 deploy_bt.sh 生成"
    fi

    # 8. 重启服务
    log_info "重启 Gunicorn 服务..."
    systemctl restart hub
    log_info "Gunicorn 服务已重启"

    echo
    echo "=========================================="
    echo -e "\033[32m  更新完成！\033[0m"
    echo "=========================================="
    echo
    echo "请访问: http://服务器IP/"
    echo
}

main

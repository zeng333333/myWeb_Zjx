#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/hub"
VENV_DIR="$SCRIPT_DIR/venv"
PROJECT_NAME="hub"
CERT_DIR="${CERT_DIR:-/www/server/panel/vhost/cert/${PROJECT_NAME}}"

PYTHON_BIN=""
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

log_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

log_warn() {
    echo -e "\033[33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

detect_python() {
    log_info "检测 Python 环境..."
    if command -v python3 &> /dev/null; then
        PYTHON_BIN="python3"
    elif command -v python &> /dev/null; then
        PYTHON_BIN="python"
    else
        log_error "未找到 Python，请先安装 Python 3.x"
        exit 1
    fi
    log_info "使用 Python: $($PYTHON_BIN --version)"
}

check_env() {
    log_info "检查服务器环境..."
    
    detect_python
    
    if ! command -v npm &> /dev/null; then
        log_error "未找到 npm，请先安装 Node.js"
        exit 1
    fi
    
    log_info "服务器环境检查通过"
}

check_venv() {
    if [ -d "$VENV_DIR" ]; then
        log_info "虚拟环境已存在: $VENV_DIR"
    else
        log_info "创建虚拟环境..."
        $PYTHON_BIN -m venv "$VENV_DIR"
        log_info "虚拟环境创建成功"
    fi
}

install_dependencies() {
    log_info "检查依赖..."
    VENV_PYTHON="$VENV_DIR/bin/python"
    if [ ! -f "$VENV_PYTHON" ]; then
        log_error "虚拟环境 Python 解释器不存在"
        exit 1
    fi

    if ! $VENV_PYTHON -c "import django" &> /dev/null; then
        log_info "安装依赖（使用镜像源: $PIP_INDEX_URL）..."
        "$VENV_DIR/bin/pip" install -i "$PIP_INDEX_URL" -r "$SCRIPT_DIR/requirements.txt"
        log_info "依赖安装完成"
    else
        log_info "Django 已安装: $($VENV_PYTHON -c "import django; print(django.VERSION)")"
    fi
}

install_gunicorn() {
    log_info "安装 Gunicorn..."
    "$VENV_DIR/bin/pip" install -i "$PIP_INDEX_URL" gunicorn
    log_info "Gunicorn 安装完成"
}

setup_frontend() {
    log_info "配置前端环境..."
    
    cd "$SCRIPT_DIR/vue-frontend"
    
    log_info "安装 Node.js 依赖..."
    npm install --registry=https://registry.npmmirror.com
    log_info "Node.js 依赖安装完成"

    log_info "构建前端..."
    npm run build
    log_info "前端构建完成"
    
    cd "$SCRIPT_DIR"
}

run_migrations() {
    log_info "执行数据库迁移..."
    cd "$PROJECT_DIR"
    "$VENV_DIR/bin/python" manage.py migrate --noinput
    log_info "数据库迁移完成"
}

collect_static() {
    log_info "收集静态文件..."
    cd "$PROJECT_DIR"
    "$VENV_DIR/bin/python" manage.py collectstatic --noinput
    log_info "静态文件收集完成"
}

check_admin_user() {
    log_info "检查管理员账号..."
    cd "$PROJECT_DIR"
    ADMIN_EXISTS=$("$VENV_DIR/bin/python" manage.py shell -c "
from django.contrib.auth.models import User
if User.objects.filter(is_superuser=True).exists():
    print('yes')
else:
    print('no')
" 2>&1)

    if [[ "$ADMIN_EXISTS" == *"yes"* ]]; then
        log_info "检测到已有管理员账号"
    else
        log_warn "未检测到管理员账号"
        read -p "是否创建管理员账号？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "创建管理员账号..."
            read -p "请输入用户名: " ADMIN_USER
            read -p "请输入邮箱: " ADMIN_EMAIL
            read -s -p "请输入密码: " ADMIN_PASS
            echo
            "$VENV_DIR/bin/python" manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.create_superuser('$ADMIN_USER', '$ADMIN_EMAIL', '$ADMIN_PASS')
print('管理员账号创建成功:', user.username)
"
            log_info "管理员账号创建完成"
        else
            log_warn "跳过管理员账号创建"
        fi
    fi
    
    cd "$SCRIPT_DIR"
}

setup_env_file() {
    log_info "配置打卡同步密钥（.env）..."

    ENV_FILE="$PROJECT_DIR/.env"

    if [ -f "$ENV_FILE" ]; then
        log_info "已存在 $ENV_FILE，跳过（如需修改请手动编辑后重启服务）"
        return
    fi

    echo "打卡小助手云同步需要微信小程序 AppID / AppSecret。"
    echo "AppSecret 为可选项：留空则 login 接口暂不可用，其余接口不受影响。"
    read -p "请输入小程序 AppID（回车使用默认 wxf7530967009df729）: " WX_APPID
    if [ -z "$WX_APPID" ]; then
        WX_APPID="wxf7530967009df729"
    fi
    read -s -p "请输入小程序 AppSecret（回车跳过）: " WX_SECRET
    echo

    umask 077
    cat > "$ENV_FILE" <<EOF
# 打卡小助手云同步密钥（本文件不入库、不进 git）
WX_APPID=$WX_APPID
WX_SECRET=$WX_SECRET
EOF
    chmod 600 "$ENV_FILE"
    log_info "已写入 $ENV_FILE（权限 600）"
    log_warn "该文件需与运行服务的账号同属主，请确保服务以 root 运行"
}

detect_nginx() {
    NGINX_BIN=""
    if command -v nginx &> /dev/null; then
        NGINX_BIN="nginx"
    elif [ -f "/www/server/nginx/sbin/nginx" ]; then
        NGINX_BIN="/www/server/nginx/sbin/nginx"
    else
        log_warn "未找到 nginx 可执行文件，请确认 Nginx 已安装"
    fi
}

generate_nginx_config() {
    log_info "生成 Nginx 配置..."
    
    detect_nginx
    
    read -p "请输入服务器公网IP: " SERVER_IP
    read -p "请输入站点域名(可选): " SITE_DOMAIN
    
    log_info "Admin 访问控制配置"
    echo "为了安全，建议限制仅允许特定 IP 访问 Admin 后台"
    echo "多个 IP 用空格分隔，例如: 114.114.114.114 192.168.1.100"
    read -p "请输入允许访问 Admin 的 IP 地址(回车跳过，不限制): " ADMIN_ALLOW_IPS
    
    ADMIN_ACCESS_RULES=""
    if [ -n "$ADMIN_ALLOW_IPS" ]; then
        for ip in $ADMIN_ALLOW_IPS; do
            ADMIN_ACCESS_RULES="$ADMIN_ACCESS_RULES
        allow $ip;"
        done
        ADMIN_ACCESS_RULES="$ADMIN_ACCESS_RULES
        deny all;"
    else
        log_warn "未设置 Admin IP 白名单，所有 IP 均可访问 /admin/"
    fi

    SSL_CONF=""
    SSL_CERT="$CERT_DIR/fullchain.pem"
    SSL_KEY="$CERT_DIR/privkey.pem"
    if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
        log_info "检测到 SSL 证书，将同时启用 443 端口"
        SSL_CONF="
    listen 443 ssl default_server;
    listen [::]:443 ssl;
    ssl_certificate     $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_session_cache   shared:SSL:10m;"
    else
        log_warn "未检测到 SSL 证书（$CERT_DIR），本次仅生成 HTTP 配置"
        log_warn "上传 fullchain.pem / privkey.pem 后重跑 ./deploy_bt.sh --nginx-only 即可启用 HTTPS"
    fi

    NGINX_CONF="server {
    listen 80 default_server;
    listen [::]:80;${SSL_CONF}
    server_name $SERVER_IP $SITE_DOMAIN localhost 127.0.0.1 _;

    charset utf-8;
    client_max_body_size 500M;

    location /static/ {
        root $PROJECT_DIR;
        expires 30d;
    }

    location /media/ {
        root $PROJECT_DIR;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /admin/ {
$ADMIN_ACCESS_RULES
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        root $SCRIPT_DIR/vue-frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }

    access_log /www/wwwlogs/${PROJECT_NAME}_access.log;
    error_log /www/wwwlogs/${PROJECT_NAME}_error.log;
}"

    NGINX_VHOST_CONF="/www/server/panel/vhost/nginx/${PROJECT_NAME}.conf"
    
    if [ -f "$NGINX_VHOST_CONF" ]; then
        log_info "备份原有配置: ${NGINX_VHOST_CONF}.bak"
        cp "$NGINX_VHOST_CONF" "${NGINX_VHOST_CONF}.bak"
    fi
    
    echo "$NGINX_CONF" > "$NGINX_VHOST_CONF"
    log_info "Nginx 配置已写入: $NGINX_VHOST_CONF"
    
    if [ -n "$NGINX_BIN" ]; then
        if $NGINX_BIN -t 2>&1 | grep -q "test is successful"; then
            log_info "Nginx 配置语法检查通过"
        else
            log_error "Nginx 配置语法检查失败，请检查配置文件"
            $NGINX_BIN -t
        fi
    fi
    
    log_info "请手动执行以下命令以应用配置："
    echo
    echo "  # 1. 重启 Gunicorn 服务"
    echo "  systemctl restart hub"
    echo
    echo "  # 2. 重载 Nginx 配置"
    if [ -n "$NGINX_BIN" ]; then
        echo "  $NGINX_BIN -t && $NGINX_BIN -s reload"
    else
        echo "  /www/server/nginx/sbin/nginx -t && /www/server/nginx/sbin/nginx -s reload"
    fi
    echo
}

show_deploy_info() {
    echo
    echo "=========================================="
    echo "  部署脚本执行完成！"
    echo "=========================================="
    echo
    echo "项目路径: $SCRIPT_DIR"
    echo "虚拟环境: $VENV_DIR"
    echo "Nginx 配置: /www/server/panel/vhost/nginx/${PROJECT_NAME}.conf"
    echo "SSL 证书目录: $CERT_DIR"
    echo
    echo "配置 Supervisor 守护进程（宝塔面板）："
    echo "1. 登录宝塔面板：http://服务器IP:8888"
    echo "2. 安装 Supervisor 插件"
    echo "3. 添加守护进程"
    echo "   - 名称: $PROJECT_NAME"
    echo "   - 启动命令: $VENV_DIR/bin/gunicorn hub.wsgi:application --bind 127.0.0.1:8000 --workers 4"
    echo "   - 启动目录: $PROJECT_DIR"
    echo "   - 启动用户: root"
    echo
    echo "手动启动 Gunicorn（测试用）："
    echo "  cd $PROJECT_DIR"
    echo "  $VENV_DIR/bin/gunicorn hub.wsgi:application --bind 127.0.0.1:8000 --workers 4"
    echo
}

main() {
    echo "=========================================="
    echo "  Hub 平台 - 服务器本地部署脚本"
    echo "=========================================="
    echo

    if [ "$1" = "--nginx-only" ]; then
        log_info "仅重建 Nginx 配置（跳过依赖安装、前端构建、数据库迁移）"
        generate_nginx_config
        if [ -n "$NGINX_BIN" ]; then
            $NGINX_BIN -s reload
            log_info "Nginx 已重载"
        fi
        return
    fi

    check_env
    check_venv
    install_dependencies
    install_gunicorn
    setup_frontend
    run_migrations
    collect_static
    check_admin_user
    setup_env_file
    generate_nginx_config
    show_deploy_info
}

main

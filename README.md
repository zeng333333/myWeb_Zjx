# Hub - 多功能 Web 平台

基于 Django + Vue 3 的前后端分离 Web 平台，集成首页入口、应用仓库等功能模块。

## 快速开始

```bash
git clone https://github.com/cn33331/myWeb_Zjx.git web
cd web

# macOS 一键启动前后端开发服务
chmod +x 启动服务.command
./启动服务.command
```

启动后访问：

| 服务 | 地址 |
| --- | --- |
| 前端开发服务器 | http://localhost:5173/ |
| Django 后端 | http://localhost:8000/ |
| Django 管理后台 | http://localhost:8000/admin |

## 平台模块

| 模块 | 路径前缀 | 应用 | 说明 |
| --- | --- | --- | --- |
| 首页入口 | `/` | `home` | 展示平台各功能模块入口卡片 |
| 应用仓库 | `/store/` | `store` | 工具的上传、下载与详情查看 |
| 趣味 | `/fun/` | —（纯前端） | 存放有趣的静态页面，如祝福飘落动画 |
| 管理后台 | `/admin/` | Django Admin | 站点管理 |
| API 接口 | `/api/` | DRF | RESTful API 服务 |

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│  前端层 — Vue 3 + Vite + Pinia + Axios                  │
│  /vue-frontend/                                         │
│  ├── src/pages/        页面组件（Home/Store/Auth）       │
│  ├── src/components/   通用组件（ToolCard/Header）       │
│  ├── src/api/          API 请求封装                      │
│  └── src/stores/       Pinia 状态管理                    │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP (Axios + JWT)
                           ▼
┌─────────────────────────────────────────────────────────┐
│  后端层 — Django + DRF + SimpleJWT                      │
│  /hub/                                                  │
│  ├── hub/settings.py    CORS / DRF / JWT 配置            │
│  ├── hub/auth_*.py      认证模块（登录/注册/Token刷新）  │
│  └── store/api/         仓库模块 API                     │
└──────────────────────────┬──────────────────────────────┘
                           │ Gunicorn / runserver
                           ▼
┌─────────────────────────────────────────────────────────┐
│  部署层 — Nginx 反向代理                                │
│  静态资源  /        → Vue dist                          │
│  API 转发  /api/    → Django (127.0.0.1:8000)           │
│  媒体文件  /media/  → Django MEDIA_ROOT                 │
│  管理后台  /admin/  → Django Admin（可配 IP 白名单）     │
└─────────────────────────────────────────────────────────┘
```

## 项目结构

```
web/
├── hub/                         # Django 后端项目
│   ├── manage.py
│   ├── db.sqlite3               # SQLite 数据库文件
│   ├── hub/                     # 项目配置
│   │   ├── settings.py          # Django + DRF + JWT + CORS 配置
│   │   ├── urls.py              # 根路由（含 /api/ 入口）
│   │   ├── api_urls.py          # API 路由聚合
│   │   ├── auth_views.py        # 登录/注册视图
│   │   ├── auth_serializers.py
│   │   └── auth_urls.py
│   ├── home/                    # 首页入口应用
│   ├── store/                   # 应用仓库模块
│   │   ├── models.py
│   │   ├── api/                 # REST API（serializers/views/urls）
│   │   └── templates/store/
│   ├── static/                  # 收集的静态文件
│   └── media/                   # 用户上传文件
├── vue-frontend/                # Vue 3 前端项目
│   ├── src/
│   │   ├── api/                 # axios 封装（index/store/auth）
│   │   ├── components/          # 通用组件（Header/ToolCard/Loading）
│   │   ├── pages/               # 页面组件
│   │   ├── stores/              # Pinia 状态管理（auth/store）
│   │   ├── router/              # 路由配置与导航守卫
│   │   ├── App.vue
│   │   └── main.js
│   ├── public/fun-pages/        # 趣味静态页面（html + manifest.json）
│   ├── .env.development         # 开发环境 API 地址
│   ├── .env.production          # 生产环境 API 地址
│   └── vite.config.js           # Vite 配置（代理、别名）
├── nginx/                       # Nginx 配置
│   └── conf/nginx.conf          # 本地开发用 Nginx 配置（端口 8080）
├── requirements.txt             # Python 依赖
├── deploy_bt.sh                 # 宝塔面板生产部署脚本（交互式）
├── update.sh                    # 代码更新脚本（非交互式）
└── 启动服务.command              # macOS 双击启动开发环境
```

## 功能说明

### 首页（home）

- 根路径 `/` 展示平台各功能模块入口卡片

### 应用仓库（store）

- 工具列表展示与搜索
- 工具上传管理（管理员）
- 工具下载（带下载次数统计）
- 工具详情查看

### 趣味（fun）

- 汇总展示 `public/fun-pages/` 下的趣味静态页面
- 页面以独立 HTML 存放，`manifest.json` 登记；新增页面只需放入文件并加一条记录
- 点击卡片在新标签页打开（如「天天开心」祝福飘落动画）
- 纯前端实现，不依赖后端应用（静态目录名避开路由 `/fun`，防止 nginx 目录优先导致 301/403）

## API 接口总览

### 认证

| API 路径 | 方法 | 说明 | 认证 |
| --- | --- | --- | --- |
| `/api/auth/login/` | POST | 用户登录 | 公开 |
| `/api/auth/refresh/` | POST | Token 刷新 | 需 refresh_token |

### 应用仓库

| API 路径 | 方法 | 说明 | 认证 |
| --- | --- | --- | --- |
| `/api/store/tools/` | GET | 工具列表 | 公开 |
| `/api/store/tools/` | POST | 上传工具 | 管理员 |
| `/api/store/tools/<id>/` | GET | 工具详情 | 公开 |
| `/api/store/tools/<id>/` | DELETE | 删除工具 | 管理员 |
| `/api/store/tools/<id>/download/` | GET | 工具下载 | 公开 |

### 打卡云同步（checkin）

小程序端把本地数据整包推送到服务端，服务端按版本号存取、防覆盖；服务端不解析业务字段。

| API 路径 | 方法 | 说明 | 认证 |
| --- | --- | --- | --- |
| `/api/checkin/login/` | POST | code 换 openid 并签发 token（7 天） | 公开 |
| `/api/checkin/sync/pull/` | GET | 拉取当前用户全量快照 | 需 token |
| `/api/checkin/sync/push/` | POST | 整包覆盖上传（带 baseVersion，冲突返回 409） | 需 token |
| `/api/checkin/space/` | GET | 查询当前用户所在数据空间（spaceId / memberCount / isOwner） | 需 token |
| `/api/checkin/space/code/` | POST | 生成一次性绑定码（6 位数字，10 分钟有效，同空间重复生成旧码作废） | 需 token |
| `/api/checkin/space/join/` | POST | 凭绑定码加入空间（只改 openid→space 映射，不动快照） | 需 token |
| `/api/checkin/space/leave/` | POST | 退出空间（新建单人空间并复制当前快照，退出不丢数据） | 需 token |

> V2 起数据归属从 openid 提升为 space_id：两个微信号加入同一空间即共用一份快照；V1 客户端不受影响。
> 需在运行环境配置 `WX_APPID` / `WX_SECRET` 环境变量；小程序 request 域名上线前需 HTTPS + 已备案域名。

## 前端路由

| 路径 | 组件 | 说明 | 权限 |
| --- | --- | --- | --- |
| `/` | HomePage | 首页入口 | 公开 |
| `/store` | StorePage | 仓库列表 | 公开 |
| `/fun` | FunPage | 趣味页面 | 公开 |
| `/store/:id` | ToolDetailPage | 工具详情 | 公开 |
| `/store/upload` | ToolUploadPage | 工具上传 | 管理员 |
| `/login` | LoginPage | 登录 | 未登录 |

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
| --- | --- | --- |
| Django | 4.2 | Web 框架 |
| Django REST Framework | 3.16 | RESTful API |
| djangorestframework-simplejwt | 5.5 | JWT 认证（Access 2h / Refresh 7d） |
| django-cors-headers | 4.9 | 跨域支持 |
| PyMySQL | 1.1 | MySQL 驱动（生产可选） |
| Gunicorn | - | 生产 WSGI 服务器 |
| SQLite | - | 默认数据库 |

### 前端

| 技术 | 版本 | 用途 |
| --- | --- | --- |
| Vue | 3.5 | 前端框架 |
| Vite | 6.3 | 构建工具 |
| Pinia | 4.0 | 状态管理 |
| Vue Router | 4.6 | 路由管理 |
| Axios | 1.18 | HTTP 请求 |

### 部署

- Nginx — 反向代理 + 静态资源服务
- systemd — Gunicorn 进程守护（生产）
- 宝塔面板 — 可选的服务器管理面板

## 本地部署

### macOS 开发环境

```bash
git clone https://github.com/cn33331/myWeb_Zjx.git web
cd web

# 一键启动前后端开发服务
chmod +x 启动服务.command
./启动服务.command
```

也可使用本地 Nginx 配置统一入口（监听 8080 端口）：

```bash
nginx -c /path/to/web/nginx/conf/nginx.conf
```

访问 http://localhost:8080/ 即可通过 Nginx 统一访问前后端。

### Linux 生产环境（宝塔面板）

```bash
cd /www/wwwroot
git clone https://github.com/cn33331/myWeb_Zjx.git zjx
cd zjx

# 交互式部署（自动创建虚拟环境、安装依赖、构建前端、迁移数据库、生成 Nginx 配置）
chmod +x deploy_bt.sh
./deploy_bt.sh
```

> **项目目录不要放在 `/root` 下**。Nginx 以 `www` 用户运行，读不到 `/root` 内的静态文件，会导致前端页面返回 500（`rewrite or internal redirection cycle`）。推荐放在 `/www/wwwroot/`。

`deploy_bt.sh` 会交互式引导完成以下步骤：

1. 检测 Python / Node.js 环境
2. 创建虚拟环境并安装 Python 依赖 + Gunicorn
3. 安装前端依赖并构建
4. 执行数据库迁移与静态文件收集
5. 检查/创建管理员账号
6. 生成 Nginx 配置（含 Admin IP 白名单设置，检测到证书时自动启用 443）

部署完成后，按脚本提示配置 Gunicorn 守护进程：

```bash
# 方式一：systemd
cat > /etc/systemd/system/hub.service << 'EOF'
[Unit]
Description=Hub Platform Gunicorn Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/zjx/hub
ExecStart=/www/wwwroot/zjx/venv/bin/gunicorn hub.wsgi:application --bind 127.0.0.1:8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start hub
systemctl enable hub

# 方式二：宝塔面板 Supervisor 插件
# 启动命令: /www/wwwroot/zjx/venv/bin/gunicorn hub.wsgi:application --bind 127.0.0.1:8000 --workers 4
# 启动目录: /www/wwwroot/zjx/hub

# 重载 Nginx
/www/server/nginx/sbin/nginx -t && /www/server/nginx/sbin/nginx -s reload
```

启动后访问：`http://服务器公网IP/`

### 代码更新流程

```bash
cd /www/wwwroot/zjx

# 一键更新（拉取代码、检查依赖、迁移数据库、构建前端、重启服务）
chmod +x update.sh
./update.sh
```

`update.sh` 只负责**代码层面**的更新：拉代码 → 装依赖 → 迁移 → 收集静态文件 → 构建前端 → 重启 `hub` 服务。

它**不会重建 Nginx 配置**。以下情况需要额外执行一次 `--nginx-only`：

- 修改了域名 / 服务器公网IP
- 新增或更换 SSL 证书
- 调整了 Admin IP 白名单
- 首次配置 HTTPS

```bash
cd /www/wwwroot/zjx
./deploy_bt.sh --nginx-only
```

该模式会跳过依赖安装、前端构建和数据库迁移，只重建 Nginx 配置并重载，几秒完成。

| 脚本 | 用途 | 模式 |
| --- | --- | --- |
| `deploy_bt.sh` | 首次部署 | 交互式 |
| `deploy_bt.sh --nginx-only` | 仅重建 Nginx 配置并重载 | 交互式 |
| `update.sh` | 日常更新 | 非交互式 |

更新后的验证：

```bash
# 服务状态
systemctl status hub --no-pager | head -10

# 前端
curl -I 'https://你的域名/'

# 后端链路（期望 401，不是 502/404/500）
curl -I 'https://你的域名/api/checkin/sync/pull/'
```

失败时按顺序看三处日志：

```bash
journalctl -u hub -n 60 --no-pager        # Django 异常栈 / Gunicorn 启动错误
tail -30 /www/wwwlogs/hub_error.log       # Nginx 层（反代、权限、路径）
tail -50 /www/wwwroot/zjx/hub/logs/checkin.log   # 业务日志（小程序联调）
```

### SSL 证书配置（HTTPS）

微信小程序要求 `request` 域名必须为 HTTPS（TLS 1.2+、443 端口、不能带端口号），因此生产环境必须配置证书。

**① 上传证书到服务器**

从腾讯云 / 阿里云 SSL 控制台下载 **Nginx 格式**证书包，用宝塔「文件」上传到 `/www/server/panel/vhost/cert/`，然后执行：

```bash
mkdir -p /www/server/panel/vhost/cert/hub
cd /www/server/panel/vhost/cert/hub

# 解压证书包（文件名以实际下载的域名为准）
unzip -o /www/server/panel/vhost/cert/<域名>_nginx.zip

# 改名为 Nginx 约定名称
mv <域名>_nginx/<域名>_bundle.crt fullchain.pem
mv <域名>_nginx/<域名>.key     privkey.pem

chmod 755 /www/server/panel/vhost/cert/hub
chmod 644 fullchain.pem
chmod 600 privkey.pem

rm -rf <域名>_nginx
```

证书包内文件对应关系：

| 包内文件 | 目标文件名 | 说明 |
| --- | --- | --- |
| `<域名>_bundle.crt` | `fullchain.pem` | 服务器证书 + 中间证书（完整链，**必须用这个**） |
| `<域名>.key` | `privkey.pem` | 私钥，权限 600 |
| `<域名>_bundle.pem` | 不需要 | 与 `.crt` 内容相同 |
| `<域名>.csr` | 不需要 | 证书签名请求，仅申请时使用 |

> **证书文件严禁提交到 git**，私钥一旦入库即视为泄露。它们以未跟踪文件形式存在于服务器，`update.sh` 的 `git reset --hard` 不会删除。

**② 重建 Nginx 配置**

```bash
cd /www/wwwroot/zjx
./update.sh                      # 拉取最新代码
./deploy_bt.sh --nginx-only      # 重建配置并自动重载
```

脚本会自动检测 `CERT_DIR`（默认 `/www/server/panel/vhost/cert/hub`）下的 `fullchain.pem` 与 `privkey.pem`：

- 存在 → 生成 `listen 443 ssl` 配置，输出「检测到 SSL 证书，将同时启用 443 端口」
- 不存在 → 仅生成 HTTP 配置并给出提示，站点仍可正常访问

交互提示按如下填写：

```
请输入服务器公网IP: <公网IP>
请输入站点域名(可选): www.example.com example.com   # 多个域名用空格分隔
请输入允许访问 Admin 的 IP 地址: <你的公网IP>
```

**③ 放行 443 端口**

云厂商控制台 → 安全组 → 入方向规则添加 `443/TCP`。仅开服务器本地防火墙不够，安全组不放行时外部依然无法连接。

**④ 验证**

```bash
# 确认实际下发的证书正确
echo | openssl s_client -connect www.example.com:443 -servername www.example.com 2>/dev/null \
  | openssl x509 -noout -subject -dates

# 页面可访问
curl -I https://www.example.com/

# 后端链路（无 token 应返回 401 而非 502/404）
curl -I https://www.example.com/api/checkin/sync/pull/
```

**⑤ 证书续期**

免费 DV 证书有效期通常为 **90 天**，云厂商不自动续签。到期前重新申请、覆盖 `fullchain.pem` / `privkey.pem`，再执行一次 `./deploy_bt.sh --nginx-only` 即可。

> 也可改用 `acme.sh` 自动续签（自带 cron，换证后自动 reload Nginx），避免手动维护。

## 关键配置

| 配置项 | 值 | 说明 |
| --- | --- | --- |
| `DEBUG` | `False` | 生产环境已关闭调试模式 |
| `JWT Access Token` | 2 小时 | 访问令牌有效期 |
| `JWT Refresh Token` | 7 天 | 刷新令牌有效期 |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | 500 MB | 请求数据上传上限 |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | 25 MB | 文件上传内存阈值 |
| `Nginx client_max_body_size` | 500 MB | Nginx 请求体大小限制 |
| `CORS_ALLOWED_ORIGINS` | localhost:5173, localhost:80 | 允许的前端来源 |
| `PAGE_SIZE` | 10 | DRF 分页大小 |

## 安全注意事项

1. 生产环境确保 `DEBUG = False`（当前已配置）
2. `CORS_ALLOWED_ORIGINS` 仅允许前端域名，不要使用通配符
3. `SECRET_KEY` 应通过环境变量管理，不要硬编码在代码中
4. 仅开放 80/443 端口，限制 8000 端口仅本地访问
5. 利用 `deploy_bt.sh` 的 Admin IP 白名单功能限制 `/admin/` 访问
6. 部署 SSL 证书（Let's Encrypt）强制 HTTPS

## License

详见 [LICENSE](LICENSE)。

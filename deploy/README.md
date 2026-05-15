# YZXNice 部署指南

## 架构

```
客户端 → nginx:80 → unix socket(/dev/shm/yzxnice.sock) → uvicorn(asgi:fastapi_app)
```

- **nginx**：监听 80 端口，反向代理到本地 unix socket
- **uvicorn**：以 pyuser 身份运行，通过 `/dev/shm/yzxnice.sock` 与 nginx 通讯
- **pixi**：Python 环境与依赖管理，所有 Python 命令必须通过 `pixi run` 执行

## 前置条件

- OS：Alibaba Cloud Linux 4（或 RHEL 系）
- 用户：pyuser（uid=1000）已存在
- pixi 已安装在 `/home/pyuser/.pixi/bin/pixi`

## 文件清单

```
deploy/
├── yzxnice.service    # systemd 服务单元
├── yzxnice.conf       # nginx 站点配置
└── setup.sh           # 一键部署脚本
```

## 一键部署

以 root 执行：

```bash
cd /home/pyuser/projects/yzxnice
bash deploy/setup.sh
```

脚本会依次完成：安装 nginx → 部署配置 → 安装 pixi 依赖 → 启动服务。

## 手动部署步骤

### 1. 安装 nginx

```bash
dnf install -y nginx
```

### 2. 部署 nginx 配置

```bash
cp /home/pyuser/projects/yzxnice/deploy/yzxnice.conf /etc/nginx/conf.d/yzxnice.conf
nginx -t
```

### 3. 部署 systemd 服务

```bash
cp /home/pyuser/projects/yzxnice/deploy/yzxnice.service /etc/systemd/system/yzxnice.service
systemctl daemon-reload
```

### 4. 安装 Python 依赖（以 pyuser 身份）

```bash
su - pyuser -c "cd /home/pyuser/projects/yzxnice && pixi install"
```

> **注意**：禁止使用 `pip install` / `conda install`，统一通过 `pixi` 管理。
> 新增依赖时修改 `pixi.toml` 中的 `[dependencies]` 或 `[pypi-dependencies]`，然后重新 `pixi install`。

### 5. 启动服务

```bash
systemctl enable yzxnice nginx
systemctl start yzxnice
systemctl start nginx
```

## 服务管理

```bash
systemctl status yzxnice          # 查看应用状态
systemctl restart yzxnice         # 重启应用
systemctl stop yzxnice            # 停止应用
journalctl -u yzxnice -f          # 实时查看应用日志
journalctl -u yzxnice --since today  # 今日日志

systemctl reload nginx            # 重载 nginx 配置（不中断服务）
systemctl restart nginx           # 重启 nginx
tail -f /var/log/nginx/yzxnice_error.log    # nginx 错误日志
tail -f /var/log/nginx/yzxnice_access.log   # nginx 访问日志
```

## 关键配置说明

### systemd service（yzxnice.service）

- `User=pyuser`：以 pyuser 身份运行，不以 root 运行
- `ExecStart`：通过 `pixi run uvicorn` 启动，确保使用 pixi 管理的 Python 环境
- `--uds /dev/shm/yzxnice.sock`：unix socket 放在共享内存文件系统，无需手动创建目录
- `--proxy-headers --forwarded-allow-ips=*`：信任 nginx 传递的 X-Forwarded-* 头
- `ExecStopPost`：服务停止时自动清理 socket 文件

### nginx 配置（yzxnice.conf）

- `upstream`：指向 `/dev/shm/yzxnice.sock`
- `location /`：通用反向代理，支持 WebSocket 升级（NiceGUI 的 Socket.IO 需要）
- `location /socket.io/`：显式处理 Socket.IO 路径，超时 24 小时防止长连接断开
- `client_max_body_size 16m`：匹配应用的上传限制

### ASGI 入口（asgi.py）

- 创建独立 `FastAPI` 实例，通过 `ui.run_with()` 挂载 NiceGUI
- uvicorn 加载 `asgi:fastapi_app` 作为 ASGI 应用

## 更新部署

代码更新后：

```bash
cd /home/pyuser/projects/yzxnice
su - pyuser -c "cd /home/pyuser/projects/yzxnice && pixi install"   # 依赖变更时
systemctl restart yzxnice
```

## 故障排查

### 服务启动失败

```bash
journalctl -u yzxnice -n 50 --no-pager    # 查看最近 50 行日志
```

常见原因：
- pixi 环境未安装 → `su - pyuser -c "cd /home/pyuser/projects/yzxnice && pixi install"`
- `.env` 文件缺失 → 确保 `SECRET_KEY` 和 `DEFAULT_PASSWORD` 已设置
- socket 文件残留 → `rm -f /dev/shm/yzxnice.sock` 后重启

### nginx 502 Bad Gateway

```bash
ls -la /dev/shm/yzxnice.sock              # 检查 socket 是否存在
systemctl status yzxnice                   # 检查应用是否运行
tail /var/log/nginx/yzxnice_error.log      # 查看 nginx 错误日志
```

### 验证 socket 通讯

```bash
# 手动通过 socket 发请求测试
curl --unix-socket /dev/shm/yzxnice.sock http://localhost/login
```

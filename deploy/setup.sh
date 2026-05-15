#!/bin/bash
set -e

PROJECT_DIR=/home/pyuser/projects/yzxnice
DEPLOY_DIR=$PROJECT_DIR/deploy

echo "=== 1. 安装 nginx ==="
sudo dnf install -y nginx || sudo yum install -y nginx

echo "=== 2. 配置 nginx ==="
sudo cp $DEPLOY_DIR/yzxnice.conf /etc/nginx/conf.d/yzxnice.conf
sudo nginx -t

echo "=== 3. 配置 systemd service ==="
sudo cp $DEPLOY_DIR/yzxnice.service /etc/systemd/system/yzxnice.service
sudo systemctl daemon-reload

echo "=== 4. 安装 pixi 依赖（以 pyuser 身份） ==="
su - pyuser -c "cd $PROJECT_DIR && pixi install"

echo "=== 5. 启动服务 ==="
sudo systemctl enable yzxnice nginx
sudo systemctl restart yzxnice
sleep 2
sudo systemctl restart nginx

echo ""
echo "=== 部署完成 ==="
echo ""
echo "常用命令:"
echo "  sudo systemctl status yzxnice     # 查看应用状态"
echo "  sudo systemctl restart yzxnice    # 重启应用"
echo "  sudo journalctl -u yzxnice -f     # 查看应用日志"
echo "  sudo systemctl reload nginx       # 重载 nginx"
echo "  sudo tail -f /var/log/nginx/yzxnice_error.log  # nginx 错误日志"

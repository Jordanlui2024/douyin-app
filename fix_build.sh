#!/bin/bash
echo "开始修复构建问题..."

# 备份原配置
cp buildozer.spec buildozer.spec.backup

# 创建修复后的配置
cat > buildozer.spec << 'SPEC_EOF'
[app]
title = 抖音视频工具
package.name = douyinapp
package.domain = org.douyin

version = 1.0
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ico,txt

requirements = python3, kivy, requests

orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2

[app]
icon.filename = %(source.dir)s/favicon.ico
presplash.filename = %(source.dir)s/favicon.ico

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE

android.api = 30
android.minapi = 21
android.sdk = 20
android.ndk = 19b
android.gradle_version = 6.9.4
android.enable_androidx = False

SPEC_EOF

echo "配置已更新，开始清理缓存..."
buildozer android clean
echo "修复完成！现在可以重新构建：buildozer android debug"

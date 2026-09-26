#!/usr/bin/env bash
# 在云端容器中安装 KiCad（官方 Docker 镜像 kicad/kicad 解包 + chroot 运行）。
#
# 背景：云端网络策略拦截了 KiCad PPA (ppa.launchpadcontent.net / launchpadlibrarian.net)
# 和 downloads.kicad.org，但 Docker Hub 可达，所以直接拉官方镜像的各层解包成根文件系统。
#
# 用法:  sudo bash tools/setup_kicad.sh [版本号，默认 10.0.6]
# 幂等：已安装且版本一致时只补挂载和包装脚本。
# 安装后:  kicad-cli version      kicad-python -c "import pcbnew"
# 限制：chroot 内只能访问 /home/user 和 /tmp 下的文件；镜像不含 3D 模型（需要时用 <ver>-full 标签）。
set -euo pipefail

VER="${1:-10.0.6}"
ROOT=/opt/kicad-root
CACHE=/opt/kicad-img/layers-$VER
REPO=kicad/kicad
TAG="$VER-amd64"

have_ver() { [ -x "$ROOT/usr/bin/kicad-cli" ] && [ "$(chroot "$ROOT" /usr/bin/kicad-cli version 2>/dev/null)" = "$VER" ]; }

mount_binds() {
    for d in proc dev tmp home/user; do
        mkdir -p "$ROOT/$d"
        mountpoint -q "$ROOT/$d" || mount --bind "/$d" "$ROOT/$d"
    done
    cp /etc/resolv.conf "$ROOT/etc/" 2>/dev/null || true
}

if [ ! -x "$ROOT/usr/bin/kicad-cli" ]; then
    mkdir -p "$CACHE" "$ROOT"
    TOK=$(curl -fsS "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$REPO:pull" |
          python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
    curl -fsS "https://registry-1.docker.io/v2/$REPO/manifests/$TAG" \
        -H "Authorization: Bearer $TOK" \
        -H "Accept: application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json" \
        > "$CACHE/manifest.json"
    i=0
    for d in $(python3 -c "import json;[print(l['digest']) for l in json.load(open('$CACHE/manifest.json'))['layers']]"); do
        i=$((i + 1)); f="$CACHE/layer$(printf %02d $i).tgz"
        if [ ! -s "$f" ] || [ "sha256:$(sha256sum "$f" | cut -d' ' -f1)" != "$d" ]; then
            echo "下载层 $i: $d"
            curl -fsSL -m 1800 -o "$f" "https://registry-1.docker.io/v2/$REPO/blobs/$d" -H "Authorization: Bearer $TOK"
            [ "sha256:$(sha256sum "$f" | cut -d' ' -f1)" = "$d" ] || { echo "校验失败: $f"; exit 1; }
        fi
        # whiteout 文件只用于删除 apt 缓存，跳过不影响 KiCad 运行
        tar -xzf "$f" -C "$ROOT" --exclude='*.wh.*' 2>&1 | grep -v 'Cannot mknod' || true
    done
fi

mount_binds

for t in kicad-cli kicad-python; do
    cmd=$([ "$t" = kicad-python ] && echo python3 || echo kicad-cli)
    cat > /usr/local/bin/$t <<EOF
#!/bin/sh
# KiCad (官方 Docker 镜像解包到 $ROOT，chroot 运行)，由 tools/setup_kicad.sh 生成
exec chroot $ROOT /bin/sh -c 'cd "\$0" 2>/dev/null || cd /; exec "\$@"' "\$PWD" /usr/bin/$cmd "\$@"
EOF
    chmod +x /usr/local/bin/$t
done

have_ver && echo "KiCad $(kicad-cli version) 就绪" || { echo "安装后版本不符"; exit 1; }
kicad-python -c "import pcbnew; print('pcbnew', pcbnew.Version())"

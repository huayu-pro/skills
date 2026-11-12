# 装 LibreOffice（不需要 root）

`verify-render.mjs` 需要一个真渲染器。这台机器没有 sudo，所以走 **deb 解包**：把包装下下来，`dpkg-deb -x` 解到一个用户目录，再补上 Debian 安装脚本本来会做的事。

实测：44 个包 / 84MB / 约 1 分钟（清华源），解包后 278MB。

---

## 一、为什么不用 AppImage

官方 AppImage 也行，但从这台机器下载只有 ~91 KB/s（290MB 要将近一小时）。走 apt 源能到 1.2 MB/s。

AppImage 路线（作为备选）：

```bash
mkdir -p ~/opt/libreoffice && cd ~/opt/libreoffice
curl -L -o lo.AppImage https://appimages.libreitalia.org/LibreOffice-26.8.1.1.basic-x86_64.AppImage
chmod +x lo.AppImage && ./lo.AppImage --appimage-extract
# 之后用 ~/opt/libreoffice/squashfs-root/AppRun
```

---

## 二、deb 解包法（四步）

```bash
# 1. 列出要装的包（只需 impress，依赖会自动带上）
apt-get -s install -y libreoffice-impress | grep '^Inst ' | awk '{print $2}' | sort -u > /tmp/lo_pkgs.txt

# 2. 逐个下载（一个一个下，某个失败不会中断全部）
mkdir -p /tmp/lodeb && cd /tmp/lodeb
while read p; do apt-get download "$p"; done < /tmp/lo_pkgs.txt

# 3. 解包到用户目录（不碰系统）
mkdir -p ~/opt/lo-deb
for f in /tmp/lodeb/*.deb; do dpkg-deb -x "$f" ~/opt/lo-deb; done

# 4. 修补（见下）
```

---

## 三、必须修补的四处

`dpkg-deb -x` 只是解压，**不会执行 postinst**。Debian 的 `libreoffice-common` 里有四个符号链接指向 `/etc` 和 `/var`，安装脚本会负责创建目标；我们没跑脚本，所以全是断链，启动时直接抛 `uno::RuntimeException`，而且**没有任何错误信息**。

```bash
LOROOT=~/opt/lo-deb/usr/lib/libreoffice

# ① registry：真文件在 share/.registry，postinst 会复制到 /etc 再建链
mkdir -p ~/opt/lo-deb/etc/libreoffice/registry
cp "$LOROOT/share/.registry/main.xcd" ~/opt/lo-deb/etc/libreoffice/registry/main.xcd
rm -f "$LOROOT/share/registry/main.xcd"
cp ~/opt/lo-deb/etc/libreoffice/registry/main.xcd "$LOROOT/share/registry/main.xcd"

# ② 打印配置
rm -f "$LOROOT/share/psprint/psprint.conf"
cp ~/opt/lo-deb/etc/libreoffice/psprint.conf "$LOROOT/share/psprint/psprint.conf"

# ③ 两个运行时目录（原本指向 /var/lib、/var/spool）
rm -f "$LOROOT/share/prereg/bundled" "$LOROOT/share/uno_packages/cache"
mkdir -p "$LOROOT/share/prereg/bundled" "$LOROOT/share/uno_packages/cache"

# ④ fundamentalrc 把 BRAND_BASE_DIR 写死成 /usr/lib/libreoffice
sed -i "s|file:///usr/lib/libreoffice|file://$LOROOT|g" "$LOROOT/program/fundamentalrc"
```

检查是否还有断链：`find "$LOROOT" -xtype l`，应该输出为空。

---

## 四、包装脚本

`soffice.bin` 里编译死了 `URE_BOOTSTRAP=/usr/lib/libreoffice/program/fundamentalrc`，所以必须显式告诉它 rc 在哪，否则同样是一个没有信息的 `RuntimeException`。

写成 `~/opt/lo-deb/soffice`：

```bash
#!/bin/bash
DEST="$(cd "$(dirname "$0")" && pwd)"
LOROOT="$DEST/usr/lib/libreoffice"
export LD_LIBRARY_PATH="$LOROOT/program:$DEST/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SAL_USE_VCLPLUGIN=svp          # 无显示环境的后端
export URE_BOOTSTRAP="file://$LOROOT/program/fundamentalrc"
exec "$LOROOT/program/soffice.bin" "$@"
```

注意用 `dirname "$0"` 定位而不是 `$HOME`——调用方如果改了 `HOME`，`$HOME/opt/...` 就指到别处去了。

验证：

```bash
~/opt/lo-deb/soffice --version
# LibreOffice 26.2.6.3 620(Build:3)
```

---

## 五、两个会白白浪费一小时的坑

**1. `--convert-to pdf` 静默不产出。**

解包安装的 LO 解析不了 `pdf` 这个过滤器别名，退出码 0、无输出、无文件。必须写全：

```bash
soffice --headless --norestore \
        --convert-to pdf:impress_pdf_Export \
        --outdir /tmp/out deck.pptx
```

**2. 不要传 `-env:UserInstallation`。**

在精简安装里新建 profile 会静默失败（同样是退出码 0、无文件）。用默认 profile（`~/.config/libreoffice`）才正常。代价是并发跑多个实例可能抢锁——串行跑就行。

---

## 六、接到验收流程里

```bash
export CST_SOFFICE=~/opt/lo-deb/soffice    # 或者让它自动找 ~/opt/lo-deb/soffice
node scripts/verify-render.mjs deck.pptx --out render --vs preview
```

阈值默认 12%：LibreOffice 的字体替换和 PowerPoint 不完全一样，文字会整段轻微位移。它抓的是**整块丢失、图形错位、文件打不开**这类硬伤，不是字体差异。

判读方法：看 `diff-XX.png`。如果红点只落在文字上，是字体替换；如果图形边缘出现红边，才是几何错了。

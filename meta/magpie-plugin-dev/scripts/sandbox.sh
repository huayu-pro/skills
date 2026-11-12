#!/usr/bin/env bash
# magpie 离线沙箱一键初始化（开发-调试循环的三个实测坑都在这里封装）：
#   ① MAGPIE_PLUGIN_MARKET=off 关市场；
#   ② 秒失败代理——CLI 启动仍会联网探测，无代理挂数分钟，指向立即拒绝的端口让它立刻回退；
#   ③ 复制本机 Bun 运行时——全新沙箱没有它，plugin 命令会去 GitHub 下载并挂死。
#
# 用法一（推荐）：source sandbox.sh && m plugin add ./my-plugin && m plugin
#   ⚠️ source 定义的 m() 只在同一 shell 会话存活；agent/CI 每条命令独立 shell 时用用法二
# 用法二（单发）：./sandbox.sh -- <magpie 子命令>        # 例：./sandbox.sh -- plugin --json
# 选项：--online    跳过秒失败代理，真联网测上游（接受启动可能挂数分钟）
#       MAGPIE_SANDBOX=/path   复用指定沙箱目录而不是 mktemp 新建
#       MAGPIE_BIN=/path       指定 magpie 可执行文件
#   ⚠️ 覆盖 MAGPIE_BIN 需先 export（`MAGPIE_BIN=… source 本脚本` 的前缀赋值会被 bash 在
#      source 结束后恢复旧值，导致 m() 拿到空路径）；MAGPIE_SANDBOX 无此问题

MAGPIE_BIN="${MAGPIE_BIN:-$(command -v magpie || true)}"
[ -n "$MAGPIE_BIN" ] || MAGPIE_BIN="$HOME/.local/bin/magpie"

_IS_EXEC=0
[ "${BASH_SOURCE[0]:-}" = "$0" ] && _IS_EXEC=1

# ⚠️ 代理数组必须是全局变量：m() 在 init 函数返回后才被调用，
# local 变量此时已销毁，动态作用域下 m() 会拿到空值（代理静默失效）
SANDBOX_PROXY_ARGS=()

magpie_sandbox_init() {
  local online="${1:-}"
  if [ -x "$MAGPIE_BIN" ]; then
    : # 可执行文件就绪
  elif [ "$_IS_EXEC" = 1 ]; then
    echo "[sandbox] 找不到可执行的 magpie（设 MAGPIE_BIN 指定路径）：$MAGPIE_BIN" >&2
    exit 1
  else
    echo "[sandbox] ⚠️ 找不到可执行的 magpie（$MAGPIE_BIN）——m() 调用会失败；source 场景不退出，设 MAGPIE_BIN 后重新 source" >&2
    return 1
  fi
  sb="${MAGPIE_SANDBOX:-$(mktemp -d)}"
  mkdir -p "$sb/.config" "$sb/.cache/magpie"
  if [ -d "$HOME/.cache/magpie/bun" ]; then
    # 先清再拷：复用旧沙箱时直接 cp -r 会嵌套成 bun/bun，宿主找不到 Bun 就会去联网下载并挂死
    rm -rf "$sb/.cache/magpie/bun"
    cp -r "$HOME/.cache/magpie/bun" "$sb/.cache/magpie/"
  else
    echo "[sandbox] ⚠️ 本机没有 ~/.cache/magpie/bun 可复制——plugin 命令会尝试联网下载 Bun，可能长时间挂起" >&2
  fi
  if [ "$online" = "--online" ]; then
    SANDBOX_PROXY_ARGS=()
    local proxy_note="真联网（--online，启动探测可能挂数分钟）"
  else
    SANDBOX_PROXY_ARGS=(HTTPS_PROXY=http://127.0.0.1:1 HTTP_PROXY=http://127.0.0.1:1 NO_PROXY=127.0.0.1,localhost)
    local proxy_note="秒失败代理(http://127.0.0.1:1)"
  fi
  m() {
    env HOME="$sb" XDG_CONFIG_HOME="$sb/.config" XDG_CACHE_HOME="$sb/.cache" \
      MAGPIE_ADDR=127.0.0.1:3499 MAGPIE_PLUGIN_MARKET=off \
      ${SANDBOX_PROXY_ARGS[@]+"${SANDBOX_PROXY_ARGS[@]}"} \
      "$MAGPIE_BIN" "$@"
  }
  if [ "$_IS_EXEC" = 1 ]; then
    MAGPIE_SANDBOX_DIR="$sb"
    echo "[sandbox] 就绪：$sb（代理：$proxy_note）" >&2
  else
    export MAGPIE_SANDBOX_DIR="$sb"
    echo "[sandbox] 就绪：$sb（代理：$proxy_note；换沙箱设 MAGPIE_SANDBOX；--online 真联网）"
  fi
}

_online=""
_rest=1
if [ "${1:-}" = "--online" ]; then
  _online="--online"
  _rest=2
fi
magpie_sandbox_init "$_online"
if [ "$_IS_EXEC" = 1 ] && [ "${!_rest:-}" = "--" ]; then
  shift "$_rest"
  m "$@"
fi

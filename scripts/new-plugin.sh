#!/usr/bin/env bash
# 从 template/ 生成新的 magpie provider 插件骨架：复制 + 全局改名（acme → <vendor>）。
#
# 用法：new-plugin.sh <vendor-id> [显示名] [目标目录]
#   vendor-id  kebab-case（如 fooai），成为 provider id 与包名成分
#   显示名     默认取 vendor-id 首字母大写；进 magpie.name 与用户可见文案
#   目标目录   默认 ./opencode-<vendor-id>-auth
#
# 生成后必做：把 BASE 换成真实 API 地址、按厂商真实端点补 loader/usage、过 SKILL.md 验证清单。
set -euo pipefail

usage() { grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
[ "${1:-}" ] || usage
case "$1" in -h|--help) usage ;; esac

vendor="$1"
display="${2:-}"
dest="${3:-./opencode-${vendor}-auth}"

# vendor-id 必须是合法 kebab-case（provider id 同时是 agent 引用前缀与目录名成分）
if ! [[ "$vendor" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "[new-plugin] vendor-id 必须是小写字母/数字/连字符的 kebab-case：$vendor" >&2
  exit 1
fi
if [ -e "$dest" ]; then
  echo "[new-plugin] 目标已存在，不覆盖：$dest" >&2
  exit 1
fi
display="${display:-${vendor^}}"
# 显示名会被拼进代码（export const <display>AuthPlugin），必须标识符安全；
# 想要含空格/符号的展示名：先用标识符安全名生成，再手工编辑各文件的字符串
if ! [[ "$display" =~ ^[A-Za-z][A-Za-z0-9_]*$ ]]; then
  echo "[new-plugin] 显示名必须是标识符安全字符（字母开头，仅字母/数字/下划线）：$display" >&2
  echo "[new-plugin] 想要更自由的展示名？先用安全名生成，再手工改各文件字符串与 magpie.name" >&2
  exit 1
fi

# sed 替换用 | 作分隔；显示名里转义分隔符与替换特殊字符
esc() { printf '%s' "$1" | sed -e 's/[\/&|]/\\&/g'; }

src="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/template"
mkdir -p "$dest"
for f in package.json index.mjs README.md; do
  sed -e "s|Acme|$(esc "$display")|g" -e "s|acme|${vendor}|g" "$src/$f" > "$dest/$f"
done

if command -v node > /dev/null 2>&1; then
  if node --check "$dest/index.mjs"; then
    echo "[new-plugin] index.mjs 语法检查通过"
  else
    echo "[new-plugin] ❌ 生成物语法检查未通过（不应发生，请回报）" >&2
    exit 1
  fi
fi
echo "[new-plugin] 已生成 $dest（provider id: $vendor，显示名: $display）"
echo "下一步：改 BASE 为真实 API 地址 → 沙箱 m plugin add ./$(basename "$dest") → m plugin login $vendor"

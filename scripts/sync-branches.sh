#!/usr/bin/env bash
# 从 main 的技能目录重新生成单技能分支（分支根目录 = 技能内容）
#
# 用法:
#   ./scripts/sync-branches.sh               # 同步全部技能
#   ./scripts/sync-branches.sh ui-design     # 只同步指定技能（分支名或路径）
#   ./scripts/sync-branches.sh --push        # 同步后推送所有分支
#
# 只在 main 上改技能，本脚本负责把内容镜像到各单技能分支。
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

SKILL_PATHS=(
  "design/ui-design"
  "research/research-architecture-figure"
  "research/literature-collection"
  "research/deep-research"
  "presentation/constructivist-ppt"
  "presentation/huayu-hanako-ppt"
  "productivity/auto-resume-tasks"
  "meta/skill-creator-cn"
  "meta/magpie-plugin-dev"
  "creative/ascii-web-design"
)

push=0
filters=()
for arg in "$@"; do
  case "$arg" in
    --push) push=1 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) filters+=("$arg") ;;
  esac
done

main_sha=$(git rev-parse --short main)
synced=0

for path in "${SKILL_PATHS[@]}"; do
  branch=$(basename "$path")

  if [ ${#filters[@]} -gt 0 ]; then
    match=0
    for f in "${filters[@]}"; do
      [ "$f" = "$branch" ] && match=1
      [ "$f" = "$path" ] && match=1
    done
    [ "$match" -eq 1 ] || continue
  fi

  if ! git cat-file -e "main:$path" 2>/dev/null; then
    echo "skip: main:$path 不存在" >&2
    continue
  fi

  tree=$(git rev-parse "main:$path")

  if git rev-parse --verify -q "refs/heads/$branch" >/dev/null; then
    if [ "$tree" = "$(git rev-parse "refs/heads/$branch^{tree}")" ]; then
      echo "unchanged: $branch"
      continue
    fi
    commit=$(git commit-tree "$tree" -p "refs/heads/$branch" -m "sync: $path @ main $main_sha")
    git branch -f "$branch" "$commit"
  else
    commit=$(git commit-tree "$tree" -m "sync: $path @ main $main_sha")
    git branch "$branch" "$commit"
  fi

  echo "synced: $branch <- $path"
  synced=$((synced + 1))
done

if [ "$push" -eq 1 ]; then
  git push origin --all
fi

echo "done: $synced branch(es) updated"

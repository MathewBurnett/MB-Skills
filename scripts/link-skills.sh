#!/usr/bin/env bash
set -euo pipefail

# Dev-only: links every skill in this repo into ~/.claude/skills as a symlink,
# so `git pull` here updates the skills everywhere. Not the supported installer
# for other people — they should use the plugin (see README).

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

# If $DEST resolves back into this repo, the per-skill symlinks below would be
# written into the repo's own skills/ tree. Bail rather than pollute it.
if [ -L "$DEST" ]; then
  resolved="$(readlink -f "$DEST")"
  case "$resolved" in
    "$REPO" | "$REPO"/*)
      echo "error: $DEST is a symlink into this repo ($resolved)." >&2
      echo "Remove it (rm \"$DEST\") and re-run; it'll be recreated as a real dir." >&2
      exit 1
      ;;
  esac
fi

mkdir -p "$DEST"

linked=0
while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  target="$DEST/$(basename "$src")"

  # A real dir here is a hand-installed copy; replace it with the symlink.
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    rm -rf "$target"
  fi

  ln -sfn "$src" "$target"
  echo "linked $(basename "$src") -> $src"
  linked=$((linked + 1))
done < <(find "$REPO/skills" -name SKILL.md -not -path '*/deprecated/*' -print0)

echo "$linked skill(s) linked into $DEST"

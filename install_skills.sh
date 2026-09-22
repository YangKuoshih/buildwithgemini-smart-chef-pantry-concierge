#!/usr/bin/env bash
# ==============================================================================
# Script: install_skills.sh
# Purpose: Installs bundled agent skills into your local Antigravity harness
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"

MODE="${1:-workspace}"

if [[ "$MODE" == "--global" || "$MODE" == "global" ]]; then
    TARGET_DIR="$HOME/.gemini/config/skills"
    echo "📦 Installing skills globally to: $TARGET_DIR"
else
    TARGET_DIR="$SCRIPT_DIR/.agents/skills"
    echo "📦 Installing skills locally to workspace: $TARGET_DIR"
fi

mkdir -p "$TARGET_DIR"

COUNT=0
for cat_dir in "$SKILLS_SRC"/0*; do
    if [[ -d "$cat_dir" ]]; then
        for skill_dir in "$cat_dir"/*; do
            if [[ -d "$skill_dir" && -f "$skill_dir/SKILL.md" ]]; then
                skill_name="$(basename "$skill_dir")"
                cp -r "$skill_dir" "$TARGET_DIR/$skill_name"
                echo "  ✓ Installed $skill_name"
                COUNT=$((COUNT + 1))
            fi
        done
    fi
done

echo ""
echo "🎉 Successfully installed $COUNT skills to $TARGET_DIR!"
echo "Antigravity will now automatically detect and load these skills."

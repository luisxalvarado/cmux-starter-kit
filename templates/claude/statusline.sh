#!/bin/bash
# Claude Code status line for every thread.
# Line 1: folder · git branch · open pull request (when there is one).
# (Printed as one row.) Model · context used · 5 hour and week plan usage, each with a countdown to its reset.
# Context colors follow the rule of keeping a thread under 50%:
#   green under 30%, yellow 30 to 49%, red at 50% or more with a /pre-compact nudge.
# Settings: refreshInterval 60 in ~/.claude/settings.json keeps the countdowns ticking.
input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name // "Claude"' | sed 's/ (1M context)//')
pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
five=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' | cut -d. -f1)
five_reset=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty' | cut -d. -f1)
week=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' | cut -d. -f1)
week_reset=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty' | cut -d. -f1)
dir=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
pr_num=$(echo "$input" | jq -r '.pr.number // empty')
pr_state=$(echo "$input" | jq -r '.pr.review_state // empty')
folder=$(basename "$dir")

# Colours match the Midnight theme. Change the hex values to restyle.
rgb() { printf '\033[38;2;%d;%d;%dm' "$((16#${1:1:2}))" "$((16#${1:3:2}))" "$((16#${1:5:2}))"; }
green=$(rgb "#22ab94"); yellow=$(rgb "#f7c948"); red=$(rgb "#f7525f")   # green, gold, red
cyan=$(rgb "#4dd0e1"); blue=$(rgb "#5b9cf6"); teal=$(rgb "#0097a7")      # cyan, blue, teal
text=$(rgb "#ffffff"); grey=$(rgb "#b2b5be"); muted=$(rgb "#787b86")
dim=$(rgb "#50535e"); empty=$(rgb "#29404b"); bold=$'\033[1m'; reset=$'\033[0m'

# Time left until a reset, like 4h19m or 1d8h.
left() {
  local s=$(( $1 - $(date +%s) ))
  [ "$s" -lt 0 ] && s=0
  local d=$(( s / 86400 )) h=$(( s % 86400 / 3600 )) m=$(( s % 3600 / 60 ))
  if [ "$d" -gt 0 ]; then printf '%dd%dh' "$d" "$h"
  elif [ "$h" -gt 0 ]; then printf '%dh%02dm' "$h" "$m"
  else printf '%dm' "$m"; fi
}

# Plan usage as small 5-block bars: green under 50%, yellow 50 to 79%, red at 80% or more.
minibar() {
  local p=$1 c n b=""
  if [ "$p" -ge 80 ]; then c=$red; elif [ "$p" -ge 50 ]; then c=$yellow; else c=$green; fi
  n=$(( (p + 10) / 20 )); [ "$n" -gt 5 ] && n=5
  for i in 1 2 3 4 5; do if [ "$i" -le "$n" ]; then b="${b}${c}▓"; else b="${b}${empty}░"; fi; done
  printf '%s %s%s%%%s' "$b" "$c" "$p" "$reset"
}

# Line 1: where you are.
branch=""
[ -n "$dir" ] && branch=$(git -C "$dir" branch --show-current 2>/dev/null)
line1="${bold}${blue}${folder}${reset}"
[ -n "$branch" ] && line1="${line1} ${dim}·${reset} ${cyan}${branch}${reset}"
if [ -n "$pr_num" ]; then
  line1="${line1} ${dim}·${reset} ${teal}PR #${pr_num}${reset}"
  [ -n "$pr_state" ] && line1="${line1} ${dim}(${pr_state})${reset}"
fi

# Line 2: how full this thread is and how much plan is left.
if [ "$pct" -ge 50 ]; then color=$red; nudge=" ${red}run /pre-compact${reset}"
elif [ "$pct" -ge 30 ]; then color=$yellow; nudge=""
else color=$green; nudge=""; fi
filled=$((pct / 10)); [ "$filled" -gt 10 ] && filled=10
bar=""
for i in $(seq 1 10); do if [ "$i" -le "$filled" ]; then bar="${bar}${color}▓"; else bar="${bar}${empty}░"; fi; done

line2="${text}${model}${reset} ${dim}·${reset} ${grey}CX${reset} ${bar} ${color}${pct}%${reset}${nudge}"
if [ -n "$five" ]; then
  line2="${line2} ${dim}·${reset} ${grey}5h${reset} $(minibar "$five")"
  [ -n "$five_reset" ] && line2="${line2} ${muted}($(left "$five_reset") left)${reset}"
fi
if [ -n "$week" ]; then
  line2="${line2} ${dim}·${reset} ${grey}WK${reset} $(minibar "$week")"
  [ -n "$week_reset" ] && line2="${line2} ${muted}($(left "$week_reset") left)${reset}"
fi

# One row: folder · branch · PR, then model and usage.
if [ -n "$folder" ]; then echo "${line1} ${dim}·${reset} ${line2}"; else echo "${line2}"; fi

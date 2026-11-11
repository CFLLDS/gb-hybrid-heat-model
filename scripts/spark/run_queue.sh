#!/bin/bash
# Cheap-window GPU queue (Craig, 5 Nov 2026: "kick the multi million scenario training off on the cheap electric time ..
# we don't want to pull peak electrons training a system to use cheap electrons"). Cron 23:35 local: runs each
# ~/cfl-model/queue/*.sh in name order, each killed at the 05:25 deadline (IOG cheap window 23:30-05:30); finished jobs
# move to queue/done/, unfinished ones stay queued for the next night. Log: ~/cfl-model/out/queue.log.
Q=$HOME/cfl-model/queue; LOG=$HOME/cfl-model/out/queue.log
mkdir -p "$Q/done"
deadline=$(date -d "05:25 tomorrow" +%s); [ "$(date +%H)" -lt 6 ] && deadline=$(date -d "05:25" +%s)
for job in "$Q"/*.sh; do
  [ -e "$job" ] || break
  left=$(( deadline - $(date +%s) )); [ "$left" -le 60 ] && { echo "$(date -Is) deadline: stop before $(basename "$job")" >> "$LOG"; break; }
  echo "$(date -Is) start $(basename "$job") (${left}s left)" >> "$LOG"
  timeout --signal=TERM --kill-after=60 "$left" bash "$job" >> "$LOG" 2>&1; rc=$?
  if [ "$rc" -eq 124 ]; then echo "$(date -Is) $(basename "$job") hit the 05:25 deadline, stays queued" >> "$LOG"; break; fi
  echo "$(date -Is) done $(basename "$job") rc=$rc" >> "$LOG"; mv "$job" "$Q/done/"
done

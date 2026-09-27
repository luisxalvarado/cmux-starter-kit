# Improve ledger (append only)

Every lesson the improve loop learns. One row per lesson; when the same cause shows up again, update its `count`
and `last seen` instead of adding a row. Written by `/improve`; reviewed weekly by `/improve weekly`. Signals
waiting to be processed live in `pending.jsonl` (written automatically by the Stop hook `signal_hook.py`).

| id | first seen | last seen | trigger | symptom | root cause | fix path | fix type | verified how | count | status |
|---|---|---|---|---|---|---|---|---|---|---|

# AEL Agent v0.5 Usage

## Start system

Run unified launcher:

```bash
python3 -m ael up
```

Optional:

```bash
python3 -m ael up --host 0.0.0.0 --port 8844 --queue queue
```

## Submit task

Natural language:

```bash
python3 -m ael submit "toggle gpio on esp32"
```

JSON mode:

```bash
python3 -m ael submit '{"title":"t","kind":"noop","payload":{}}' --json
```

or

```bash
python3 -m ael submit path/to/task.json --json
```

## Check status

```bash
python3 -m ael status
```

The command reads queue states from:

- `queue/running`
- `queue/done`

## Expected flow

1. `ael up` starts Bridge + Agent loop
2. `ael submit ...` posts task to Bridge
3. Agent executes task from queue
4. Result is available through queue state and Bridge API

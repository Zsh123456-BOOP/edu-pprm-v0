# DeepSeek Small-Batch Validation

## Result

Use `deepseek-v4-flash` for the full 240-sample real labeling run.

## Why

- flash: 20/20 success, avg latency 2.658s, parse 1.0, schema 1.0
- pro: 2/2 success, avg latency 4.23s, parse 1.0, schema 1.0

## Fix Applied

The first small-batch attempts failed with HTTP 400 because `reasoning_effort` was still set while `thinking.type` was disabled. Card 3.9 fixes the small-batch runner to clear `reasoning_effort` for compact throughput prompts.

## Next Step

Run the full 240-sample real labeling with `deepseek-v4-flash`, then rerun the Gate 3 evaluation. Do not train until those real labels replace the fallback labels.
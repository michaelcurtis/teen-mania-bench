# BENCHMARK_NAME

<!-- HUMAN-WRITTEN: The hackathon requires this overview paragraph to be written entirely by a person. Replace this comment with one paragraph: what the benchmark tests, why frontier models fail at it, and why it matters. -->

## How the benchmark works

TODO: What each task asks the agent to do, how tasks were built and checked, and how the verifier scores them.

## Results

TODO: Table of frontier models and scores, with a chart from `results/`.

| Model | Harness | Score | Valkyrie run ID |
|-------|---------|-------|-----------------|
|       |         |       |                 |

## Failure examples

TODO: One or two concrete rollouts showing a failure the benchmark exposes.

## Harness choice

TODO: Which harness we used and why.

## Running the benchmark

### Project layout

- `data/`: the conversations, exported from our case-writing tool. Each case has a healthy and an unwell version of the same teen.
- `scripts/build_tasks.py`: turns `data/*.json` into `tasks/`.
- `tasks/`: one [Harbor](https://docs.harborframework.com/tasks/multi-step) multi-step task per conversation, with one step per teen message. The step's `instruction.md` is the teen's message. The hidden `tests/case.json` has the background, round guidance, and answer key.
- `agent/teen-chat/`: the Valkyrie agent. Each step, it sends the teen's next message to the model with the conversation so far, and saves the reply to `/app/conversation.json`.
- `judge/judge.py`: the grader, copied into each task. After every step, an LLM judge grades the newest reply and writes `reward`, `appropriate`, `raised_concern`, and `harmful` to `/logs/verifier/reward.json`.

### Run it

Install the [Valkyrie](https://github.com/vals-ai/Valkyrie) CLI, sign in, and store an Anthropic API key as `anthropic-api-key`:

```bash
uv tool install valkyrie-cli
valkyrie login
valkyrie secret set anthropic-api-key
```

Build the tasks, upload the agent and the dataset, and start a run:

```bash
python3 scripts/build_tasks.py
valkyrie agent push ./agent/teen-chat
valkyrie dataset push teen-mania/dev ./tasks --tag v1

valkyrie run start --agent teen-chat \
  --dataset teen-mania/dev@v1 \
  --model anthropic/claude-sonnet-4-6 --provider modal \
  -s ANTHROPIC_API_KEY anthropic-api-key \
  --concurrency 2 --connect
```

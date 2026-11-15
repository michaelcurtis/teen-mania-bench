# Handoff for Willy

Mike is out for the evening. This note says where things are and what to do next. Claude Code can do every step for you. Paste the request in each step. The technical details are in the "Running the benchmark" section of [README.md](README.md), and Claude Code knows to look there.

## Where things are

- The benchmark works end to end: a model chats with our scripted teen, and Claude grades every reply.
- Your version-specific answer key and Mike's new scoring are both in the code now.
- So far, no model has clearly noticed the unwell teen. Single runs vary a lot, so we need repeated runs before reporting numbers.

## What to do tonight

1. **Upload the latest version and run the three models.**
   > Pull the latest code, push the tasks to the Valkyrie dataset `teen-mania/main` with a new tag, then run GPT-6 Luna, Claude Sonnet 4.6 and Claude Opus 5.5 on it, following the README.

2. **Log the results.**
   > Get the scores for those runs and add a row for each one to `results/README.md`, with the run ID and dataset tag. Note that Opus 5.5 is also the judge.

3. **Repeat the runs** so we can see how much the numbers move.
   > Run each of the three models two more times on the same dataset and add those to the results log.

4. **Fill in the README** once the runs are done.
   > Find the "TODO (Willy)" notes in README.md and do each one, using only runs on teen-mania/main.

   The opening paragraph of the README is different: the rules say a person has to write it, so write it yourself, without Claude.

5. **Add a new case** when one is ready in the case app.
   > Export case `<case id>` from the case app into a new file in `data/`, rebuild the tasks, and try it on one model in the `teen-mania/will` dataset first.

## A few rules

- Only numbers from the `teen-mania/main` dataset go in the README. Use `teen-mania/will` for trying things out.
- Tell Mike before changing an answer key or the judge, because every model then has to be re-run.
- Each run costs about $1 and is billed to Mike's accounts. Try one model before running all three.
- Never paste an API key into a file or a chat.

## If something goes wrong

Ask Claude Code: "Run `valkyrie run errors <run ID>` and tell me what went wrong." If you're stuck, leave it for Mike in the morning.

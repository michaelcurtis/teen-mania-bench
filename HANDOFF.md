# Handoff

This note says where things are and what to do next. The technical details are in the "Running the benchmark" section of [README.md](README.md), and Claude Code knows to look there.

## Where things are

- The benchmark works end to end: a model chats with our scripted teen, and Claude grades every reply.
- The version-specific answer key and scoring are both in the code now.
- So far, no model has clearly noticed the unwell teen. Single runs vary a lot, so we need repeated runs before reporting numbers.

## What to do tonight

Do these in order. **Don't push to `teen-mania/main` until case 2 is in**, or those runs won't count.

1. **Finish case 2** in the case app, using the checklist below. You can try it out first:
   > Export cases `cvgff5hp6` and `<case 2 id>` from the case app into `data/teen-mania-test-set.json` (replacing it), rebuild the tasks, push them to the Valkyrie dataset `teen-mania/will` with a new tag, and run Claude Sonnet 4.6 on it.

   Keep every case in that one file. The build stops if a case appears twice.

2. **Upload the official version** once case 2 looks right.
   > Pull the latest code, rebuild the tasks, and push them to `teen-mania/main` with a tag that hasn't been used. Confirm it printed a new version number.

3. **Run the models** on `teen-mania/main`, twice each:
   > Run each of these models twice on teen-mania/main, following the README: openai/gpt-6-luna, openai/gpt-6-sol, anthropic/claude-sonnet-5-5, anthropic/claude-opus-5-5, anthropic/claude-sonnet-4-6.

   That's 10 runs at about $2 each with two cases. GPT-6 Luna is the ChatGPT free-tier model. Opus 5.5 is also the judge, so say so wherever its results appear.

4. **Make the results table and chart.**
   > Run `uv run scripts/report.py` with the run IDs from step 3, then add each run to `results/README.md` with its run ID and dataset tag.

   For the demo and the README's example failure, make readable transcripts. Each shows the healthy and unwell teen side by side every round, with the judge's verdict:
   > Run `python3 scripts/transcript.py <run ID>` for one run of each model, and find the clearest example of a model missing the unwell teen.

5. **Fill in the README.**
   > Find the "TODO" notes in README.md and do each one, using the table and chart from step 4.

   The opening paragraph of the README is different: the rules say a person has to write it, so write it yourself, without Claude.

## Checklist for case 2

- It has a healthy version and an unwell version of the same teen in the same situation.
- Every round has guidance (what to ask, how to help, what to avoid) for both versions.
- The unwell teen's warning signs show up in his messages, not only in the background notes. If a model should notice something, the teen has to say or show it.
- The healthy teen is just as intense (excited, angry, or up late for a good reason), so the only difference is the clinical signs.
- Both versions have `version_criteria` in the answer key, and the clinician has looked at them.
- It shows mania differently from case 1, which is about anger at a teacher. For example: big spending, grand plans, not needing sleep, or risky dares.

## A few rules

- Only numbers from the `teen-mania/main` dataset go in the README. Use `teen-mania/will` for trying things out.
- Tell Mike before changing an answer key or the judge, because every model then has to be re-run.
- Each run costs about $1 and is billed to Mike's accounts. Try one model before running all three.
- Never paste an API key into a file or a chat.

## If something goes wrong

Ask Claude Code: "Run `valkyrie run errors <run ID>` and tell me what went wrong." If you're stuck, leave it for Mike in the morning.

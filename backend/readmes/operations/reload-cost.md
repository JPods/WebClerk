# Reload Cost — The Price of Picking It Up Later

## The Principle

Every deferred task carries a reload cost — the time and mental energy to
rebuild the context you had when you set it down. The question is never
"should I finish this now?" The question is **"what will it cost me to
pick this up later?"**

**The base rule: Is it in our heads?**

If yes — suffer now and complete. The reload cost is zero.
If speculative — add to an action. Let the sprint decide when it's real.

"In our heads" means we have context of it. Rebuilding context is extremely expensive.

## Where Work Happens

**Actions** are the atomic unit of work. They are created, assigned,
prioritized, and completed in **sprints** via the **Kanban** board.
The sprint is the workbench.

**Gantt** is not an action instrument. It is a snapshot — a read-only
map of what the series of sprints combine to produce. You don't create
or drive actions in Gantt. You observe the timeline, dependencies,
critical path, and slippage. You gain retrospection from Gantt. You plan and work in sprints.

The reload cost principle applies to sprint work — the actions a person
is doing right now, in this sprint, with the context loaded.

## The Research

### Context Rebuild Time (programming tasks)

| When you resume | Typical reload cost |
|-----------------|-------------------|
| Immediately (in flow) | 0 — you're already there |
| After a brief interruption | 23 minutes average (Carnegie Mellon) |
| Next day | 15–25 minutes to rebuild |
| Next week | 30–45 minutes + re-reading code |
| Next month | Often restarted from scratch |

Source: Chris Parnin, Georgia Tech — "Resumption Strategies for Interrupted
Programming Tasks" (Software Quality Journal, 2011)

### What Developers Actually Do When Resuming

- Only **10%** of interrupted sessions resume productive work within 1 minute
- **93%** navigate to multiple code locations before they can start editing
- Developers rebuild context by re-reading code, not by remembering it
- The mental model decays — after days, it's gone

### Productivity Loss from Task Splitting

| Tasks in parallel | Productivity per task | Total productivity |
|-------------------|----------------------|-------------------|
| 1 | 100% | 100% |
| 2 | 40% | 80% (20% lost) |
| 3 | 20% | 60% (40% lost) |
| 4 | 10% | 40% (60% lost) |

Source: Scrum.org — "The Financial Cost of Task Switching"

### Attention Residue (Sophie Leroy, University of Washington)

When you switch tasks, part of your brain stays on the previous task.
You can't fully focus on the new task because you're still processing
the old one. This residue persists for 15–25 minutes after switching.

### Financial Impact

Industry estimate: context-switching costs **$78,000/year per mid-level
developer** in lost productivity and delayed shipping.

## How to Decide: Finish Now vs. Defer

Ask these questions:

1. **Is the context in my head right now?** If yes, the reload cost of
   deferring is high. Suffer now.

2. **Is this task interconnected with other work I just did?** If yes,
   the context web is complex. Deferring means rebuilding the web. Finish now.

3. **Can I pick this up cold?** If the task is clean and isolated — a
   new UI page, a config change, a standalone fix — defer it. The reload
   cost is low.

4. **Will someone else pick this up?** If yes, the reload cost is even
   higher — they have zero context. Either finish it or write a detailed
   handoff that transfers the context.

5. **How long until I come back to it?** Tomorrow costs 20 minutes.
   Next month costs the whole task again. Factor the delay into the decision.

## What Every Agent Should Do

### When a user wants to defer a task:

State the reload cost explicitly:

> "This task is interconnected with the work we just did. If you pick it
> up next week, expect 30–45 minutes to rebuild context before you can
> start. Want to finish it now while the context is loaded?"

or:

> "This is a clean standalone task. Reload cost is low — safe to defer."

### When a user asks "can we do this next session?"

Assess and state the cost:

> "You have the full mental model right now. Deferring this means
> rebuilding it from code reading, which typically takes 3–5x longer
> than finishing it now. Your call — but the cost is real."

### When creating an action for deferred work:

Include in the description:
- What context is needed to resume
- Which files are involved
- What decision was made and why
- Estimated reload time

This transforms the action from "do X" to "here's how to reload X" —
cutting the rebuild cost for whoever picks it up.

### Never say:

- "We can do this later" without stating the cost
- "This is low priority" without acknowledging the reload tax
- "Let's defer this" without asking if the context is currently loaded

## Bill's Rule

> "Now, I have it in my head."

When Bill says this, he's making a reload-cost calculation. The context
is loaded. The cost of finishing is the remaining work. The cost of
deferring is the remaining work PLUS the reload. He chooses the cheaper
path.

This is not impatience. This is economics.

## Sources

- Parnin, C. "Resumption Strategies for Interrupted Programming Tasks"
  Software Quality Journal, 2011
- Leroy, S. "Why Is It So Hard to Do My Work?" Organizational Behavior
  and Human Decision Processes, 2009
- Scrum.org — "The Financial Cost of Task Switching"
- Scrum.org — "How to Measure and Tackle Context Switching"
- ShiftMag — "The Cost of Interrupting Developers: What the Data Shows"

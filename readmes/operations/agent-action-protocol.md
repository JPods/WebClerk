# Agent Action Protocol

## The Rule

Every agent on the team — Alice, Allie, Claude, Noelle — has standing
authority to create action records when they see something that needs doing.

No waiting to be asked. No holding observations until session end.
See it, document it, assign it.

## How It Works

1. Agent observes something: a missing widget, a layout improvement,
   a field that should be a select list, a pattern that repeats
2. Agent creates an Action record:
   - **action**: what needs to be done
   - **description**: why it matters, what was observed
   - **assigned_to**: the agent who should review it
   - **project_id**: the relevant project (or WC3 Development)
   - **priority**: agent's assessment
   - **difficulty**: agent's estimate (Fibonacci: 1, 4, 8, 13, 21)
   - **status**: "open"
3. Humans review all agent recommendations in the sprint

## Who Creates What

### Alice
- Widget suggestions based on field usage patterns
- Data quality observations (fields always empty, always the same value)
- Layout improvements based on user behavior (which fields are edited
  together, which are never touched)
- Reports to WC_HQ (ourselves for now) with recommendations

### Claude Code
- Technical debt spotted during coding sessions
- Missing tests, incomplete error handling
- Architecture decisions that need follow-up
- Reload cost warnings ("this should be finished now, not deferred")

### Allie
- Cross-domain patterns from nightly synthesis
- Stale documentation or outdated readmes
- Lessons from TFTS arcs that need to become rules
- Missing agent Understandings

### Noelle
- Network design validation failures
- Build pipeline improvements
- Station template issues

## Review Process

Every sprint review includes agent-created actions. They appear in the
Kanban like any other action. The team:
1. Reviews each recommendation
2. Accepts (moves to sprint backlog) or defers (with reason)
3. Never deletes — a rejected recommendation is still a data point

## The Principle

Agents are team members, not tools. A team member who sees a problem
and doesn't say anything is not participating. Every observation has
value — even wrong ones reveal what the agent is paying attention to.

The cost of a false recommendation is one action record reviewed and
rejected. The cost of a missed recommendation is a bug in production
or a user struggling with a bad form layout.

Create the action. Let the sprint decide.

# Condition-based waiting

Flaky tests often guess at timing with fixed delays. That creates a race: the test passes on a fast
machine and fails under load, in parallel, or on a slow runner. **Wait for the condition you
actually care about, not for a guess about how long it takes.**

## Contents

- When to use it
- The core pattern
- Quick patterns
- The generic helper
- Helpers for an event stream
- A worked example
- Mistakes
- When a fixed delay is right

## When to use it

```
does the test sleep or delay?
    no  -> nothing to do
    yes -> is the test about timing itself (a debounce, a throttle, a tick interval)?
               yes -> keep the delay, and document why (see "When a fixed delay is right")
               no  -> replace it with a wait on the condition
```

Use it when:
- a test has a fixed delay (a sleep, a timer, a "wait a bit");
- a test is flaky: it passes sometimes, and fails under load;
- tests time out when run in parallel;
- a test waits for an asynchronous operation to finish.

Do not use it when the test is about real timing behavior. Even then, say in a comment why the delay
is there.

## The core pattern

```
BEFORE  -- guessing at timing
        sleep(50ms)
        result = getResult()
        expect(result).toExist()

AFTER   -- waiting for the condition
        waitFor(() => getResult(), "the result")
        result = getResult()
        expect(result).toExist()
```

## Quick patterns

| Scenario | Pattern |
|----------|---------|
| Wait for an event | `waitFor(() => events.find(e => e.type == "DONE"), "the DONE event")` |
| Wait for a state | `waitFor(() => machine.state == "ready", "the ready state")` |
| Wait for a count | `waitFor(() => items.length >= 5, "five items")` |
| Wait for a file | `waitFor(() => fileExists(path), "the output file")` |
| A compound condition | `waitFor(() => obj.ready and obj.value > 10, "a ready value over 10")` |

## The generic helper

```
waitFor(condition, description, timeout = 5s):
    start = now()
    loop:
        result = condition()            -- call it every time: never cache the state before the loop
        if result is truthy:
            return result
        if now() - start > timeout:
            fail "timed out waiting for " + description + " after " + timeout
        pause(10ms)                     -- poll every 10ms: often enough, without burning the processor
```

The description is not optional: it is what the failure message says, and a timeout that only says
"timed out" sends the next reader back to debugging.

## Helpers for an event stream

When the system under test records events (a thread of messages, a job log, a queue), wrap the
generic poll in helpers named for the domain. Each one reads fresh events on every poll, and each
fails with a message that says what it was waiting for.

```
waitForEvent(manager, threadId, eventType, timeout = 5s) -> the first matching event:
    poll every 10ms:
        events = manager.getEvents(threadId)
        event = first of events where event.type == eventType
        if event: return event
        if timed out: fail "timed out waiting for " + eventType + " event after " + timeout

waitForEventCount(manager, threadId, eventType, count, timeout = 5s) -> the matching events:
    poll every 10ms:
        matching = all of manager.getEvents(threadId) where event.type == eventType
        if matching.length >= count: return matching
        if timed out:
            fail "timed out waiting for " + count + " " + eventType + " events after " + timeout
                 + " (got " + matching.length + ")"

waitForEventMatch(manager, threadId, predicate, description, timeout = 5s) -> the first match:
    poll every 10ms:
        event = first of manager.getEvents(threadId) where predicate(event)
        if event: return event
        if timed out: fail "timed out waiting for " + description + " after " + timeout
```

Usage:

```
waitForEvent(threads, agentThreadId, "TOOL_RESULT")
waitForEventCount(threads, agentThreadId, "AGENT_MESSAGE", 2)     -- the reply and its continuation
waitForEventMatch(threads, agentThreadId,
                  e => e.type == "TOOL_RESULT" and e.data.id == "call_123",
                  "TOOL_RESULT with id call_123")
```

## A worked example

```
BEFORE (flaky)
    reply = agent.sendMessage("Execute tools")
    sleep(300ms)                       -- hope the tools have started
    agent.abort()
    await reply
    sleep(50ms)                        -- hope the results have arrived
    expect(toolResults.length).toBe(2) -- fails at random

AFTER (reliable)
    reply = agent.sendMessage("Execute tools")
    waitForEventCount(threads, threadId, "TOOL_CALL", 2)     -- the tools have started
    agent.abort()
    await reply
    waitForEventCount(threads, threadId, "TOOL_RESULT", 2)   -- the results have arrived
    expect(toolResults.length).toBe(2)                       -- passes every time
```

Replacing the guesses this way fixed fifteen flaky tests across three files in one session: the pass
rate went from 60% to 100%, and the suite ran about 40% faster, because no test waited longer than
its condition took.

## Mistakes

| Mistake | Fix |
|---------|-----|
| Polling too fast (every 1ms) wastes the processor | poll every 10ms |
| No timeout: the loop runs forever if the condition never holds | always set a timeout, with a clear message |
| Stale data: the state was read once, before the loop | call the getter inside the loop, every time |
| A timeout with no description | name what you were waiting for |

A wait that times out **fails the test**. It never hangs the run, and never waits for a person
(`apm:test-first`, "No test waits on a person").

## When a fixed delay is right

```
waitForEvent(manager, threadId, "TOOL_STARTED")   -- first: wait for the triggering condition
sleep(200ms)                                      -- then: wait for the timed behavior
-- the tool ticks every 100ms; two ticks are needed to see partial output, so 200ms is derived, not guessed
```

Three requirements, all of them:
1. First wait for the triggering condition.
2. Base the delay on known timing (an interval the code defines), not on a guess.
3. Say why in a comment next to the delay.

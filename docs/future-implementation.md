# Future implementation

Designs that are valuable but not lightweight. None of these are built for the challenge. The current design is `docs/superpowers/specs/2026-11-04-ca-message-app-design.md`.

## Tool-calling agent

Replace the chat layer with an agent that loops: the model chooses a tool, reads the result, and repeats until it has three candidates.

- **Tools:** find a client, read the conversation history, search products, read the brand rules, run the pipeline, run the code checks.
- **Guardrails:** a limit on steps and cost, read-only tools, and nothing sent to a client without the CA.
- **Evaluation:** the same fifty cases, plus a check that each tool call was needed and that the agent did not invent a client or a product.
- **Risk:** the path changes from run to run, so results are harder to repeat than with the fixed pipeline.
- **Framework:** LangGraph, for its state, loops, and pauses for the CA's approval.

## Feedback loop from picks and edits

- Use logged Copy and Edit events as few-shot examples, chosen by scenario, strategy, and client.
- Treat an edit as a stronger signal than a pick. Store what was changed.
- Each change to the examples is a new generator version, scored on the fifty cases before use.
- Add outcome signals: whether the client replied, booked, or bought.

## Per-client memory

- A memory record per client: tone that worked, topics to avoid, preferred contact rhythm.
- Keep what the CA prefers separate from what the client prefers.
- Expire stale notes, and let the CA see and correct the memory.

## Real data sources

- **Client list builder:** pick today's clients and scenarios from triggers such as a birthday, days since purchase, months since a visit, or an upcoming event.
- **CRM and WeChat Work:** read client records and conversation history instead of the fictional store.
- **Product catalog search:** retrieval, possibly with a vector database, so recommendations come from the live catalog.
- **Morning list view:** each of the CA's clients for the day, with three drafts to review.

## Evaluation at scale

- A person hand-scores a sample of each run in Langfuse, to check and tune the model judge.
- Track agreement between the judge and people over versions.
- Use the GLM Batch API for judge scoring and large reruns. It costs half the normal price, but results can take up to 24 hours, each file holds one model, and the account needs real-name verification. It does not suit the live page.

## Product hardening

- Detect the scenario from the client's message instead of asking the CA.
- Logins and one workspace per CA, deployment, audit logs.
- Privacy review of real client data, retention limits, and redaction in traces.

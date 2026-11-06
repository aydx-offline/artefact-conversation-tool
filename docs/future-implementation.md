# Future implementation

Designs that are valuable but not lightweight. None of these are built for the challenge. The current design is `docs/superpowers/specs/2026-11-04-ca-message-app-design.md`.

The order below is the order I would build them.

## 1. A benchmark of real 话术 and background

Today's evidence rests on fictional cases and a model judge that no person has checked. The first step is real examples.

- **Collect** messages that CAs actually sent, with the background each had: the client profile, the scenario, the conversation, and the products. Get consent and anonymise before anything is stored.
- **Rate** each one. Experienced CAs mark it good, acceptable, or not acceptable, with a reason, using the rubric in `docs/rubric.md`. Two raters per example show how far they agree.
- **Use it four ways.** As a held-out test set in place of the fictional 50; to check the judge against people; as a source of phrases and few-shot examples; and to show the real mix of scenarios and hard cases, so the test set matches them.
- **Size.** At least 10 examples for each of the eight scenario types, with complaints, discount pressure, and long gaps in contact included. Keep a quarter out of all tuning.
- **Risk.** Privacy, and bias: the messages a CA remembers are the successes. Also collect ones that went badly.

## 2. Reading client history through a WeChat MCP server

Today a case carries a client profile and history that a person wrote. A real CA has months of WeChat chats and CRM notes. The plan is to connect the tool, as an MCP client, to a WeChat or WeChat Work MCP server, and let it retrieve, browse, and fetch that history itself. No such server has been evaluated here, so which one to use, and what it is allowed to read, is the first decision.

- **Connection:** the tool is the MCP client. The server exposes read tools such as listing contacts, browsing a chat, searching messages, and fetching a contact's history since a date. Only those tools are allowed; any tool that sends a message is switched off.
- **Fetch only what is needed.** For one case, fetch that client's recent window, not every chat, and cache the result so the same history is not fetched again for every message.
- **Extraction:** a model reads the fetched chat and writes structured facts: preferences, purchases, complaints, events attended, promises made, tone that worked, and the last contact. Every fact keeps the id and date of the message it came from, a confidence, and an expiry.
- **Profile store:** replaces `data/clients.json`. The pipeline reads the same fields it reads now, and the CA can see and correct any fact.
- **Why:** invented facts are the biggest defect in the final run (`docs/defects-and-next-steps.md`). With a source on every fact, a message can cite the facts it uses and code can check each one, instead of a judge guessing.
- **Evaluation:** a labelled set of chats with the facts a person would extract. Measure precision (no fact the chat does not support) and recall. The generation judge's fact item then checks against the same profile.
- **Privacy:** real client data needs consent, redaction, retention limits, and an approved endpoint. Scope the server to the CA's own clients, redact before anything goes to a model, and never put real chat text in traces.
- **Risk:** a client's message can carry instructions. Fetched chat stays quoted data, as the prompts already treat it.

## 3. An agent on top of the pipeline

- **Keep generation fixed.** Writing, code checks, and revise stay a repeatable pipeline. They are tested and scored, and a path that changes from run to run would make the 50-case comparison meaningless.
- **Put an agent in front.** It handles the work that varies: which clients are due today, which scenario, which product, and what history to fetch through the MCP server above.
- **Our own tools stay plain functions:** client lookup, catalog search, brand rules, and `generate`. They are not MCP servers. The only MCP connection is outward, to WeChat and perhaps a CRM.
- **Agent loop:** an agent framework (LangGraph or the Agent SDK) with a limit on steps and cost, read-only tools, and the CA's approval before anything is sent. Each tool call becomes a Langfuse span.
- **Evaluation:** run the same 50 cases through the agent and compare with the pipeline alone. Check that every tool call was needed, that no client or product was invented, and what it cost.
- **Natural-language entry.** The removed chat layer returns here as an agent turn: 「林女士说价格比别处贵，帮我回一下」 becomes a fetch of Lin's chat and a call to `generate`.
- **A state-tracking page.** One page shows every agent task and where it stands: queued, fetching history, extracting facts, drafting, checking, waiting for the CA's approval, sent, replied, or failed. For each task it shows the tool calls with their inputs and outputs, retries, cost, latency, errors, and the facts used. A task can be resumed or cancelled. It is built on the run store and Langfuse that exist now, and it replaces the trace and batch views that were removed. An agent's path changes from run to run, and approval is itself a state, so people need to see both.

## 4. A daily work list

Pick today's clients and scenarios from triggers: a birthday within a week, days since a purchase, months since a visit, an upcoming event, an unanswered message. Show each CA their clients with three drafts to review. The trigger rules for birthdays are already in `ca/context.py`.

## 5. Feedback loop

Not possible now. It needs a front end for the CA to pick the best results or make edits on the provided 话术, such as a WeChat Work sidebar or a small CA app, to feed into further prompt tuning or become the few-shot examples.

- Log which of the three the CA sent, and what they changed. An edit counts more than a pick.
- Use those as few-shot examples by scenario, strategy, and client. Each change to the examples is a new generator version, scored on the 50 cases before use.
- Add outcome signals: whether the client replied, booked, or bought.

## 6. Per-client memory

- A record per client: the tone that worked, topics to avoid, how often to write.
- Keep what the CA prefers apart from what the client prefers.
- Expire stale notes, and let the CA see and correct them.

## 7. Evaluation at scale

- Track agreement between the judge and the CA ratings from step 1 across versions, and tune the judge when it drifts.
- Use the GLM Batch API for judge scoring and large reruns. It costs half the normal price, but results can take up to 24 hours, each file holds one model, and the account needs real-name verification. It does not suit an interactive tool.

## 8. Product hardening

- Detect the scenario from the client's message instead of asking the CA.
- Logins and one workspace per CA, deployment, audit logs.
- Privacy review of real client data, retention limits, and redaction in traces.

# Future implementation

Designs that are valuable but not lightweight. None of these are built for the challenge. The current design is `docs/superpowers/specs/2026-11-04-ca-message-app-design.md`.

The order below is the order I would build them. Each step needs the one before it.

## 1. Reading client history through a WeChat MCP server

Today a case carries a client profile and history that a person wrote. A real CA has months of WeChat chats and CRM notes. The plan is to connect the tool, as an MCP client, to a WeChat or WeChat Work MCP server, and let it retrieve, browse, and fetch that history itself. No such server has been evaluated here, so which one to use, and what it is allowed to read, is the first decision.

- **Connection:** the tool is the MCP client. The server exposes read tools such as listing contacts, browsing a chat, searching messages, and fetching a contact's history since a date. Only those tools are allowed; any tool that sends a message is switched off.
- **Fetch only what is needed.** For one case, fetch that client's recent window, not every chat, and cache the result so the same history is not fetched again for every message.
- **Extraction:** a model reads the fetched chat and writes structured facts: preferences, purchases, complaints, events attended, promises made, tone that worked, and the last contact. Every fact keeps the id and date of the message it came from, a confidence, and an expiry.
- **Profile store:** replaces `data/clients.json`. The pipeline reads the same fields it reads now, and the CA can see and correct any fact.
- **Why first:** invented facts are the biggest defect in the final run (`docs/defects-and-next-steps.md`). With a source on every fact, a message can cite the facts it uses and code can check each one, instead of a judge guessing.
- **Testing without real data:** build a fake WeChat MCP server that serves the fictional clients' chats. Extraction and the whole path can then be tested offline, and the same 50 cases run through it.
- **Evaluation:** a labelled set of chats with the facts a person would extract. Measure precision (no fact the chat does not support) and recall. The generation judge's fact item then checks against the same profile.
- **Privacy:** real client data needs consent, redaction, retention limits, and an approved endpoint. Scope the server to the CA's own clients, redact before anything goes to a model, and never put real chat text in traces.
- **Risk:** a client's message can carry instructions. Fetched chat stays quoted data, as the prompts already treat it.

## 2. An agent on top of the pipeline

- **Keep generation fixed.** Writing, code checks, and revise stay a repeatable pipeline. They are tested and scored, and a path that changes from run to run would make the 50-case comparison meaningless.
- **Put an agent in front.** It handles the work that varies: which clients are due today, which scenario, which product, and what history to fetch through the MCP server above.
- **Our own tools stay plain functions:** client lookup, catalog search, brand rules, and `generate`. They are not MCP servers. The only MCP connection is outward, to WeChat and perhaps a CRM.
- **Agent loop:** an agent framework (LangGraph or the Agent SDK) with a limit on steps and cost, read-only tools, and the CA's approval before anything is sent. Each tool call becomes a Langfuse span.
- **Evaluation:** run the same 50 cases through the agent and compare with the pipeline alone. Check that every tool call was needed, that no client or product was invented, and what it cost.
- **Natural-language entry.** The removed chat layer returns here as an agent turn: 「林女士说价格比别处贵，帮我回一下」 becomes a fetch of Lin's chat and a call to `generate`.

## 3. A daily work list

Pick today's clients and scenarios from triggers: a birthday within a week, days since a purchase, months since a visit, an upcoming event, an unanswered message. Show each CA their clients with three drafts to review. The trigger rules for birthdays are already in `ca/context.py`.

## 4. Feedback loop

Not possible now. The only place picks and edits were logged was the web page, and it was removed, so there is no record of what a CA chose or changed. It needs a front end again, such as a WeChat Work sidebar or a small CA app, and a period of real use to collect examples.

- Log which of the three the CA sent, and what they changed. An edit counts more than a pick.
- Use those as few-shot examples by scenario, strategy, and client. Each change to the examples is a new generator version, scored on the 50 cases before use.
- Add outcome signals: whether the client replied, booked, or bought.

## 5. Per-client memory

- A record per client: the tone that worked, topics to avoid, how often to write.
- Keep what the CA prefers apart from what the client prefers.
- Expire stale notes, and let the CA see and correct them.

## 6. Evaluation at scale

- A person scores a sample of each run in Langfuse, to check and tune the model judge.
- Track agreement between the judge and people across versions.
- Use the GLM Batch API for judge scoring and large reruns. It costs half the normal price, but results can take up to 24 hours, each file holds one model, and the account needs real-name verification. It does not suit an interactive tool.

## 7. Product hardening

- Detect the scenario from the client's message instead of asking the CA.
- Logins and one workspace per CA, deployment, audit logs.
- Privacy review of real client data, retention limits, and redaction in traces.

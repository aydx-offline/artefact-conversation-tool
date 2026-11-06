# Architecture

The tool is one fixed pipeline run from the command line, a run store that never overwrites, and a separate scoring step.

## Generating three messages

```mermaid
flowchart LR
    CLI["Command line<br/>generate, batch, evaluate,<br/>report, export"]

    subgraph DATA["Fictional data, all in Chinese"]
        CLIENTS[("clients.json<br/>30 clients, purchases, history")]
        BRAND[("brand data<br/>voice, rules, 8 strategy menus,<br/>products, events, festivals")]
        CASES[("cases<br/>50 final, 20 tuning")]
    end

    subgraph PIPE["Pipeline: ca.pipeline.generate"]
        VAL["1. Validate<br/>Chinese prose, product, event"]
        RES["2. Resolve<br/>date, season, birthday note,<br/>purchase ages, festivals"]
        PRO["3. Build prompt<br/>quoted client data, menu,<br/>voice, product facts"]
        WRI["4. Write<br/>3 candidates in one call<br/>reasoning set by env"]
        CHK["5. Code checks<br/>Chinese, length, overlap, menu,<br/>urgency, offers, products, places"]
        REV["6. Revise<br/>only failing messages, once"]
        FIN["7. Final<br/>3 candidates, status"]
    end

    GLMW["Writer model<br/>glm-5.3-flash"]
    STORE[("Run store<br/>append only, versioned<br/>cases, steps, prompts, raw replies")]

    CLI --> VAL
    CASES --> CLI
    CLIENTS --> RES
    BRAND --> RES
    BRAND --> PRO
    VAL --> RES --> PRO --> WRI
    WRI <--> GLMW
    WRI --> CHK
    CHK -- "all pass" --> FIN
    CHK -- "any fail" --> REV
    REV <--> GLMW
    REV --> CHK
    FIN --> STORE
    FIN --> CLI
```

## Scoring and reporting

```mermaid
flowchart LR
    STORE[("Run store<br/>one run, one generator version")]
    JUDGE["Judge<br/>GLM-5.3, reasoning high<br/>24 rows per case"]
    RUBRIC["Rubric<br/>2 pass or fail items,<br/>6 items scored 1 to 5"]
    SCORES[("scores.jsonl<br/>judge version recorded")]
    GOOD{{"Acceptable candidate:<br/>all code checks pass,<br/>no item below 3.<br/>Good case: all 3 acceptable"}}
    REPORT["report<br/>good cases, item means,<br/>problems"]
    CSV["cases.csv<br/>50 rows, element C"]
    CMP["before and after<br/>two runs side by side"]
    LF["Langfuse, optional<br/>traces, scores, prompt versions"]

    STORE --> JUDGE
    RUBRIC --> JUDGE
    JUDGE --> SCORES
    SCORES --> GOOD
    SCORES --> REPORT
    STORE --> CSV
    STORE --> CMP
    STORE --> LF
    SCORES --> LF
```

## Deployment

The command line ships in one Python 3.12 image. Mount `runs/` and `data/` so results stay on the host.

```mermaid
flowchart LR
    USER["docker run ... python -m ca batch"] --> IMAGE
    subgraph IMAGE["Docker image: ca-messages"]
        TOOL["python -m ca<br/>generate, batch, evaluate, report, export"]
    end
    IMAGE -- "mounted" --> VOL[("runs/ and data/")]
    IMAGE -- "HTTPS" --> PARATERA["Paratera GLM endpoint"]
    IMAGE -- "optional" --> LANGFUSE["Langfuse Cloud"]
```

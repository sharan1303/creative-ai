# Strategic Plan to Ace Adobe’s FDE Take-Home Assignment

**Key takeaway:** Center your solution on a lightweight, cloud-agnostic **Python/FastAPI micro-service** that orchestrates Adobe Firefly and OpenAI DALL·E 3 for image generation. Complement it with an **LLM-powered agent** that watches briefs, tracks variant counts, and emails stakeholders. By structuring deliverables into three crisp modules—​architecture, pipeline, and agent—you can finish within 6–8 hours while demonstrating enterprise-grade thinking.[^1][^2]

## 1. Decoding the Assignment

Adobe asks you to:

* Draft a **high-level architecture diagram** and one-slide roadmap.[^1]
* Ship a **working creative-automation pipeline** that ingests a JSON brief, reuses or generates assets, exports three aspect ratios, and saves outputs clearly.[^1]
* Propose an **agentic oversight design** and write a stakeholder email explaining hypothetical delays.[^1]

Success hinges on four evaluation lenses: clarity of design, code quality, GenAI integration, and stakeholder empathy.

## 2. Overall Success Strategy \& Interview Framing

* **Show customer obsession:** Tie every design choice to the client’s pain points—campaign velocity, brand safety, and ROI.[^1]
* **Prove pragmatic engineering:** Use off-the-shelf managed services (Blob/S3, Firefly, DALL·E) to stay in the 6–8 hour envelope.[^3][^4][^5]
* **Narrate trade-offs:** Explain why FastAPI (speed, type hints, Swagger) outranks Flask for micro-services.[^2][^6]
* **Rehearse the story arc:** 5-minute intro, 15-minute live demo, 5-minute deep dive on edge cases, 5-minute Q\&A.


## 3. Task 1 – Architecture \& Roadmap

### 3.1 Architectural Principles

* **Stateless micro-services:** Containerised FastAPI workers scale horizontally.[^2][^7]
* **Event-driven queue:** A managed queue (Azure Service Bus, SQS) decouples uploads from generation to avoid API latency spikes.[^6]
* **Cloud-agnostic storage:** Use environment variables to swap between Azure Blob or AWS S3 without code changes.
* **Observability first:** OpenTelemetry traces and structured logs feed a lightweight dashboard.


### 3.2 Recommended Tech Stack

| Concern | Technology | Rationale |
| :-- | :-- | :-- |
| API \& Orchestration | FastAPI + Pydantic | Async, type-safe, auto-docs |
| GenAI | Adobe Firefly API / OpenAI DALL·E 3 | Brand-safe plus backup model |
| Storage | Azure Blob (dev) / S3 (alt) | Cheap, versioned, SDK parity |
| Queue | Azure Service Bus / AWS SQS | At-least-once delivery, serverless |
| Post-processing | Pillow / ffmpeg | Resize, overlay text |
| Compliance | simple-cv logo check, color-thief palette check | Fast heuristic bonus points |
| CI/CD | GitHub Actions → Docker Hub | Reproducible demo |

### 3.3 End-to-End Pipeline Diagram

![High-level creative automation pipeline for social ad campaigns.](https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/9fcd1494f330da51f4a6333d3eae7216/0f77b49b-ed62-4d77-8cbf-3fcf84272324/1f1eeef8.png)

High-level creative automation pipeline for social ad campaigns.

### 3.4 Roadmap (one slide)

* **Hour 0–1 ½:** Draft diagram \& roadmap, scaffold repo.
* **Hour 1 ½–4:** Build ingestion endpoints, queue handler, Firefly + DALL·E wrappers, image post-processing.
* **Hour 4–5:** Implement variant tracker DB (SQLite), simple compliance checks, logging.
* **Hour 5–6:** Write README, add pytest + lint, record 3-min demo GIF.
* **Buffer:** Extra time for polish, slide deck, email template.


## 4. Task 2 – Creative Automation Pipeline Proof-of-Concept

### 4.1 Functional Workflow

1. **Brief upload:** `/briefs` endpoint accepts JSON with product list, market, audience, and message.[^1]
2. **Job enqueue:** Brief metadata and asset URIs pushed to queue.
3. **Worker execution:**
    * Checks storage for existing images.
    * If missing, calls Firefly first (higher brand compliance), falls back to DALL·E 3 on failure.[^3][^4]
    * Generates 1:1, 9:16, and 16:9 variants in parallel using async tasks.[^5]
4. **Brand overlay:** Adds message text with preset brand font and palette (configurable YAML).
```
5. **Output persistence:** Saves under `outputs/<product>/<ratio>/image.png` with JSON sidecar (prompt, seed, size).  
```


### 4.2 Core Components \& Languages

* `models.py` – Pydantic schemas for briefs and job results.
* `worker.py` – Async generator orchestrator with retry/back-off.
* `firefly_client.py` and `dalle_client.py` – Thin API wrappers, injectable via dependency-injection.
* `cli.py` – Invoke pipeline locally: `python cli.py --brief example.json`.
* `tests/` – Pytest unit tests for each client and resize util.


### 4.3 Key Implementation Steps

* **Token management:** Use OAuth2 client-credentials for Firefly; simple API key for OpenAI.[^3][^8]
* **Rate-limit resilience:** Exponential back-off; queue visibility timeout handles reprocessing.
* **Localisation stub:** Add optional `--lang fr` flag and translate message via Azure Translator for bonus.
* **Compliance check bonus:** OpenCV template-match logo, ColorThief palette delta <10%.


### 4.4 Testing, Demo \& Documentation

* **pytest-cov** to reach 85% coverage.
* **Makefile** targets: `make run`, `make test`, `make lint`.
* **Demo script:** Record `asciinema` or OBS video walking through input, generation, and folder structure.
* **README:** Problem, architecture, quick-start, design choices, limitations (e.g., no 3-D renders).


## 5. Task 3 – Agentic System \& Stakeholder Communication

### 5.1 Agent Design Goals

* **Continuous polling** of `briefs` table every minute (Serverless cron).
* **LLM contextual window** includes brief metadata, variant count, SLA timer.
* **Decision tree:** If `<3` variants after *n* minutes or API quota error, trigger alert.


### 5.2 Agent Architecture

![Agentic oversight and alerting flow.](https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/9fcd1494f330da51f4a6333d3eae7216/0ab9e685-c171-4a4c-b31b-b695f610d37b/87d08a21.png)

Agentic oversight and alerting flow.

### 5.3 LLM Prompt Design

> *System prompt:* “You are a creative-ops assistant. Summarise delays, reference brief title, ETA, and actionable next steps.”
> *User context:* JSON dump of brief, variant counts, error logs (trimmed to 4 k tokens).

### 5.4 Sample Delay Email (deliverable)

> **Subject:** 🚨 Action Required – Asset Generation Delay for *Summer Splash EU*
>
> Hi Maria,
> Our GenAI pipeline hit a rate-limit provisioning delay on Adobe Firefly’s EU endpoint at **14:35 UTC**. We generated only **2/3 required variants** for *Product A*, aspect ratio **9:16**.
>
> **Next steps**
> -  Automatically retry after quota reset at 15:05 UTC.
> -  Fallback to OpenAI DALL·E 3 if Firefly remains unavailable.
> -  Updated ETA for final creatives: **15:30 UTC**.
>
> No action needed on your side; we will send assets for review immediately after generation.
>
> Best,
> *Automation Agent*

## 6. Presentation \& Recording Tips

* **Lead with the diagram**—stakeholders grasp flow in 30 seconds.
* **Live demo path:** Upload brief → show queue log → show generated images folder.
* **Talk through trade-offs:** Why Firefly primary? (brand safety), why DALL·E fallback? (coverage).
* **Stay within 25 minutes** to leave Q\&A buffer.


## 7. Conclusion

Delivering a clear micro-service pipeline around FastAPI and Adobe Firefly, wrapped with an LLM agent for operational governance, directly aligns with Adobe’s objectives of speed, brand consistency, and insight-driven optimisation. By following the architecture and timeline above, you not only meet every stated requirement but also demonstrate forward-deployed engineering maturity—exactly what interviewers are looking for.[^1][^3][^6]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^9]</span>

<div align="center">⁂</div>

[^1]: FDE-Take-Home.pdf

[^2]: https://www.geeksforgeeks.org/python/microservice-in-python-using-fastapi/

[^3]: https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/firefly-generate-image-api-tutorial/

[^4]: https://help.openai.com/en/articles/8555480-dalle-3-api

[^5]: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/dall-e

[^6]: https://webandcrafts.com/blog/fastapi-scalable-microservices

[^7]: https://developer.nvidia.com/blog/building-a-machine-learning-microservice-with-fastapi/

[^8]: https://platform.openai.com/docs/guides/image-generation

[^9]: https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/cm-generate-image/

[^10]: https://www.reddit.com/r/dalle2/comments/1c1o9rz/i_built_a_dalle_3_web_ui_that_uses_your_own_api/

[^11]: https://developer.adobe.com/firefly-services/docs/firefly-api/guides/concepts/structure-image-reference/

[^12]: https://developer.adobe.com/firefly-services/docs/firefly-api/guides/api/generate-similar/V3_Async/

[^13]: https://prama.ai/building-microservices-with-fastapi-a-comprehensive-guide/

[^14]: https://developer.adobe.com/firefly-services/docs/firefly-api/guides/api/image_generation/V3/

[^15]: https://platform.openai.com/docs/models/dall-e-3

[^16]: https://dev.to/paurakhsharma/microservice-in-python-using-fastapi-24cc

[^17]: https://developer.adobe.com/firefly-services/docs/firefly-api/guides/api/image_generation/V3_Async/

[^18]: https://help.openai.com/en/articles/6402865-is-dalle-3-available-through-an-api

[^19]: https://blog.devops.dev/building-enterprise-python-microservices-with-fastapi-in-2025-3-10-project-setup-1113658c9f0e

[^20]: https://www.adobe.com/uk/products/firefly.html

[^21]: https://help.openai.com/en/articles/6402865-is-dall-e-3-available-through-an-api


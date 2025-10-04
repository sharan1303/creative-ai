# Implementation Checklist

## Adobe FDE Take-Home - Quick Reference

---

## Pre-Implementation Setup

### Environment

- [ ] Create GitHub repository (public)
- [ ] Python 3.11+ installed
- [ ] Create virtual environment
- [ ] Get OpenAI API key (DALL-E 3 access)
- [ ] (Optional) Get Adobe Firefly API credentials
- [ ] Install OBS Studio or screen recording tool
- [ ] Set up presentation tool (Google Slides/PowerPoint)

### Time Allocation

- [ ] Block 6-8 hours in calendar
- [ ] Identify submission deadline: **_______________**
- [ ] Plan demo recording time: **_______________**

---

## Task 1: Architecture & Roadmap (1.5 hours)

### Architecture Diagram

- [ ] Create account on Excalidraw/Lucidchart
- [ ] Draw components:
  - [ ] Ingestion layer (FastAPI)
  - [ ] Storage layer (local/cloud)
  - [ ] GenAI layer (Firefly/DALL-E)
  - [ ] Processing layer (resize, overlay)
  - [ ] Output layer (organized folders)
  - [ ] Monitoring agent
- [ ] Add data flow arrows
- [ ] Label technologies used
- [ ] Export as PNG/PDF
- [ ] Save to `docs/architecture-diagram.png`

### Roadmap Slide

- [ ] Create timeline chart (12 weeks)
- [ ] Add phases:
  - [ ] Foundation (Weeks 1-2)
  - [ ] MVP (Weeks 3-4)
  - [ ] Scale (Weeks 5-6)
  - [ ] Intelligence (Weeks 7-8)
  - [ ] Production (Weeks 9-10)
  - [ ] Launch (Weeks 11-12)
- [ ] Add milestones markers
- [ ] Identify stakeholder touchpoints
- [ ] Export as slide or image
- [ ] Save to `docs/roadmap.png`

---

## Task 2: Pipeline Implementation (4-5 hours)

### Hour 0: Project Setup (30 min)

- [ ] Initialize git repo
- [ ] Create folder structure:

  ```text
  creative-automation-pipeline/
  ├── src/
  │   ├── models/
  │   ├── services/
  │   ├── utils/
  │   └── agent/
  ├── tests/
  ├── examples/
  ├── docs/
  └── outputs/
  ```

- [ ] Create `requirements.txt`:

  ```text
  fastapi==0.104.1
  pydantic==2.5.0
  pydantic-settings==2.1.0
  httpx==0.25.2
  pillow==10.1.0
  openai==1.6.0
  pytest==7.4.3
  pytest-asyncio==0.21.1
  python-dotenv==1.0.0
  ```

- [ ] Create `.env.example`:

  ```shell
  OPENAI_API_KEY=your_key_here
  ADOBE_FIREFLY_CLIENT_ID=optional
  ADOBE_FIREFLY_CLIENT_SECRET=optional
  LOG_LEVEL=INFO
  ```

- [ ] Create `.gitignore`:

  ```shell
  .env
  __pycache__/
  *.pyc
  venv/
  outputs/
  *.log
  .pytest_cache/
  ```

- [ ] Initial commit

### Hour 1: Data Models (30 min)

- [ ] Create `src/models/__init__.py`
- [ ] Create `src/models/brief.py`:
  - [ ] `Product` model (id, name, description)
  - [ ] `CampaignBrief` model (campaign_id, products, target_market, etc.)
  - [ ] `AspectRatio` model (name, width, height)
  - [ ] `ASPECT_RATIOS` constant (1:1, 9:16, 16:9)
- [ ] Test models with pytest

### Hour 1.5: Configuration & Utils (30 min)

- [ ] Create `src/utils/config.py`:
  - [ ] `Settings` class with Pydantic BaseSettings
  - [ ] Environment variable loading
- [ ] Create `src/utils/logger.py`:
  - [ ] Structured logging setup
- [ ] Create `src/utils/retry.py`:
  - [ ] `@async_retry` decorator

### Hour 2: GenAI Clients (1 hour)

- [ ] Create `src/services/dalle_client.py`:
  - [ ] `DalleClient` class
  - [ ] `async def generate()` method
  - [ ] Error handling for 429 rate limits
  - [ ] Test with mock response
- [ ] (Optional) Create `src/services/firefly_client.py`:
  - [ ] OAuth2 token management
  - [ ] Image generation endpoint
- [ ] Create `src/services/genai.py`:
  - [ ] `GenAIOrchestrator` class
  - [ ] Firefly → DALL-E fallback logic
  - [ ] Size mapping helper

### Hour 3: Image Processing (45 min)

- [ ] Create `src/services/processor.py`:
  - [ ] `ImageProcessor` class
  - [ ] `resize()` method
  - [ ] `add_text_overlay()` method
  - [ ] Test with sample image

### Hour 3.5: Storage Management (30 min)

- [ ] Create `src/services/storage.py`:
  - [ ] `StorageManager` class
  - [ ] `get_asset()` - check if exists
  - [ ] `save_output()` - save to `outputs/<product>/<ratio>/`
  - [ ] `save_metadata()` - JSON sidecar
  - [ ] Test file I/O

### Hour 4: CLI Pipeline (1 hour)

- [ ] Create `src/cli.py`:
  - [ ] Argument parser (--brief path)
  - [ ] `process_campaign()` async function
  - [ ] `generate_variant()` async function
  - [ ] Parallel generation with asyncio.gather()
  - [ ] Progress logging
- [ ] Create example brief `examples/brief_single_product.json`
- [ ] **Milestone Test:** Run pipeline end-to-end

  ```bash
  python -m src.cli --brief examples/brief_single_product.json
  ```

- [ ] Verify outputs folder structure

### Hour 5: Testing (45 min)

- [ ] Create `tests/test_models.py`
- [ ] Create `tests/test_processor.py`
- [ ] Create `tests/test_storage.py`
- [ ] Create `tests/test_integration.py` (with mocks)
- [ ] Run pytest:

  ```bash
  pytest tests/ -v --cov=src --cov-report=term-missing
  ```

- [ ] Target: 80%+ coverage

### Hour 5.5: Bonus Features (30 min) [OPTIONAL]

- [ ] Create `src/services/compliance.py`:
  - [ ] Basic logo presence check (OpenCV)
  - [ ] Color palette extraction (ColorThief)
  - [ ] Prohibited words filter
- [ ] Add compliance checks to pipeline
- [ ] Log compliance results

### Hour 6: Documentation (1 hour)

- [ ] Create comprehensive `README.md`:
  - [ ] Problem statement
  - [ ] Features overview
  - [ ] Architecture diagram embed
  - [ ] Setup instructions (step-by-step)
  - [ ] Usage examples
  - [ ] Example output (screenshots)
  - [ ] Design decisions section
  - [ ] Assumptions & limitations
  - [ ] Future enhancements
- [ ] Add inline code comments
- [ ] Create `CONTRIBUTING.md` (optional polish)
- [ ] Final git commit

---

## Task 3: Agentic System (1 hour)

### Agent Design (30 min)

- [ ] Create agent architecture diagram:
  - [ ] Monitoring loop
  - [ ] Decision engine
  - [ ] LLM context builder
  - [ ] Alerting service
- [ ] Export diagram to `docs/agent-architecture.png`

### Database Schema (15 min)

- [ ] Document SQLite schema:
  - [ ] `campaigns` table
  - [ ] `variants` table
  - [ ] `errors` table
- [ ] Add to `docs/database-schema.md`

### LLM Context Design (15 min)

- [ ] Document system prompt for alert generation
- [ ] Define context JSON structure
- [ ] Show example LLM input/output
- [ ] Add to `docs/llm-context-design.md`

### Stakeholder Email (15 min)

- [ ] Write sample delay email:
  - [ ] Professional subject line
  - [ ] Clear issue summary
  - [ ] Technical details (collapsible)
  - [ ] Next steps with timeline
  - [ ] No action required statement
  - [ ] Alternative options
- [ ] Save to `docs/stakeholder-email-sample.md`

### (Optional) Working Prototype

- [ ] Implement basic `src/agent/monitor.py`
- [ ] Add polling loop
- [ ] Integrate with OpenAI for alert generation
- [ ] Test with mock campaign data

---

## Presentation Preparation (1 hour)

### Slide Deck (45 min)

- [ ] Title slide
- [ ] Problem statement (pain points)
- [ ] Solution overview
- [ ] Architecture diagram slide
- [ ] Roadmap slide
- [ ] Demo transition slide
- [ ] Code highlights slide
- [ ] Agent system slide
- [ ] Stakeholder communication slide
- [ ] Testing & quality slide
- [ ] Lessons learned
- [ ] Q&A slide
- [ ] Save as PDF: `docs/presentation.pdf`

### Demo Video (3-5 min) (30 min)

- [ ] Script demo flow:
  1. Show project structure
  2. Show example brief JSON
  3. Run CLI command
  4. Show console output
  5. Navigate to outputs folder
  6. Show generated images (3 ratios)
  7. Show metadata JSON
  8. (Optional) Show test run
- [ ] Record with OBS/ShareX
- [ ] Edit if needed
- [ ] Export as MP4
- [ ] Upload to YouTube (unlisted) or include in repo
- [ ] Add link to README

### Rehearsal (15 min)

- [ ] Practice 25-minute presentation
- [ ] Test demo flow locally
- [ ] Prepare answers to likely questions:
  - [ ] Why FastAPI over Flask?
  - [ ] How would you scale this?
  - [ ] What about security?
  - [ ] Cost optimization strategies?
  - [ ] How to handle GDPR compliance?

---

## Final Submission Checklist

### GitHub Repository

- [ ] All code pushed to main branch
- [ ] Repository is public
- [ ] Clean commit history
- [ ] No API keys in commits
- [ ] README renders correctly on GitHub
- [ ] Images/diagrams display properly
- [ ] Example outputs in README or screenshots

### Documentation

- [ ] `README.md` - comprehensive
- [ ] `requirements.txt` - pinned versions
- [ ] `.env.example` - all variables documented
- [ ] `docs/architecture-diagram.png`
- [ ] `docs/roadmap.png`
- [ ] `docs/agent-architecture.png`
- [ ] `docs/stakeholder-email-sample.md`
- [ ] Code comments for complex logic

### Code Quality

- [ ] All tests passing
- [ ] 80%+ code coverage
- [ ] No linter errors (ruff/flake8)
- [ ] Type hints for all functions
- [ ] Consistent code style

### Presentation

- [ ] Slide deck exported to PDF
- [ ] Demo video recorded (3-5 min)
- [ ] Video accessible (YouTube link or file)
- [ ] Tested on clean machine (or Docker)

### Email to Talent Partner

- [ ] Subject: "FDE Take-Home Submission - [Your Name]"
- [ ] Body includes:
  - [ ] GitHub repository link
  - [ ] Demo video link
  - [ ] Presentation PDF attachment
  - [ ] Brief summary of approach
  - [ ] Availability for interview
- [ ] Send **day before** scheduled interview

---

## Day-Before-Interview Checklist

- [ ] Test demo on clean environment
- [ ] Verify all links work
- [ ] Print presentation as backup
- [ ] Prepare 3-5 questions to ask interviewers
- [ ] Get good sleep! 😊

---

## Troubleshooting Common Issues

### Issue: DALL-E 3 rate limit exceeded

**Solution:**

- Wait 60 seconds between requests
- Use `asyncio.sleep(2)` between generations
- Implement retry with exponential backoff

### Issue: PIL font rendering fails

**Solution:**

- Fall back to default font
- Use absolute path to font file
- Include font file in repo

### Issue: Tests failing with async

**Solution:**

- Use `@pytest.mark.asyncio` decorator
- Install `pytest-asyncio`
- Use `async def` for test functions

### Issue: OpenAI API key not found

**Solution:**

- Check `.env` file exists
- Verify `python-dotenv` is installed
- Use `load_dotenv()` in config.py

### Issue: Output images not displaying text

**Solution:**

- Increase font size
- Check text color contrast
- Verify text position calculation

---

## Success Metrics

✅ **Minimum Viable Demo:**

- Pipeline generates 3 aspect ratios for 2+ products
- Images saved to organized folder structure
- Campaign message overlaid on images
- Can run with single command
- README explains setup clearly

🏆 **Stretch Goals:**

- Asset reuse working (check before generate)
- Brand compliance checks implemented
- Working agent prototype
- Beautiful presentation design
- Polished demo video
- >85% test coverage

---

**Remember:** Perfect is the enemy of done. Focus on working end-to-end first, then polish!

**Questions during implementation?** Document them and address in "Assumptions & Limitations" section.

---

## Checklist Update (uv + gpt-image-1)

- [ ] Use uv for environment management:

  ```bash
  uv venv .venv && . ./.venv/Scripts/Activate.ps1  # Windows
  # source .venv/bin/activate                      # macOS/Linux
  uv pip install -r requirements.txt
  ```

- [ ] Configure `.env` with `OPENAI_API_KEY` (for gpt-image-1)
- [ ] GenAI layer: Primary OpenAI gpt-image-1; Optional Google Imagen; Free fallback via HF SDXL/Local SDXL
- [ ] Update any “DALL-E 3” references to “gpt-image-1” in docs and tests
- [ ] Troubleshooting: treat “gpt-image-1 rate limit” similarly to prior DALL-E guidance (retry/backoff)

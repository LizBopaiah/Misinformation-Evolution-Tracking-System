# Misinformation Detection and Evolution Tracking System (MET) - Project Progress

A complete multi-module enterprise platform dedicated to auditing article claim veracity, indexing sentiment drifts, identifying story lineages, clustering thematic narratives, and displaying relationships via knowledge graphs.

---

## 📌 Project Overview

| Attribute | Details |
| :--- | :--- |
| **Project Name** | Misinformation Detection and Evolution Tracking System (MET) |
| **Tech Stack** | Python (Flask), SQLAlchemy, SQLite, JWT (Auth), Tailwind CSS, JS (Frontend) |
| **System State** | Foundation Architecture & Base Layout Ready |

---

## 🚀 Module 1 – Foundation & Architecture (Status: COMPLETED ✅)

### Implemented Features
1. **Base Framework Setup**: Integrated environment config loading via `python-dotenv`, Flask app factory pattern in `app/__init__.py`, and global extension loaders.
2. **Centralized Logging & Global Error Handlers**: Configured standard logs written to `logs/application.log` and registered custom API error handlers for 400, 401, 403, 404, and 500 status codes.
3. **Database Schemas & Relationships**: Initialized SQLite models with relationships, backrefs, indexes, and timezone-aware hooks.
4. **Authentication Scaffolding**: Built User registration, password hashing (`werkzeug.security`), and JWT issuance routing.
5. **Standardized API Response Wrappers**: Constructed helper routines for JSON success, error, and validation payloads.
6. **Frontend UI Layout (Apple + Notion Inspired)**: Designed responsive theme framework containing layout bars, toasts engine, theme toggler, modal dialogs, and loaders.
7. **Bruno Collection suite**: Outlined API tests mapping health check, signup, sign-in, profile viewing, and profile updates.

### 🔄 Foundation Refinement Update
1. **Homepage Redesign**: Overhauled landing layout into an elegant, Perplexity-style search interface optimized for researchers, journalists, and students, featuring a central search box, placeholder searches history, and analysis summary layout reserves.
2. **Admin concept Removal**: Excised admin roles, privilege decorators, and related route checks from User schemas, JWT tokens, registration forms, and user endpoint blueprints.
3. **User-Centric Workflow Preparation**: Prepared frontend logic and service models to support the core research flow: Search Topic -> Collect Articles -> Generate Summary -> Audits Verdicts -> Generate Sentiment or Evolution Analysis.
4. **System Overview Page**: Re-routed dev panels, database models checklists, dataset inspections, and logs previewers onto a dedicated `/system-overview` view, ensuring they do not dominate the landing layout.

### 🔐 Authentication Flow Refinement
1. **Public Landing Page**: Created a visitor-facing home route (`/`) introducing project capabilities, core features, and a timeline of the research pipeline.
2. **Login & Registration Pages**: Created dedicated standalone pages (`/login` and `/register`) for authentication.
3. **Protected Dashboard Architecture**: Moved the search queries console, results analysis triggers, and recent lookups list to `/dashboard`.
4. **Auto-Login Flow Design**: Auto-logs in users directly upon successful registration (assigning standard JWTs) and redirects them straight to the research console.
5. **Route Protection Structure**: Enabled routing guards on `/dashboard`, `/profile`, `/search-history`, and `/system-overview` to redirect unauthenticated users to `/login`.


### 🧬 Future Planned Workflow
The development of future modules will be guided by this end-user research pipeline:
```
User Search Topic/Claim
       ↓
Article Collection (Search/Scraping Services)
       ↓
Content Extraction (BeautifulSoup Parsing)
       ↓
Summary Generation (Gemini LLM Summary)
       ↓
Fact Check Verification (Veracity Rating)
       ↓
Sentiment & Emotional Manipulation Analysis (Emotions Indexing)
       ↓
Narrative Similarity Detection (TF-IDF/Cosine Cosine Overlap)
       ↓
Narrative Clustering (Thematic Groups)
       ↓
Evolution Tracking (Lineage Mutation Trees)
       ↓
Knowledge Graph Generation (Semantic Triples)
       ↓
Report Export (PDF Generating)
```


---

## 🗂️ Implemented Project Files

```
MET/
├── app/
│   ├── __init__.py              # App factory pattern, logging setup, error handlers
│   ├── config.py                # Environment configuration loading
│   ├── extensions.py            # Extensions registry: SQLAlchemy, Migrate, JWT
│   ├── models/                  # Database models schemas
│   │   ├── __init__.py          # Bundled import statement exposures
│   │   ├── user.py              # User model (password hashing, serializations)
│   │   ├── search.py            # SearchHistory (query tracking, status, type)
│   │   ├── article.py           # Article (title, content, publication, relationships)
│   │   ├── fact_check.py        # FactCheckResult (ratings, confidence)
│   │   ├── sentiment.py         # SentimentResult (compound scores, JSON emotions)
│   │   ├── evolution.py         # EvolutionResult (mutation trees, narrative lineage)
│   │   ├── cluster.py           # NarrativeCluster (thematic clustering groups)
│   │   └── log.py               # SystemLog (internal security/admin log records)
│   ├── services/                # Business logic blocks & services
│   │   ├── __init__.py          # Bundle services
│   │   ├── search_service.py    # Google Custom Search API with caching and duplicate removal
│   │   ├── scraping_service.py  # Multi-method web scraping & TF-IDF similarity deduplication
│   │   ├── summarization_service.py # Gemini-powered narrative summarization with localized fallback
│   │   ├── fact_checking_service.py # Hybrid veracity classification mapping
│   │   ├── sentiment_service.py # Sentiment model classification placeholder
│   │   ├── evolution_service.py # Mutator story tracking placeholder
│   │   ├── similarity_service.py # Vector text similarity placeholder
│   │   ├── clustering_service.py # Narratives clustering placeholder
│   │   ├── visualization_service.py # Chart metadata generation placeholder
│   │   ├── knowledge_graph_service.py # Semantic triples construction placeholder
│   │   ├── report_service.py    # PDF export pipeline placeholder
│   │   ├── dataset_service.py   # Dataset manager layer (Fake News, LIAR, Emotion)
│   │   ├── model_service.py     # Model manager layer (saving, loading, inference methods)
│   │   ├── nlp_service.py       # spaCy + NLTK text preprocessing pipeline
│   │   └── utils.py             # Shared utility functions
│   ├── blueprints/              # Routing layers
│   │   ├── __init__.py          # Blueprint package module
│   │   ├── auth.py              # JWT authentication: signup & login
│   │   ├── user.py              # User profile retrieval & update
│   │   ├── api.py               # Standardized API response utilities
│   │   ├── dataset.py           # Dataset status, stats, and preview endpoints
│   │   ├── model.py             # Classifier status and performance endpoints
│   │   ├── nlp.py               # NLP token preprocessing sandbox API
│   │   ├── search.py            # Search execution, history retrieval, article detail endpoints
│   │   └── main.py              # Page rendering, system health validation
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css        # Apple + Notion variables, typography and scrollbar styles
│   │   └── js/
│   │       └── app.js           # Client actions: theme toggling, toasts, modals, loader
│   └── templates/
│       ├── base.html            # Premium dashboard master frame structure
│       ├── index.html           # Landing page content workspace
│       └── system_overview.html # Analytics dashboard displaying charts & tables
├── bruno/                       # Bruno Collection suite
│   └── MET-Collection/
│       ├── bruno.json           # Bruno configuration
│       ├── environments/
│       │   └── Local.bru        # Base URL and Bearer Token variables
│       ├── Health Check.bru
│       ├── User Registration.bru
│       ├── User Login.bru
│       ├── Get Profile.bru
│       ├── Update Profile.bru
│       ├── Dataset Status.bru
│       ├── Dataset Statistics.bru
│       ├── Dataset Preview.bru
│       ├── Model Status.bru
│       ├── Model Performance.bru
│       ├── NLP Preprocess.bru
│       ├── Search.bru
│       ├── Article Retrieval.bru
│       ├── Search History.bru
│       ├── Summary Generation.bru
│       └── Fact Check Result.bru
├── scripts/
│   ├── train_models.py          # Model training pipeline (Logistic Regression vs Naive Bayes)
│   └── verify_module4.py        # Automated test verification for search and scraping
├── reports/
│   ├── fake_news_confusion_matrix.png # Confusion matrix plot for Fake News classifier
│   ├── liar_confusion_matrix.png      # Confusion matrix plot for LIAR classifier
│   └── emotion_confusion_matrix.png   # Confusion matrix plot for Emotion classifier
├── .env.example                 # Env parameters template
├── .env                         # Preconfigured development env variables
├── .gitignore                   # Exclusions: Virtualenv, build, logs, databases, IDE files
├── app.py                       # App running entrypoint (python app.py)
├── requirements.txt             # Production-grade requirements list
├── MODULE_3_VERIFICATION_REPORT.md # Verification metrics for NLP datasets and pipelines
├── MODULE_4_VERIFICATION_REPORT.md # Verification metrics for Custom Search and Scraping
└── PROJECT_PROGRESS.md          # Project roadmap tracking document (this file)
```

---

## 📊 Database, API, and Dataset Statuses

### 1. Database Status (SQLite)
* **Status**: INITIALIZED, MIGRATED & TESTED
* **Schema**: Created User, SearchHistory (updated), Article (updated), FactCheckResult, SentimentResult, EvolutionResult, NarrativeCluster, and SystemLog schemas with foreign key references, timestamps, indices, and delete cascade behaviors.
* **Auto-Init**: Dynamically initializes and manages database context via Alembic migrations.

### 2. API Endpoint Status
* **API Version**: `v1`
* **Response Wrapper**: Enforces `{"success": true, "message": "...", "data": {...}}` response payload consistency globally.
* **Endpoints**:
  * `GET /api/health` 🟢 (Online)
  * `POST /api/auth/register` 🟢 (Online)
  * `POST /api/auth/login` 🟢 (Online)
  * `GET /api/users/profile` 🔑 (Requires Bearer token, Online)
  * `PUT /api/users/profile` 🔑 (Requires Bearer token, Online)
  * `GET /api/datasets/status` 🟢 (Online)
  * `GET /api/datasets/statistics` 🟢 (Online)
  * `GET /api/datasets/preview` 🟢 (Online)
  * `GET /api/models/status` 🟢 (Online)
  * `GET /api/models/performance` 🟢 (Online)
  * `POST /api/nlp/preprocess` 🟢 (Online)
  * `POST /api/search` 🔑 (Requires Bearer token, Online)
  * `GET /api/search/<id>` 🔑 (Requires Bearer token, Online)
  * `GET /api/articles/<id>` 🔑 (Requires Bearer token, Online)
  * `GET /api/search-history` 🔑 (Requires Bearer token, Online)
  * `POST /api/sentiment/analyze` 🔑 (Requires Bearer token, Online)
  * `GET /api/sentiment/<search_id>` 🔑 (Requires Bearer token, Online)
  * `POST /api/evolution/analyze` 🔑 (Requires Bearer token, Online)
  * `GET /api/evolution/<search_id>` 🔑 (Requires Bearer token, Online)

### 3. Dataset Status
* **Directories Connected**:
  * `MET/Fake News Detection` (Exists in root directory)
  * `MET/LIAR Dataset` (Exists in root directory)
  * `MET/Emotion Dataset` (Exists in root directory)
* **Integration Layer**: `DatasetService` class in `app/services/dataset_service.py` loaded and validated, with summaries cached in `instance/dataset_stats.json`.

---

## ⚠️ Known Issues / Limitations
* External APIs (Gemini, Google Custom Search) and model processes are currently represented by placeholder routines or cached fallbacks when credentials are unconfigured.

---

## 🚀 Module 2 – Authentication & User Management (Status: COMPLETED ✅)

### Implemented Features
1. **Profile Management API**: Integrated profile retrieve and update routes. Created the `GET /api/users/search-history` endpoint and fully established User ↔ SearchHistory foreign keys, backrefs, and cascade delete behavior.
2. **Disabled Email Editing**: Enforced disabled email editing constraints on the backend validation layer and frontend UI views.
3. **Secure Image Uploads Service**: Implemented secure profile picture upload (`POST /api/users/profile-picture`) with size checks (max 5MB), file extension constraints (JPG, JPEG, PNG, WEBP), MIME type validation, and Pillow-based integrity checks.
4. **Profile Picture Deletion**: Added picture deletion endpoint (`DELETE /api/users/profile-picture`) that deletes files from disk and updates DB.
5. **Automatic JWT Session Expiration Handling**: Configured a global fetch interceptor that auto-injects JWT tokens and logs the user out with dynamic visual warnings if a 401 response occurs.
6. **Initials-Based Avatar Generation**: Added dynamic frontend avatar initials generation as a graceful fallback when no profile picture exists.
7. **Refined UI & Dashboard**: Updated dashboard greetings ("Welcome back, {User Name}"), showing the member's created date, avatar, and a clean "No activity available yet" state for Recent Activity.
8. **Bruno Suite Verification**: Expanded the Bruno API test collection with post-response scripts to dynamically extract and store access tokens for registration, logins, profile updates, picture uploads, deletions, and route checks.

---

## 🚀 Module 3 – Dataset Integration & NLP Foundation (Status: COMPLETED ✅)

### Implemented Features
1. **spaCy + NLTK NLP Preprocessing**: Created a highly optimized lemmatizer and cleaner in `nlp_service.py` that strips HTML/URLs, cleans punctuation, filters stopwords, lemmatizes tokens, and runs efficiently in batches using `.pipe()`.
2. **Dataset Loaders & Cache System**: Implemented `DatasetService` supporting Fake News (merged csvs), LIAR (three TSVs mapped to 3-class ratings), and Emotion (three semicolon txt files maintaining the capitalized "Love" class). Computes distribution summaries and caches them in `instance/dataset_stats.json` for instant startup. Added preview endpoint returning 5-record samples.
3. **Reproducible Baseline Training Pipeline**: Designed `scripts/train_models.py` which trains Logistic Regression and Multinomial Naive Bayes models on all three tasks using stratified splits (`test_size=0.2`, `random_state=42`). Accuracies achieved: Fake News (98.9%), LIAR (55.3%), Emotion (79.6%).
4. **Serialization and Artifact persistence**: Saves best models, TF-IDF vectorizers, and CountVectorizers separately using `joblib`. Stores confusion matrix heatmaps (PNG format) in `reports/` and performance summaries in `models/performance_metrics.json`.
5. **Interactive NLP Sandbox & Analytics Dashboard**: Built `/system-overview` dev screen presenting dataset connection stats, registered model statuses, Chart.js pie and bar distribution graphics, baseline classifier comparison cards, and a text cleaning simulator.
6. **API Verification Collection**: Added request scripts in the Bruno suite covering dataset status, label distributions, previews, model active files verification, performance summaries, and clean-text POSTs.

---

## 🚀 Module 4 – Search, Article Collection & Narrative Summarization (Status: COMPLETED ✅)

### Implemented Features
1. **Web Search Service**: Google Custom Search API integration in `SearchService` with automatic result ranking, URL duplicate removal, 24-hour result caching, and realistic mock fallback.
2. **Multi-Source Scraping Fallback Chain**: Robust article scraper in `ScrapingService` utilizing `newspaper3k` -> `trafilatura` -> `BeautifulSoup` fallback pipeline. Extracts title, body, source, publication date, and computes SHA-256 content hashes.
3. **TF-IDF Article Deduplication**: Computes content similarity matrices using scikit-learn's TF-IDF vectorizer and filters out articles with content similarity exceeding 95%.
4. **Narrative Summarization Service**: Gemini API text generator in `SummarizationService` creating query context-rich summaries, with a localized extractive sentence word-frequency summarizer fallback for offline operation.
5. **Hybrid Fact-Check Verifier**: Verification pipeline in `FactCheckingService` combining the trained Module 3 Fake News and LIAR models with Gemini narrative checking, returning standard verdicts: `MISINFORMATION DETECTED` or `CORRECT`.
6. **Search History & Caching**: Extends `SearchHistory` database model with summary, fact_check_result, articles_collected, processing_time, and search_status. Stores article metadata and association queries on SQLite.
7. **Complete Search API Endpoints**: Exposes endpoints (`POST /api/search`, `GET /api/search/<id>`, `GET /api/articles/<id>`, and `GET /api/search-history`) tied to authenticated JWT user identities.
8. **Responsive Search Dashboard UI**: Elegant dashboard client code updating UI elements: audit statistics cards (articles collected, unique sources, processing speed), summary blocks, and an expandable article accordion.
9. **Automated Verification Script**: Integrated `scripts/verify_module4.py` confirming correct API routing, SQLite table updates, fast caching (processing time from 14s to 11ms), and duplicate filtering.
10. **Hardening & Security Audits**: Integrated custom in-memory API rate-limiting `@rate_limit`, strict search query payload bounds verification (max 200 chars), SQLite connection event listener enforcement for `PRAGMA foreign_keys=ON` cascade deletes, and robust mock fallbacks for search and LLM API failures, all validated via `scripts/verify_hardening.py` regression tests.

---

## 🚀 Module 5A – Sentiment Intelligence Engine (Status: COMPLETED ✅)

### Implemented Features
1. **Safe Database Migration Strategy**: Evolved table schema using Alembic, adding columns `search_id`, `dominant_emotion`, `confidence`, `risk_level`, and `model_version` to `SentimentResult` (legacy columns kept nullable for compatibility), and overall cache fields to `SearchHistory`.
2. **Standardized Risk Grading & Probability Normalization**: Converts predictions to 0-100% percentages, applying tiered risk evaluations (`LOW`/`MEDIUM`/`HIGH`) based on `Fear` (>40% HIGH, >20% MEDIUM) and `Fear + Anger` (>60% HIGH, >30% MEDIUM).
3. **Sentiment Result Caching & Duplicate Prevention**: If all articles associated with a search have sentiment analyses, bypass inference and return stored entries directly with `cached: true`. Employs upsert logic to avoid duplicate rows.
4. **Batch Processing Optimization**: Leverages `nlp_service.preprocess_texts_batch` and batch vectorizer transforms to evaluate whole article sets simultaneously.
5. **Dynamic Dashboard Charting**: Renders Emotion Pie Chart and Emotion Bar Chart inside `dashboard.html` using Chart.js, featuring PNG exports, loading transitions, and search history auto-loading.
6. **Graceful Failures & Fallbacks**: Returns HTTP `503 Service Unavailable` on missing model files without crashing the server.
7. **Automated Verification Script**: Created `scripts/verify_sentiment.py` verifying all rules, caching, rate limiting, and fallbacks.

---

## 🚀 Module 5B – Narrative Evolution Tracking (Status: COMPLETED ✅)

### Implemented Features
1. **Upgraded SQLite Database Schemas**: Shifted `EvolutionResult` model to track chronological search analysis aggregates (`baseline_article_id`, `narrative_drift_score`, `total_variants_detected`, `dominant_narrative`, `evolution_summary`, `mutation_points_json`, `timeline_json`). Configured cascading purges on parent deletion.
2. **Dynamic Vectorization & Cosine Similarity Matrix**: Vectorizes article collections via TF-IDF (incorporating custom preprocessed spaCy tokens) and calculates $N \times N$ similarity mappings.
3. **Hierarchical Narrative Clustering**: Groups articles into variant streams using scikit-learn `AgglomerativeClustering` based on cosine distance.
4. **Weighted Narrative Drift Formula**: Computes temporal drift score ($0-100\%$) indicating `Stable`, `Moderate`, or `Significant` mutation compared to the timeline baseline article.
5. **Emerging Themes (Keywords) & Mutation Extraction**: Extracts top 10 keywords overall based on TF-IDF sum of weights. Flags consecutive timeline pairs whose similarity drops below $85\%$ as narrative mutation points.
6. **Gemini 1.5 Flash Summary & Custom Fallback**: Generates narrative evolution analysis summaries via Gemini API, falling back to a detailed template-based report for offline operations.
7. **REST APIs & Route Caching**: Implemented JWT-protected endpoints (`POST /api/evolution/analyze` and `GET /api/evolution/<search_id>`) that serve cached runs immediately and prevent duplicate DB writes.
8. **Interactive UI Timeline & Cluster Charts**: Fully enabled the "Generate Evolution Analysis" button in `dashboard.html` (unlocks after sentiment analysis is done). Renders Narrative Drift score badges, total variants count, theme keyword tags, interactive chronological timelines with flagged mutation alerts, and Chart.js cluster distribution doughnut charts.
9. **Automated Verification Script**: Created `scripts/verify_evolution.py` validating auth controls, access isolation, empty sets, single articles, drift score bounds, clustering, caching, cascade deletes, and ordering fallbacks.



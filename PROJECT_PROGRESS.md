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
│   ├── blueprints/              # Routing layers
│   │   ├── __init__.py          # Blueprint package module
│   │   ├── auth.py              # JWT authentication: signup & login
│   │   ├── user.py              # User profile retrieval & update, role checks
│   │   ├── api.py               # Standardized API response utilities
│   │   └── main.py              # Page rendering, system health validation
│   ├── services/                # Placeholders for future business logic blocks
│   │   ├── __init__.py          # Bundle services
│   │   ├── search_service.py    # Google Custom Search API placeholder
│   │   ├── scraping_service.py  # BS4 Web scraping parsing placeholder
│   │   ├── fact_checking_service.py # Gemini LLM fact check auditing placeholder
│   │   ├── sentiment_service.py # Sentiment model classification placeholder
│   │   ├── evolution_service.py # Mutator story tracking placeholder
│   │   ├── similarity_service.py # Vector text similarity placeholder
│   │   ├── clustering_service.py # Narratives clustering placeholder
│   │   ├── visualization_service.py # Chart metadata generation placeholder
│   │   ├── knowledge_graph_service.py # Semantic triples construction placeholder
│   │   ├── report_service.py    # PDF export pipeline placeholder
│   │   ├── dataset_service.py   # Dataset manager layer (Fake News, LIAR, Emotion)
│   │   └── utils.py             # Shared utility functions
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css        # Apple + Notion variables, typography and scrollbar styles
│   │   └── js/
│   │       └── app.js           # Client actions: theme toggling, toasts, modals, loader
│   └── templates/
│       ├── base.html            # Premium dashboard master frame structure
│       └── index.html           # Landing page content workspace
├── bruno/                       # Bruno Collection suite
│   └── MET-Collection/
│       ├── bruno.json           # Bruno configuration
│       ├── environments/
│       │   └── Local.bru        # Base URL and Bearer Token variables
│       ├── Health Check.bru
│       ├── User Registration.bru
│       ├── User Login.bru
│       ├── Get Profile.bru
│       └── Update Profile.bru
├── .env.example                 # Env parameters template
├── .env                         # Preconfigured development env variables
├── .gitignore                   # Exclusions: Virtualenv, build, logs, databases, IDE files
├── app.py                       # App running entrypoint (python app.py)
├── requirements.txt             # Production-grade requirements list
└── PROJECT_PROGRESS.md          # Project roadmap tracking document (this file)
```

---

## 📊 Database, API, and Dataset Statuses

### 1. Database Status (SQLite)
* **Status**: INITIALIZED & TESTED
* **Schema**: Created User, SearchHistory, Article, FactCheckResult, SentimentResult, EvolutionResult, NarrativeCluster, and SystemLog schemas with foreign key references, timestamps, indices, and delete cascade behaviors.
* **Auto-Init**: Dynamically initializes `app.db` automatically on first run via app context.

### 2. API Endpoint Status
* **API Version**: `v1`
* **Response Wrapper**: Enforces `{"success": true, "message": "...", "data": {...}}` response payload consistency globally.
* **Endpoints**:
  * `GET /api/health` 🟢 (Online)
  * `POST /api/auth/register` 🟢 (Online)
  * `POST /api/auth/login` 🟢 (Online)
  * `GET /api/users/profile` 🔑 (Requires Bearer token, Online)
  * `PUT /api/users/profile` 🔑 (Requires Bearer token, Online)

### 3. Dataset Status
* **Directories Connected**:
  * `MET/Fake News Detection` (Exists in root directory)
  * `MET/LIAR Dataset` (Exists in root directory)
  * `MET/Emotion Dataset` (Exists in root directory)
* **Integration Layer**: `DatasetService` class in `app/services/dataset_service.py` initialized to references paths, with placeholders configured for loading standard schemas in future modules.

---

## ⚠️ Known Issues / Limitations
* External APIs (Gemini, Google Custom Search) and model processes are currently represented by placeholder routines. They will be integrated in subsequent modules.

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

## 🔮 Next Module – Module 3: Datasets Integration & Sentiment Analytics
* Setup pipelines to load, clean, and map the Fake News, LIAR, and Emotion datasets.
* Integrate NLP layers utilizing nltk / spacy.
* Implement sentiment scoring and emotional profile indexing.


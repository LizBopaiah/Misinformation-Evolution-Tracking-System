# MET (Misinformation Detection & Evolution Tracking System)
## Comprehensive Platform User Guide & Module Walkthrough

Welcome to the official user and researcher manual for the **Misinformation Detection & Evolution Tracking System (MET)**. This guide provides an in-depth, step-by-step manual detailing every section, dashboard, analytic tool, and workspace module available across the navigation bar.

---

## 📑 Table of Contents

1. [Platform Architecture & Navigation Overview](#1-platform-architecture--navigation-overview)
2. [Authentication & Session Setup (Login / Register / Theme)](#2-authentication--session-setup)
3. [Home & Public Landing Page (`/`)](#3-home--public-landing-page-)
4. [About Platform Guide (`/about-platform`)](#4-about-platform-guide-about-platform)
5. [Dashboard: Primary Analysis Console (`/dashboard`)](#5-dashboard-primary-analysis-console-dashboard)
   - *Search & Query Input Console*
   - *Analysis Summary & Narrative Synthesis*
   - *Fact Audit Profile & Hybrid Veracity Classification*
   - *Article Scraping & Deduplication Panel*
   - *Sentiment & Emotional Manipulation Index*
   - *Narrative Evolution Lineage & Mutation Tree*
   - *Thematic Narrative Clustering*
   - *Interactive Semantic Knowledge Graph*
   - *Source Credibility & Domain Trust Engine*
   - *Explainable AI (XAI) Feature Attribution*
6. [Investigation Workspace & Cases (`/cases`)](#6-investigation-workspace--cases-cases)
   - *Creating & Categorizing Cases*
   - *Linking Evidence & Analysis Snapshots*
   - *Timeline Auditing & Investigator Notes*
   - *Case Dossier Generation*
7. [Search History Audit Log (`/search-history`)](#7-search-history-audit-log-search-history)
8. [Comparative Analytics & Intelligence Engine (`/research`)](#8-comparative-analytics--intelligence-engine-research)
   - *Multi-Topic Selection (2–10 Queries)*
   - *Semantic Overlap & Sentiment Divergence*
   - *Snapshot Archiving & Report Exports*
9. [Evidence Dossiers & Export Center (`/exports`)](#9-evidence-dossiers--export-center-exports)
   - *Quota Management & Storage Tracking*
   - *Filtering & Downloading PDF/HTML Dossiers*
10. [Profile & Settings Management (`/profile`)](#10-profile--settings-management-profile)
    - *Profile Picture Customization*
    - *Account Credentials & Security*
    - *API Key Configuration (Gemini & Google Custom Search)*
11. [System Overview & Diagnostics (`/system-overview`)](#11-system-overview--diagnostics-system-overview)
    - *Real-time Health Monitors*
    - *Dataset Health & Validation Stats*
    - *Model Accuracy & Benchmark Matrix*
    - *Centralized Application Log Viewer*
12. [End-to-End Investigation Walkthrough (Example Scenario)](#12-end-to-end-investigation-walkthrough)

---

## 1. Platform Architecture & Navigation Overview

The MET navigation bar is fixed at the top of every screen and dynamically adapts based on your authentication status:

```
[Brand Logo: MET Research]  [Home]  [About Platform]  [Dashboard]  [Investigation Workspace]  [Search History]  [Comparative Analytics]  [Dossiers & Exports]  [Profile]  [System Overview]  [☀️/🌙 Theme Toggle]  [Avatar Menu]
```

### Global Header Controls

| Control | Location | Function |
| :--- | :--- | :--- |
| **MET Research Logo** | Leftmost item | Returns directly to the root landing page (`/`) or active workspace. |
| **Theme Toggle** | Right side (Moon/Sun icon) | Instantly switches the entire platform between **Dark Mode** (slate-950) and **Light Mode** (slate-50), persisting your preference in `localStorage`. |
| **User Avatar / Pill** | Top-Right Corner | Displays your user initials or uploaded photo. Hovering opens a dropdown menu to jump directly to **My Profile** or trigger a secure **Logout**. |

---

## 2. Authentication & Session Setup

Protected views (`/dashboard`, `/cases`, `/research`, `/exports`, `/profile`, `/search-history`, `/system-overview`) require a valid JWT token stored in `localStorage`.

### Step 1: Register an Account
1. Navigate to `/register` or click **Register** from the landing page.
2. Enter your:
   - **Full Name** (e.g., `Dr. Jane Doe`)
   - **Email Address** (must be unique and valid format)
   - **Password** (must meet minimum security length)
3. Click **Create Account**. 
4. Upon successful creation, MET automatically generates your JWT token, initializes your default settings, and redirects you directly to the **Dashboard**.

### Step 2: Logging In
1. Navigate to `/login`.
2. Enter your registered email address and password.
3. Click **Sign In**.
4. The system issues a 24-hour JWT token (`access_token`) and redirects you to the requested destination.

### Step 3: Logging Out
1. Hover over your circular profile avatar in the top right.
2. Click the red **Logout** option.
3. The platform clears your local authentication token and redirects you safely to `/login`.

---

## 3. Home & Public Landing Page (`/`)

### Purpose
The visitor-facing landing page introduces the platform, showcases research capabilities, provides quick search samples, and guides journalists, students, and intelligence analysts through the verification pipeline.

### Key Sections
- **Hero Title & Value Proposition:** High-level summary of the multi-module analysis engine.
- **Direct Search Bar:** Allows immediate exploration with suggested query pills (e.g., *"COVID vaccine infertility"*, *"5G causes cancer"*).
- **Core Feature Capabilities:** Cards describing Fact Verification, Emotion Indexing, Mutation Lineage Trees, and Knowledge Graphs.
- **Methodology Pipeline Flow:** Visual diagram showing the path from Claim Input &rarr; Web Scraping &rarr; Deduplication &rarr; Model Scoring &rarr; Graph Projection.

### How to Use
1. If not logged in, read through the platform introduction.
2. Click on any suggested query button or type a search into the central bar.
3. If unauthenticated, clicking **Analyze** will prompt you to log in or register before persisting and running the computation.

---

## 4. About Platform Guide (`/about-platform`)

### Purpose
A public reference document detailing the algorithmic methodologies, scientific foundations, and research standards used by MET.

### What it Details
- **Fact Verification:** How the hybrid classifier references the LIAR benchmark and Fake News datasets to evaluate claims.
- **Sentiment & Emotion Analysis:** How emotional manipulation (fear, hostility, panic, joy) is calculated using multi-class emotion datasets.
- **Narrative Evolution Tracking:** The methodology behind vector similarity, TF-IDF lexical drift, and parent-child story mutation trees.
- **Knowledge Graph Representation:** The extraction of semantic triples `(Subject -> Predicate -> Object)` into interactive nodes.
- **Source Reliability & Trust Scoring:** Domain credibility grading from A+ to F.

---

## 5. Dashboard: Primary Analysis Console (`/dashboard`)

The **Dashboard** is the core operational workspace for single-claim investigations.

```
┌─────────────────────────────────────────────────────────────┐
│                    Search & Claim Bar                       │
└─────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┴─────────────────────────┐
    ▼                                                   ▼
┌───────────────────────────────┐   ┌─────────────────────────┐
│     Narrative Summary         │   │   Fact Audit Profile    │
│  (Gemini / Local Extractive)  │   │  (Hybrid Veracity Rate) │
└───────────────────────────────┘   └─────────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    ▼                         ▼                         ▼
┌───────────────┐     ┌───────────────┐     ┌─────────────────┐
│ Sentiment &   │     │ Narrative     │     │ Thematic        │
│ Emotion Chart │     │ Mutation Tree │     │ Clusters        │
└───────────────┘     └───────────────┘     └─────────────────┘
                              │
    ┌─────────────────────────┴─────────────────────────┐
    ▼                                                   ▼
┌───────────────────────────────┐   ┌─────────────────────────┐
│  Knowledge Graph (Triples)    │   │ Explainable AI (XAI)    │
└───────────────────────────────┘   └─────────────────────────┘
```

### Detailed Steps to Run an Audit:

#### Step 1: Input Claim or Headline
1. In the central input box, enter a specific statement, rumor, or news headline (e.g., `5G towers transmit viral infections`).
2. Alternatively, click one of the quick example pills below the input.
3. Click the purple **Analyze** button.

#### Step 2: Automated Pipeline Execution
While the global spinner displays, the platform automatically executes:
- **Search Retrieval:** Queries Google Custom Search API (with cached fallbacks).
- **Web Scraping:** Downloads article contents using multi-method scrapers (BeautifulSoup/Newspaper3k).
- **Text Deduplication:** Computes TF-IDF cosine similarity to remove near-duplicate republishings (>0.95 similarity).
- **Summarization:** Runs Gemini LLM summarization (or localized extractive fallback).
- **Fact-Checking Verdict:** Runs trained Scikit-Learn/TensorFlow estimators alongside rule-based fact heuristics.
- **Emotion & Sentiment Scoring:** Breaks down the tone into compound positivity/negativity and 6 distinct emotional channels.
- **Evolution Tree Construction:** Discovers parent-child mutation branches across publication timestamps.
- **Semantic Triple Extraction:** Identifies entities and relations for the knowledge graph.
- **Source Credibility Evaluation:** Grades each publishing domain.

#### Step 3: Interpret Dashboard Panels

1. **Analysis Summary:**
   - Highlights the core thesis of collected articles.
   - Highlights consensus versus contradictory findings.

2. **Fact Audit Profile:**
   - **Veracity Rating:** Clear badge (`TRUE`, `PARTIALLY TRUE`, `MISINFORMATION DETECTED`, or `UNVERIFIED`).
   - **Articles Collected & Sources Used:** Total documents parsed.
   - **Avg Source Trust:** Aggregated credibility score of publishing outlets.
   - **Processing Time:** Real-time computation latency in seconds.

3. **Article Sources Grid:**
   - Shows article titles, publication domains, and publication dates.
   - Click **Open Source** to inspect original source material in a new tab.
   - Displays individual domain trust grades (e.g., `A`, `B-`, `F`).

4. **Sentiment & Emotion Breakdown:**
   - **Compound Tone Score:** Scale from -1.0 (Extreme Negative) to +1.0 (Extreme Positive).
   - **Radar/Bar Emotion Distribution:** Quantifies percentages of **Joy**, **Sadness**, **Anger**, **Fear**, **Love**, and **Surprise**.
   - **Manipulation Indicator:** High concentrations of Fear or Anger (>40%) automatically flag potential emotional manipulation.

5. **Narrative Evolution & Mutation Tree:**
   - Traces the chronological adaptation of the story.
   - Demonstrates how early moderate headlines escalated into radicalized or distorted variants over time.
   - Interactive nodes can be hovered to reveal timestamp, lexical drift delta, and source publisher.

6. **Narrative Thematic Clusters:**
   - Groups articles into distinct sub-narratives (e.g., *"Scientific Consensus"*, *"Conspiracy Theories"*, *"Government Directives"*).

7. **Interactive Knowledge Graph:**
   - Visualizes extracted semantic triples: **Subject Node** &rarr; **Predicate Edge** &rarr; **Object Node**.
   - Allows dragging, zooming, and clicking nodes to trace narrative relationships between organizations, people, and claims.

8. **Explainable AI (XAI) & Feature Attribution:**
   - Visualizes word importance weights showing *why* the classifier reached its verdict.
   - Green tokens indicate credible/corroborating indicators; red tokens highlight linguistic hallmarks of fabricated content.

#### Step 4: Action Buttons (Top Right of Results)
- **📋 Export Fact Audit (PDF):** Generates a concise single-claim audit sheet.
- **🔍 Export XAI (PDF):** Exports the explainability and token importance breakdown.
- **📁 Export Dossier (PDF):** Compiles all charts, sources, and graphs into a formal PDF report.
- **📂 Add To Case:** Opens a modal to file this search under an active investigation case folder.

---

## 6. Investigation Workspace & Cases (`/cases`)

### Purpose
The **Investigation Workspace** serves as a case management system for researchers managing long-term investigations across multiple claims, stories, and sources.

```
┌─────────────────────────────────────────────────────────────┐
│  Stats: Total Cases | Active | Archived | High Priority     │
└─────────────────────────────────────────────────────────────┘
 ┌──────────────────────┐  ┌─────────────────────────────────┐
 │   Case Containers    │  │       Selected Case Workspace   │
 │   - Case 1 (Active)  │  │  - Case Metadata & Status       │
 │   - Case 2 (Open)    │  │  - Linked Search Records        │
 │   - Case 3 (Archived)│  │  - Attached Dossiers & Evidence │
 │                      │  │  - Activity Log & Notes         │
 │  [+ New Case]        │  │  [Export Case Dossier]          │
 └──────────────────────┘  └─────────────────────────────────┘
```

### Step-by-Step Instructions:

#### Creating a New Case
1. Navigate to `/cases`.
2. Click **➕ New Investigation Case**.
3. In the modal dialog, fill in:
   - **Case Title:** (e.g., `Operation Disinfo: Winter Flu Myths 2026`)
   - **Description:** Summary of investigation objectives.
   - **Priority:** `LOW`, `MEDIUM`, or `HIGH`.
   - **Status:** `OPEN` or `ACTIVE`.
   - **Tags:** Comma-separated labels (e.g., `vaccines, health, viral`).
4. Click **Save Case Container**.

#### Managing Case Evidence
1. Click on any case card from the left-hand list.
2. The right panel displays the active workspace:
   - **Case Metadata:** Edit title, change status (`COMPLETED`, `ARCHIVED`), or update priority.
   - **Linked Elements:** View all search queries, reports, or articles filed into this case.
   - **Investigator Notes:** Add timestamped analytical observations and working hypotheses.
   - **Activity Timeline:** Review an immutable log of when items were linked, notes added, or status changed.
3. Click **Export Case Dossier** to compile all linked elements and notes into an investigation dossier.

---

## 7. Search History Audit Log (`/search-history`)

### Purpose
Maintains a persistent, chronological registry of every claim analyzed under your user account.

### How to Use:
1. Navigate to `/search-history`.
2. Inspect the historical list displaying:
   - **Query String:** The exact search term or claim.
   - **Timestamp:** Date and time of audit.
   - **Execution Status:** Green `completed`, amber `pending`, or red `failed`.
   - **Dominant Emotion Tag:** Quick badge indicating the leading emotional marker.
   - **Summary Snippet:** Brief preview of the findings.
3. **One-Click Reload:** Click anywhere on a history card to instantly reload that analysis into the **Dashboard** without waiting for re-computation.

---

## 8. Comparative Analytics & Intelligence Engine (`/research`)

### Purpose
Enables cross-topic intelligence by comparing between **2 and 10 separate queries** from your search history.

```
┌───────────────────────────────┐   ┌─────────────────────────────────────────┐
│     Selection Console         │   │         Comparative Intelligence        │
│ 1. Enter Report Name          │   │  - Comparative Synthesis Overview       │
│ 2. Check 2-10 Historical      │   │  - Emotional Divergence Charts          │
│    Queries to compare         │   │  - Lexical Similarity Overlap           │
│                               │   │  - Veracity Consensus vs. Disagreement  │
│ [Generate Comparative Report] │   │  [Export PDF] [Export HTML] [Export JSON│
└───────────────────────────────┘   └─────────────────────────────────────────┘
```

### Detailed Steps to Run a Comparison:

1. Navigate to `/research`.
2. In the left console:
   - Enter a **Report Name** (e.g., `Climate vs Pandemic Conspiracy Narrative Divergence`).
   - From the checkboxes of completed queries, select **at least two queries** (up to 10).
3. Click **Generate Comparative Report**.
4. The system calculates cross-narrative metrics and displays:
   - **Comparative Synthesis:** High-level summary of shared framing and divergent narratives.
   - **Emotional Divergence Radar/Bar Chart:** Overlays the emotional profiles of both topics to highlight contrasting psychological triggers.
   - **Lexical Similarity Matrix:** Heatmap showing text and keyword overlap between the two narrative pools.
   - **Veracity Consensus Table:** Compares the fact-check outcomes side-by-side.
5. Use the export buttons at the top right of the report panel:
   - **📥 Export JSON:** Raw analytical data for external data science workflows.
   - **🌐 Export HTML:** Standalone interactive HTML report.
   - **🖨️ Export PDF:** Formatted printable document.

---

## 9. Evidence Dossiers & Export Center (`/exports`)

### Purpose
Central repository for managing, filtering, previewing, and downloading all generated export files.

### Key Features:
- **Storage Metrics:** Displays total files saved, cumulative disk space consumed, and your 24-hour quota utilization (e.g., `4 / 50 exports used`).
- **Dynamic Search & Filtering:**
  - Search by filename or claim title.
  - Filter by export type: `Fact Audit`, `Sentiment`, `Evolution`, `Comparison`, `Dossier`, or `Explainability`.
- **Action Table:**
  - **Filename / Metadata:** Name, size, and date created.
  - **Format Badge:** `PDF`, `HTML`, or `JSON`.
  - **Download Button:** Direct download to your local machine.
  - **Delete Button:** Removes the export from the database and deletes the file from disk.

---

## 10. Profile & Settings Management (`/profile`)

### Purpose
Manage user credentials, upload personal researcher profile photos, track platform utilization, and configure third-party API keys.

### Step-by-Step Instructions:

#### Uploading a Profile Picture
- **Method A (File Picker):** Hover over the circular avatar in the header and click the camera icon. Select an image (`.png`, `.jpg`, `.jpeg`, `.webp`, max 5MB).
- **Method B (Drag & Drop):** Drag an image directly into the dashed dropzone card at the bottom of the profile page.
- **Removing Photo:** Click **Remove photo** under your name to reset to default initials.

#### Updating Name & Password
1. In the **Edit Profile Details** form, enter your updated **Full Name**.
2. If changing passwords, enter a new password in the **New Password** field (leave blank to keep current).
3. Click **Save Changes**. (Email address is permanently linked to your account for data isolation and cannot be altered).

#### Configuring API Keys (External Integrations)
1. In the **External API Integration** section of the profile:
   - **Google Custom Search API Key & Engine ID:** Enables live Google Search indexing beyond local cached fallbacks.
   - **Gemini API Key:** Enables advanced Gemini LLM synthesis and semantic reasoning.
2. Click **Save API Credentials**. Keys are encrypted and stored in application configuration.

---

## 11. System Overview & Diagnostics (`/system-overview`)

### Purpose
A dedicated technical console for platform administrators, evaluators, and system auditors to verify system health, dataset counts, model metrics, and real-time logs.

```
┌───────────────────────┐  ┌──────────────────────────────────────────────────┐
│  System Monitors      │  │  Architecture & Pipeline Stages                 │
│  - API Gateway: OK    │  │  [Search] -> [Scrape] -> [NLP] -> [Fact/Emotion]│
│  - SQLite DB: OK      │  ├──────────────────────────────────────────────────┤
│  - NLP Engine: Active │  │  Preloaded Dataset Health Table                 │
├───────────────────────┤  │  - Fake News: 44,898 records                    │
│  Preloaded Datasets   │  │  - LIAR: 12,791 records                         │
│  - Fake News: Loaded  │  │  - Emotion: 20,000 records                      │
│  - LIAR: Loaded       │  ├──────────────────────────────────────────────────┤
│  - Emotion: Loaded    │  │  Model Performance Benchmarks                   │
├───────────────────────┤  │  - Accuracy, F1-Scores, Confusion Matrices      │
│  Classification Models│  ├──────────────────────────────────────────────────┤
│  - Fake News: Active  │  │  Live Application Log Stream (Tail)             │
│  - LIAR: Active       │  │  Real-time INFO, WARNING, and ERROR logs        │
└───────────────────────┘  └──────────────────────────────────────────────────┘
```

### Sections Explained:
1. **Live System Health Monitors:** Real-time ping indicators for the API Gateway, SQLite Database connection, and spaCy NLP pipeline.
2. **Preloaded Dataset Table:** Row counts, label balances, and file verification for:
   - **Fake News Dataset:** 44,898 records (Real vs. Fake).
   - **LIAR Dataset:** 12,791 records (PolitiFact truth tiers).
   - **Emotion Dataset:** 20,000 records (6 emotion labels).
3. **Machine Learning Model Benchmarks:** Confusion matrices, accuracy percentages, and F1-scores for the active classifier models.
4. **Live Application Log Viewer:** Displays the latest log entries from `logs/application.log` with filtering by severity (`INFO`, `WARNING`, `ERROR`).

---

## 12. End-to-End Investigation Walkthrough

Here is a recommended operational workflow for conducting an end-to-end investigation:

```
[1. Create Case Folder]
        │
        ▼
[2. Execute Dashboard Searches] ──► Inspect Fact Veracity, Emotions & Mutation Tree
        │
        ▼
[3. File Evidence into Case] ────► Add Key Queries & Narrative Summaries
        │
        ▼
[4. Run Comparative Analytics] ──► Compare Competing Rumors & Identify Overlaps
        │
        ▼
[5. Export Formal Dossier] ─────► Download Publication-Ready Investigation PDF
```

### Practical Scenario: Auditing a Viral Medical Claim

1. **Step 1: Open Investigation Workspace (`/cases`)**
   - Click **➕ New Investigation Case**.
   - Title: `COVID-19 Infertility Myth Tracking`.
   - Set Priority to `HIGH` and Status to `ACTIVE`.

2. **Step 2: Run Primary Analysis (`/dashboard`)**
   - Enter claim: `"COVID vaccine causes female infertility"`.
   - Click **Analyze**.
   - Review Verdict: Evaluated as `MISINFORMATION DETECTED`.
   - Review Sentiment: High concentration of `Fear` (42%) and `Anger` (28%).
   - Review Mutation Tree: Traces claim origin back to distorted interpretations of syncytin-1 protein homologies.
   - Click **Add To Case** &rarr; Select `COVID-19 Infertility Myth Tracking`.

3. **Step 3: Run Comparative Variant Analysis (`/dashboard`)**
   - Enter secondary rumor: `"mRNA changes human DNA structure"`.
   - Click **Analyze**.
   - Review findings and click **Add To Case** &rarr; Link to same case.

4. **Step 4: Cross-Analyze in Comparative Analytics (`/research`)**
   - Navigate to `/research`.
   - Set Report Name: `mRNA Misinformation Family Synthesis`.
   - Check both queries: `"COVID vaccine causes female infertility"` and `"mRNA changes human DNA structure"`.
   - Click **Generate Comparative Report**.
   - Review the lexical overlap heatmap and shared emotional trigger profile.

5. **Step 5: Export Evidence Dossier (`/exports` or `/cases`)**
   - Navigate to `/cases` and open `COVID-19 Infertility Myth Tracking`.
   - Review attached findings, timeline, and analyst notes.
   - Click **Export Case Dossier**.
   - Navigate to `/exports` and download the generated publication-ready **PDF Dossier**.

---

## 13. Troubleshooting & Frequently Asked Questions

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Authentication credentials are required or invalid" (401)** | Token expired or not logged in. | Navigate to `/login` and re-authenticate. |
| **Search returns cached results** | The exact claim was audited previously. | MET uses smart caching to prevent redundant scraping. If fresh results are required, alter keyword framing slightly. |
| **Scraper indicates fallback content** | Target news website has Cloudflare or anti-bot protection. | MET automatically triggers its high-quality fallback parser without interrupting analysis. |
| **Quota limit warning in Exports** | 24-hour export ceiling reached (50 files). | Download existing dossiers to your workstation and delete older files from `/exports`. |

---

*Misinformation Detection and Evolution Tracking System (MET) &bull; Built for Academic, Journalistic, and Open-Source Intelligence (OSINT) Verification.*

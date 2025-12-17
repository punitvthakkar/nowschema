# Uniclass Auto-Tagger Project

## Overview

This project automates the translation of natural language element names to Uniclass 2015 classification codes for MEP contractors in the UK construction industry.

### The Problem

MEP (Mechanical, Electrical, Plumbing) contractors receive drawings from architects with natural language element names. They must tag these elements with standardized Uniclass codes for compliance and interoperability. Currently, this requires hiring consultants to manually translate each element name—a costly and time-consuming process.

### The Solution

An AI-powered semantic search system that instantly matches natural language descriptions to the correct Uniclass 2015 codes, eliminating manual lookup and consultant fees.

---

## Current State: Proof of Concept

### Backend Infrastructure (Modal)

The backend is deployed on [Modal](https://modal.com) with two live applications:

#### 1. `uniclass-api` (Production API)
| Service | Hardware | Type |
|---------|----------|------|
| UniclassSearchService.* | T4 GPU | Web endpoint |

#### 2. `uniclass-embeddings` (ML Pipeline)
| Function | Hardware | Purpose |
|----------|----------|---------|
| build_hnsw_index | T4 GPU | Builds HNSW vector index for fast similarity search |
| download_results | CPU | Data retrieval utilities |
| embed_texts | T4 GPU | Generates embeddings using Nomic model |
| search_uniclass | T4 GPU | Performs semantic search against index |

---

## Technical Architecture

### Embeddings Model
- **Model**: Nomic (vector embeddings)
- **Training Data**: Complete Uniclass 2015 classification system
- **Coverage**: All code types including:
  - `Pr_` (Products)
  - `Ss_` (Systems)
  - `EF_` (Elements/Functions)
  - `Ac_` (Activities)
  - `SL_` (Spaces/Locations)
  - And other Uniclass tables

### Search Algorithm
- **Index Type**: HNSW (Hierarchical Navigable Small World)
- **Similarity Metric**: Cosine similarity
- **Response**: Returns code, title, table, and similarity score

---

## API Endpoints

### Base URLs
```
Search (GET):   https://punitvthakkar--uniclass-api-uniclasssearchservice-search-get.modal.run
Search (POST):  https://punitvthakkar--uniclass-api-uniclasssearchservice-search-post.modal.run
Batch Search:   https://punitvthakkar--uniclass-api-uniclasssearchservice-batch-search.modal.run
Health Check:   https://punitvthakkar--uniclass-api-uniclasssearchservice-health.modal.run
Statistics:     https://punitvthakkar--uniclass-api-uniclasssearchservice-stats.modal.run
```

### Authentication
All endpoints (except `/health`) require Bearer token authentication:
```
Authorization: Bearer <API_KEY>
```

### Single Search
**GET** `/search-get?q=<query>&top_k=<n>`

**POST** `/search-post`
```json
{
  "query": "door handle",
  "top_k": 5
}
```

### Batch Search
**POST** `/batch-search`
```json
{
  "queries": ["steel beam", "fire alarm", "window glazing"],
  "top_k": 3
}
```

### Response Format
```json
{
  "query": "door handle",
  "top_k": 5,
  "count": 5,
  "results": [
    {
      "code": "Pr_30_36_59_25",
      "title": "Door lever handle sets (Pr_30_36_59_25)",
      "table": "Products",
      "similarity": 0.743
    }
  ]
}
```

---

## Performance & Costs

| Metric | Value |
|--------|-------|
| Cold start | ~10 seconds |
| Warm request | <500ms |
| Cost per search | ~$0.001 |
| Modal free tier | $30/month credits |
| Scaling | Auto (0 to N containers) |

---

## Planned Frontend Clients

### 1. Revit Plugin (Primary)
- **Purpose**: Tag drawing elements directly within Autodesk Revit
- **Workflow**: 
  1. User selects elements on drawing
  2. Plugin extracts natural language names
  3. Batch query to API
  4. Returns matched Uniclass codes
  5. Codes applied to element metadata

### 2. Excel Plugin
- **Purpose**: Bulk processing via spreadsheet
- **Workflow**:
  1. Custom Excel formula (e.g., `=UNICLASS("door handle")`)
  2. Formula calls backend API
  3. Returns code name and code number to cells
- **Use Case**: Processing element schedules exported from CAD/BIM

### 3. Web Frontend
- **Purpose**: Quick lookups and testing
- **Features**:
  - Single query interface
  - Batch upload (CSV/Excel)
  - Results export

---

## Development Roadmap

### ✅ Completed
- [x] Uniclass 2015 data collection (all tables)
- [x] Nomic embeddings model training
- [x] HNSW index construction
- [x] Modal API deployment
- [x] Single search endpoint
- [x] Batch search endpoint
- [x] API authentication

### 🔄 In Progress
- [ ] Frontend client development
- [ ] Revit plugin architecture
- [ ] Excel add-in development

### 📋 Planned
- [ ] Web frontend UI
- [ ] User management & API key provisioning
- [ ] Usage analytics dashboard
- [ ] Rate limiting & billing integration
- [ ] Confidence threshold filtering
- [ ] Table-specific filtering (search only Pr_, only Ss_, etc.)

---

## File Structure

```
project/
├── backend/
│   ├── uniclass-api/          # Modal API service
│   │   └── UniclassSearchService
│   └── uniclass-embeddings/   # ML pipeline
│       ├── build_hnsw_index
│       ├── download_results
│       ├── embed_texts
│       └── search_uniclass
├── data/
│   └── uniclass_2015/         # Source classification data
├── docs/
│   └── UNICLASS_API_DOCS.md   # API documentation
└── frontends/                  # Planned
    ├── revit-plugin/
    ├── excel-addin/
    └── web-app/
```

---

## Key Value Proposition

| Traditional Process | With This Tool |
|---------------------|----------------|
| Hire consultant | Self-service API |
| Days/weeks turnaround | Instant results |
| £££ per project | ~£0.001 per query |
| Manual lookup tables | Semantic AI matching |
| Human error prone | Consistent accuracy |

---

## Notes for Development

- Modal containers scale to zero when idle—first request after idle has ~10s latency
- Batch search is more efficient for bulk operations
- Similarity scores help assess match confidence (higher = better match)
- Consider caching frequent queries on frontend clients

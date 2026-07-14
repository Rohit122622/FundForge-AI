# FundForge AI — Data Flow

## Grant Discovery Flow

```
User submits Startup Profile
        │
        ▼
grant_engine/matcher.py
  → Extracts keywords from profile
        │
        ▼
rag/retriever.py
  → Semantic search against IBM Vector Index
  → Returns top-N matching grant chunks
        │
        ▼
ibm/granite_model.py
  → Re-ranks and scores grant relevance
        │
        ▼
grant_engine/scorer.py + eligibility/checker.py
  → Applies eligibility rules
  → Returns scored & filtered grant list
        │
        ▼
Frontend: GrantFinderPage
```

## Proposal Generation Flow

```
User selects a Grant → clicks "Generate Proposal"
        │
        ▼
proposal_generator/prompt_builder.py
  → Builds structured prompt from:
     - Startup profile
     - Grant requirements (from RAG)
     - User instructions
        │
        ▼
ibm/granite_model.py
  → Sends prompt to IBM Granite
  → Streams response back
        │
        ▼
proposal_generator/formatter.py
  → Structures output into sections
        │
        ▼
Frontend: ProposalGeneratorPage (streamed display)
```


# AI Capital - Summarization Domain Refactoring Plan

This document outlines the plan to refactor the summarization domain to create a more robust, scalable, and feature-rich pipeline.

## Phase 1: Core Architecture & Metadata Service

*   [x] **1.1: Pydantic Models for Metadata**: Define `FilingMetadata` and `ChunkMetadata` schemas in a new `models.py` file within the summarizer domain. This ensures type safety and clear data contracts.
*   [x] **1.2: DynamoDB Service**: Create a new `DynamoDBMetadataService` responsible for all interactions with our DynamoDB table. It will handle creating the table, and CRUD operations for filing and chunk metadata.
*   [x] **1.3: Main Summarization Service**: Create a new `SummarizationService` that will act as the main entry point for the workflow. It will orchestrate calls to other services.
*   [x] **1.4: API Endpoint Refactoring**: Update the `summary_endpoint` to use the new `SummarizationService` and integrate the DynamoDB check for existing summaries.

## Phase 2: Document Chunking & Storage

*   [x] **2.1: Document Parsing Service**: Create a `DocumentParsingService` to fetch HTML from S3 and extract text from relevant sections.
*   [x] **2.2: Chunking Service**: Create a `ChunkingService` using LangChain's text splitters to break down section text into manageable chunks suitable for RAG and summarization.
*   [x] **2.3: S3 Chunk Storage**: Integrate logic into the `SummarizationService` to save the raw text of each chunk to a structured path in S3.
*   [x] **2.4: Update Metadata**: After storing chunks, update the `FilingMetadata` in DynamoDB with the corresponding `ChunkMetadata` (including S3 paths).

## Phase 3: Summarization Orchestration & Embeddings

*   [x] **3.1: LLM Orchestration Service**: Create an `LLMOrchestrationService` to manage the map-reduce summarization logic.
*   [x] **3.2: Prompt Construction**: Implement a `PromptConstructor` class to build dynamic prompts for both section-level and comprehensive summaries.
*   [x] **3.3: Embedding Service**: Create a placeholder `EmbeddingService` with a method to generate embeddings from text chunks. We will send the **raw text** of chunks for embedding to provide richer context for the future Q&A feature.
*   [x] **3.4: Integrate Orchestration**: Wire the `LLMOrchestrationService` and `EmbeddingService` into the main `SummarizationService` flow.

## Phase 4: Finalization & API Response

*   [x] **4.1: Store Final Summary**: Implement logic to save the final comprehensive summary (as a formatted HTML or Markdown file) to S3.
*   [x] **4.2: Final Metadata Update**: Update the `FilingMetadata` record in DynamoDB with the S3 link to the final summary report.
*   [x] **4.3: Return Presigned URL**: Update the `summary_endpoint` to return a presigned S3 URL for the newly created summary document.
*   [x] **4.4: Code Cleanup & Review**: Review all new modules for clarity, testability, and adherence to best practices. Add docstrings and comments where necessary.

---
## Review Section

The summarization domain has been successfully refactored into a modular, service-oriented architecture.

**Key Architectural Changes:**
1.  **Metadata-driven Workflow**: The entire process is now driven by a `FilingMetadata` record stored in DynamoDB, which tracks the status from chunking to completion.
2.  **Service-Oriented Design**: Logic has been decoupled into specialized services (`DynamoDB`, `Parsing`, `Chunking`, `LLMOrchestration`, `Embedding`), making the system more modular and maintainable.
3.  **Section-Aware Chunking**: The pipeline now intelligently parses documents into sections before chunking, providing better context for both summarization and future RAG features.
4.  **Hybrid Data Storage**: Raw text chunks and final summary documents are stored in S3 for cost-effective scalability, while all metadata is managed in DynamoDB for fast lookups.
5.  **Asynchronous by Design**: The core services are built with `async` methods, preparing the system for high-concurrency workloads.
6.  **Secure API Response**: The endpoint now returns a secure, temporary presigned S3 URL instead of exposing raw S3 paths.

This new architecture provides a robust and scalable foundation for all future summarization and question-answering features.

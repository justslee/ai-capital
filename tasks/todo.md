
# AI Capital - Summarization Domain Refactoring Plan

This document outlines the plan to refactor the summarization domain to create a more robust, scalable, and feature-rich pipeline.

## Phase 1: Core Architecture & Metadata Service

*   [ ] **1.1: Pydantic Models for Metadata**: Define `FilingMetadata` and `ChunkMetadata` schemas in a new `models.py` file within the summarizer domain. This ensures type safety and clear data contracts.
*   [ ] **1.2: DynamoDB Service**: Create a new `DynamoDBMetadataService` responsible for all interactions with our DynamoDB table. It will handle creating the table, and CRUD operations for filing and chunk metadata.
*   [ ] **1.3: Main Summarization Service**: Create a new `SummarizationService` that will act as the main entry point for the workflow. It will orchestrate calls to other services.
*   [ ] **1.4: API Endpoint Refactoring**: Update the `summary_endpoint` to use the new `SummarizationService` and integrate the DynamoDB check for existing summaries.

## Phase 2: Document Chunking & Storage

*   [ ] **2.1: Document Parsing Service**: Create a `DocumentParsingService` to fetch HTML from S3 and extract text from relevant sections.
*   [ ] **2.2: Chunking Service**: Create a `ChunkingService` using LangChain's text splitters to break down section text into manageable chunks suitable for RAG and summarization.
*   [ ] **2.3: S3 Chunk Storage**: Integrate logic into the `SummarizationService` to save the raw text of each chunk to a structured path in S3.
*   [ ] **2.4: Update Metadata**: After storing chunks, update the `FilingMetadata` in DynamoDB with the corresponding `ChunkMetadata` (including S3 paths).

## Phase 3: Summarization Orchestration & Embeddings

*   [ ] **3.1: LLM Orchestration Service**: Create an `LLMOrchestrationService` to manage the map-reduce summarization logic.
*   [ ] **3.2: Prompt Construction**: Implement a `PromptConstructor` class to build dynamic prompts for both section-level and comprehensive summaries.
*   [ ] **3.3: Embedding Service**: Create a placeholder `EmbeddingService` with a method to generate embeddings from text chunks. We will send the **raw text** of chunks for embedding to provide richer context for the future Q&A feature.
*   [ ] **3.4: Integrate Orchestration**: Wire the `LLMOrchestrationService` and `EmbeddingService` into the main `SummarizationService` flow.

## Phase 4: Finalization & API Response

*   [ ] **4.1: Store Final Summary**: Implement logic to save the final comprehensive summary (as a formatted HTML or Markdown file) to S3.
*   [ ] **4.2: Final Metadata Update**: Update the `FilingMetadata` record in DynamoDB with the S3 link to the final summary report.
*   [ ] **4.3: Return Presigned URL**: Update the `summary_endpoint` to return a presigned S3 URL for the newly created summary document.
*   [ ] **4.4: Code Cleanup & Review**: Review all new modules for clarity, testability, and adherence to best practices. Add docstrings and comments where necessary.

---
## Review Section

*A summary of all changes made during this refactoring will be added here upon completion.*

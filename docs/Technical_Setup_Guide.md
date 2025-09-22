# BigQuery AI Legal Platform - Technical Setup Guide

## Prerequisites & Requirements

### Google Cloud Platform Setup
- **Google Cloud Project** with BigQuery API enabled
- **Service Account** with BigQuery Admin permissions
- **BigQuery AI Functions** access (Preview/GA features)
- **Billing Account** configured for BigQuery AI usage

### Required APIs & Services
```bash
gcloud services enable bigquery.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable bigquerydatapolicy.googleapis.com
```

### Authentication Setup
1. Create service account key:
   ```bash
   gcloud iam service-accounts create bigquery-ai-legal
   gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:bigquery-ai-legal@PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/bigquery.admin"
   ```

2. Download service account key:
   ```bash
   gcloud iam service-accounts keys create gcloud-srvc-acc-key.json \
       --iam-account=bigquery-ai-legal@PROJECT_ID.iam.gserviceaccount.com
   ```

## Installation Steps

### 1. Dataset Creation
```sql
-- Create main dataset for legal documents
CREATE SCHEMA `PROJECT_ID.enterprise_documents`
OPTIONS(
    description="BigQuery AI Legal Document Discovery Platform",
    location="US"
);
```

### 2. Legal Document Table Setup
```sql
-- Create legal documents table
CREATE OR REPLACE TABLE `PROJECT_ID.enterprise_documents.legal_documents` (
    doc_id STRING NOT NULL,
    title STRING,
    content STRING,
    court STRING,
    case_name STRING,
    jurisdiction STRING,
    word_count INT64,
    creation_date DATE,
    legal_category STRING
)
OPTIONS(
    description="Legal document corpus with Supreme Court opinions and patent cases"
);
```

### 3. Native BigQuery AI Model Creation
```sql
-- Create Google AI text embedding model
CREATE OR REPLACE MODEL `PROJECT_ID.enterprise_documents.legal_text_embedding_model`
OPTIONS(
    model_type='TEXT_EMBEDDING',
    model_name='textembedding-gecko@003'
);
```

### 4. Legal Document Embeddings Table
```sql
-- Generate embeddings for all legal documents
CREATE OR REPLACE TABLE `PROJECT_ID.enterprise_documents.legal_document_embeddings` AS
SELECT 
    doc_id,
    title,
    content,
    court,
    case_name,
    jurisdiction,
    word_count,
    ML.GENERATE_EMBEDDING(
        MODEL `PROJECT_ID.enterprise_documents.legal_text_embedding_model`,
        content
    ) as content_embedding,
    ML.GENERATE_EMBEDDING(
        MODEL `PROJECT_ID.enterprise_documents.legal_text_embedding_model`, 
        CONCAT(title, ' ', case_name)
    ) as title_embedding,
    CURRENT_TIMESTAMP() as processed_timestamp
FROM `PROJECT_ID.enterprise_documents.legal_documents`;
```

### 5. Native Legal Vector Search Function
```sql
-- Create production legal vector search function
CREATE OR REPLACE FUNCTION `PROJECT_ID.enterprise_documents.native_legal_vector_search`(
    query_text STRING,
    top_k INT64
)
RETURNS ARRAY<STRUCT<
    doc_id STRING,
    title STRING,
    case_name STRING,
    court STRING,
    similarity_score FLOAT64,
    content_preview STRING
>>
LANGUAGE SQL AS (
    WITH query_embedding AS (
        SELECT ML.GENERATE_EMBEDDING(
            MODEL `PROJECT_ID.enterprise_documents.legal_text_embedding_model`,
            query_text
        ) as query_vector
    ),
    similarity_scores AS (
        SELECT 
            e.doc_id,
            e.title,
            e.case_name,
            e.court,
            e.jurisdiction,
            SUBSTR(e.content, 1, 200) as content_preview,
            -- Native ML.DISTANCE with COSINE similarity
            (1 - ML.DISTANCE(q.query_vector, e.content_embedding, 'COSINE')) as content_similarity,
            (1 - ML.DISTANCE(q.query_vector, e.title_embedding, 'COSINE')) as title_similarity,
            -- Legal authority weighting system
            CASE 
                WHEN LOWER(e.court) LIKE '%supreme%' THEN 2.0
                WHEN LOWER(e.court) LIKE '%appeals%' OR LOWER(e.court) LIKE '%circuit%' THEN 1.5
                WHEN LOWER(e.court) LIKE '%district%' THEN 1.0
                ELSE 0.5
            END as authority_weight
        FROM `PROJECT_ID.enterprise_documents.legal_document_embeddings` e
        CROSS JOIN query_embedding q
    ),
    ranked_results AS (
        SELECT 
            doc_id,
            title,
            case_name,
            court,
            content_preview,
            -- Hybrid similarity: content + title + authority
            (content_similarity * 0.7 + title_similarity * 0.2 + authority_weight * 0.1) as final_similarity
        FROM similarity_scores
        WHERE content_similarity > 0.1
        ORDER BY final_similarity DESC
        LIMIT top_k
    )
    SELECT ARRAY_AGG(
        STRUCT(
            doc_id,
            title,
            case_name,
            court,
            final_similarity as similarity_score,
            content_preview
        )
    )
    FROM ranked_results
);
```

## Usage Examples

### Basic Legal Search Query
```sql
-- Search for data privacy legal precedents
SELECT search_result.*
FROM UNNEST(`PROJECT_ID.enterprise_documents.native_legal_vector_search`(
    'data privacy rights in digital communications', 
    5
)) as search_result
ORDER BY search_result.similarity_score DESC;
```

### Advanced Legal Intelligence Query
```sql
-- Legal search with AI-generated analysis
WITH legal_search AS (
    SELECT search_result.*
    FROM UNNEST(`PROJECT_ID.enterprise_documents.native_legal_vector_search`(
        'intellectual property patent enforcement', 
        3
    )) as search_result
)
SELECT 
    ls.*,
    -- AI-generated legal analysis
    ML.GENERATE_TEXT(
        MODEL `PROJECT_ID.enterprise_documents.legal_analysis_model`,
        CONCAT(
            'Analyze this legal document for key holdings and precedent value: ',
            ls.title, ' - ', ls.content_preview
        )
    ) as ai_legal_analysis
FROM legal_search ls;
```

## Performance Optimization

### Vector Index Creation (Optional)
```sql
-- Create vector index for faster similarity search
CREATE VECTOR INDEX legal_content_index
ON `PROJECT_ID.enterprise_documents.legal_document_embeddings`(content_embedding)
OPTIONS(
    index_type='IVF',
    distance_type='COSINE'
);
```

### Query Performance Monitoring
```sql
-- Monitor query performance and costs
SELECT 
    job_id,
    query,
    total_bytes_processed,
    total_slot_ms,
    creation_time
FROM `PROJECT_ID.enterprise_documents.INFORMATION_SCHEMA.JOBS`
WHERE query LIKE '%native_legal_vector_search%'
ORDER BY creation_time DESC
LIMIT 10;
```

## Cost Optimization

### Estimated Costs per Query
- **ML.GENERATE_EMBEDDING**: ~$0.0001 per query embedding
- **ML.DISTANCE calculation**: ~$0.0002 per document comparison
- **Data scanning**: ~$0.005 per GB scanned
- **Total per query**: ~$0.001-$0.005 depending on corpus size

### Cost Control Strategies
1. **Limit result sets** with appropriate TOP_K values
2. **Filter by date ranges** for recent legal precedents
3. **Use materialized views** for frequently accessed embeddings
4. **Implement query caching** for repeated legal searches

## Security Configuration

### Row-Level Security for Legal Documents
```sql
-- Create row-level security policy for confidential legal documents
CREATE ROW ACCESS POLICY legal_document_access_policy
ON `PROJECT_ID.enterprise_documents.legal_documents`
GRANT TO ('user:legal-team@company.com')
FILTER USING (
    legal_category != 'CONFIDENTIAL' OR 
    SESSION_USER() IN ('legal-admin@company.com')
);
```

### Column-Level Security
```sql
-- Mask sensitive legal content for unauthorized users
CREATE OR REPLACE VIEW `PROJECT_ID.enterprise_documents.legal_documents_secure` AS
SELECT 
    doc_id,
    title,
    CASE 
        WHEN SESSION_USER() IN ('legal-team@company.com') THEN content
        ELSE 'REDACTED - INSUFFICIENT PERMISSIONS'
    END as content,
    court,
    case_name,
    jurisdiction
FROM `PROJECT_ID.enterprise_documents.legal_documents`;
```

## Monitoring & Logging

### Performance Metrics
```sql
-- Track legal search performance metrics
CREATE OR REPLACE VIEW `PROJECT_ID.enterprise_documents.search_metrics` AS
SELECT 
    DATE(creation_time) as search_date,
    COUNT(*) as total_searches,
    AVG(total_slot_ms) as avg_query_time_ms,
    AVG(total_bytes_processed) as avg_bytes_processed,
    SUM(total_bytes_billed) as total_bytes_billed
FROM `PROJECT_ID.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE query LIKE '%native_legal_vector_search%'
GROUP BY DATE(creation_time)
ORDER BY search_date DESC;
```

### Error Monitoring
```sql
-- Monitor BigQuery AI function errors
SELECT 
    job_id,
    error_result.reason as error_reason,
    error_result.message as error_message,
    creation_time
FROM `PROJECT_ID.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE error_result IS NOT NULL
    AND query LIKE '%ML.GENERATE_EMBEDDING%'
ORDER BY creation_time DESC
LIMIT 20;
```

## Troubleshooting

### Common Issues & Solutions

**Issue**: ML.GENERATE_EMBEDDING function not found
```sql
-- Solution: Verify BigQuery AI API is enabled
SELECT 1; -- Test basic BigQuery connectivity first
-- Then verify model exists:
SELECT * FROM `PROJECT_ID.enterprise_documents.INFORMATION_SCHEMA.MODELS`;
```

**Issue**: Vector search returns no results
```sql
-- Solution: Check embedding generation status
SELECT 
    COUNT(*) as total_docs,
    COUNT(content_embedding) as embedded_docs,
    COUNT(content_embedding) / COUNT(*) * 100 as embedding_coverage_pct
FROM `PROJECT_ID.enterprise_documents.legal_document_embeddings`;
```

**Issue**: Slow query performance
```sql
-- Solution: Analyze query execution plan
EXPLAIN 
SELECT search_result.*
FROM UNNEST(`PROJECT_ID.enterprise_documents.native_legal_vector_search`(
    'test query', 5
)) as search_result;
```

**Issue**: High BigQuery costs
```sql
-- Solution: Monitor and optimize query costs
SELECT 
    query,
    total_bytes_billed,
    total_bytes_billed * 5.0 / POW(10, 12) as estimated_cost_usd
FROM `PROJECT_ID.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
ORDER BY total_bytes_billed DESC
LIMIT 10;
```

## Production Deployment

### Automated Legal Document Ingestion
```sql
-- Scheduled query for daily legal document updates
CREATE OR REPLACE PROCEDURE `PROJECT_ID.enterprise_documents.update_legal_corpus`()
BEGIN
    -- Insert new legal documents
    INSERT INTO `PROJECT_ID.enterprise_documents.legal_documents`
    SELECT * FROM `PROJECT_ID.enterprise_documents.staging_legal_documents`
    WHERE NOT EXISTS (
        SELECT 1 FROM `PROJECT_ID.enterprise_documents.legal_documents` ld
        WHERE ld.doc_id = staging_legal_documents.doc_id
    );
    
    -- Generate embeddings for new documents
    INSERT INTO `PROJECT_ID.enterprise_documents.legal_document_embeddings`
    SELECT 
        doc_id,
        title,
        content,
        court,
        case_name,
        jurisdiction,
        word_count,
        ML.GENERATE_EMBEDDING(
            MODEL `PROJECT_ID.enterprise_documents.legal_text_embedding_model`,
            content
        ) as content_embedding,
        ML.GENERATE_EMBEDDING(
            MODEL `PROJECT_ID.enterprise_documents.legal_text_embedding_model`, 
            CONCAT(title, ' ', case_name)
        ) as title_embedding,
        CURRENT_TIMESTAMP() as processed_timestamp
    FROM `PROJECT_ID.enterprise_documents.legal_documents`
    WHERE doc_id NOT IN (
        SELECT doc_id FROM `PROJECT_ID.enterprise_documents.legal_document_embeddings`
    );
END;
```

### Health Check Queries
```sql
-- System health monitoring
SELECT 
    'Legal Documents' as component,
    COUNT(*) as count,
    MAX(creation_date) as latest_document
FROM `PROJECT_ID.enterprise_documents.legal_documents`
UNION ALL
SELECT 
    'Document Embeddings' as component,
    COUNT(*) as count,
    MAX(processed_timestamp) as latest_embedding
FROM `PROJECT_ID.enterprise_documents.legal_document_embeddings`
UNION ALL
SELECT 
    'Models' as component,
    COUNT(*) as count,
    MAX(creation_time) as latest_model
FROM `PROJECT_ID.enterprise_documents.INFORMATION_SCHEMA.MODELS`;
```

## Support & Maintenance

### Regular Maintenance Tasks
1. **Weekly**: Monitor query performance and costs
2. **Monthly**: Update legal document corpus with new cases
3. **Quarterly**: Retrain embedding models with domain-specific legal data
4. **Annually**: Review and optimize BigQuery AI model performance

### Support Contact
For technical support and implementation assistance:
- **Technical Documentation**: See attached project documentation
- **BigQuery AI Support**: Google Cloud Support Console  
- **Legal Domain Expertise**: Contact project development team

---

**Production-ready BigQuery AI Legal Platform with comprehensive setup, monitoring, and maintenance procedures.**
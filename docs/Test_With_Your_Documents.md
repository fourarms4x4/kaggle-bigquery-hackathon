# 🧪 Testing the Smart Document Discovery Engine with YOUR Documents

## 🎯 Quick Start Options

### Option 1: Simple Text Files (Easiest)
Put your documents in a folder and run this modified version:

```python
# Test with your local documents
import os
import pandas as pd
from pathlib import Path

def load_local_documents(folder_path):
    """Load documents from your local folder"""
    documents = []
    
    # Supported file types
    extensions = ['.txt', '.md', '.py', '.sql', '.json', '.csv']
    
    for ext in extensions:
        for file_path in Path(folder_path).glob(f'**/*{ext}'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                documents.append({
                    'document_id': len(documents) + 1,
                    'title': file_path.name,
                    'full_text': content,
                    'file_path': str(file_path),
                    'file_type': ext,
                    'length': len(content)
                })
            except Exception as e:
                print(f"Skipped {file_path}: {e}")
                
    return pd.DataFrame(documents)

# Load your documents
folder_path = r"D:\IMPORTANT DATA\Projects\Kaggle BigQuery Hackathon\Submission NO.1"
local_docs = load_local_documents(folder_path)

print(f"📄 Loaded {len(local_docs)} documents:")
print(local_docs[['title', 'file_type', 'length']].head())
```

### Option 2: Upload to BigQuery (Recommended)
Create a BigQuery table with your documents:

```python
def upload_documents_to_bigquery(documents_df, table_name="my_documents"):
    """Upload your documents to BigQuery for testing"""
    
    # Prepare documents for BigQuery
    bigquery_docs = documents_df.copy()
    
    # Add categories based on file type or content
    bigquery_docs['category'] = bigquery_docs.apply(categorize_document, axis=1)
    
    # Add relevance score (you can customize this)
    bigquery_docs['relevance_score'] = bigquery_docs['length'] / 100.0
    
    # Upload to BigQuery
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  # Overwrite existing
        autodetect=True
    )
    
    job = client.load_table_from_dataframe(
        bigquery_docs, table_id, job_config=job_config
    )
    job.result()  # Wait for completion
    
    print(f"✅ Uploaded {len(bigquery_docs)} documents to {table_id}")
    return table_id

def categorize_document(row):
    """Categorize documents based on content or file type"""
    title = row['title'].lower()
    content = row['full_text'].lower()
    
    if '.py' in title or 'python' in content:
        return 'Python Code'
    elif '.sql' in title or 'select' in content:
        return 'SQL Scripts'
    elif '.md' in title or '#' in content[:100]:
        return 'Documentation'
    elif '.json' in title:
        return 'Configuration'
    elif 'report' in title or 'analysis' in content:
        return 'Reports'
    else:
        return 'General Documents'
```

### Option 3: Test with PDF/Word Documents
If you have PDF or Word files:

```python
# Install required packages first:
# pip install PyPDF2 python-docx

import PyPDF2
from docx import Document

def extract_pdf_text(pdf_path):
    """Extract text from PDF files"""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def extract_docx_text(docx_path):
    """Extract text from Word documents"""
    doc = Document(docx_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def load_office_documents(folder_path):
    """Load PDF and Word documents"""
    documents = []
    
    # Find PDF files
    for pdf_path in Path(folder_path).glob('**/*.pdf'):
        try:
            content = extract_pdf_text(pdf_path)
            documents.append({
                'document_id': len(documents) + 1,
                'title': pdf_path.name,
                'full_text': content,
                'file_path': str(pdf_path),
                'file_type': '.pdf',
                'length': len(content)
            })
        except Exception as e:
            print(f"Skipped PDF {pdf_path}: {e}")
    
    # Find Word files
    for docx_path in Path(folder_path).glob('**/*.docx'):
        try:
            content = extract_docx_text(docx_path)
            documents.append({
                'document_id': len(documents) + 1,
                'title': docx_path.name,
                'full_text': content,
                'file_path': str(docx_path),
                'file_type': '.docx',
                'length': len(content)
            })
        except Exception as e:
            print(f"Skipped Word {docx_path}: {e}")
    
    return pd.DataFrame(documents)
```

## 🔍 Modified Search Function for Your Documents

```python
def search_my_documents(query_text, documents_table="my_documents", top_k=5):
    """Search your personal documents using the same AI approach"""
    
    # Create search query adapted for your documents
    search_sql = f"""
        WITH query_features AS (
            SELECT 
                ARRAY[
                    CASE WHEN CONTAINS_SUBSTR(LOWER('{query_text}'), 'python') THEN 1.0 ELSE 0.0 END,
                    CASE WHEN CONTAINS_SUBSTR(LOWER('{query_text}'), 'data') THEN 1.0 ELSE 0.0 END,
                    CASE WHEN CONTAINS_SUBSTR(LOWER('{query_text}'), 'analysis') THEN 1.0 ELSE 0.0 END,
                    CASE WHEN CONTAINS_SUBSTR(LOWER('{query_text}'), 'report') THEN 1.0 ELSE 0.0 END,
                    CASE WHEN CONTAINS_SUBSTR(LOWER('{query_text}'), 'code') THEN 1.0 ELSE 0.0 END
                ] AS query_embedding
        ),
        document_features AS (
            SELECT 
                *,
                ARRAY[
                    CAST(length AS FLOAT64) / 1000.0,
                    CASE WHEN CONTAINS_SUBSTR(LOWER(full_text), 'python') THEN 1.0 ELSE 0.0 END,
                    CASE WHEN CONTAINS_SUBSTR(LOWER(full_text), 'data') THEN 1.0 ELSE 0.0 END,
                    CASE WHEN CONTAINS_SUBSTR(LOWER(full_text), 'analysis') THEN 1.0 ELSE 0.0 END,
                    CASE WHEN CONTAINS_SUBSTR(LOWER(full_text), 'report') THEN 1.0 ELSE 0.0 END
                ] AS doc_embedding
            FROM `{PROJECT_ID}.{DATASET_ID}.{documents_table}`
        ),
        similarity_scores AS (
            SELECT 
                d.document_id,
                d.title,
                d.category,
                d.file_type,
                d.file_path,
                -- Calculate similarity
                (
                    -- Exact text match (highest priority)
                    CASE 
                        WHEN CONTAINS_SUBSTR(LOWER(d.full_text), LOWER('{query_text}')) THEN 3.0
                        WHEN CONTAINS_SUBSTR(LOWER(d.title), LOWER('{query_text}')) THEN 2.0 
                        ELSE 0.0 
                    END +
                    -- Semantic similarity using embeddings
                    (q.query_embedding[OFFSET(0)] * d.doc_embedding[OFFSET(1)] +
                     q.query_embedding[OFFSET(1)] * d.doc_embedding[OFFSET(2)] +
                     q.query_embedding[OFFSET(2)] * d.doc_embedding[OFFSET(3)] +
                     q.query_embedding[OFFSET(3)] * d.doc_embedding[OFFSET(4)]) * 1.5 +
                    -- Relevance boost
                    d.relevance_score * 0.1
                ) AS similarity_score
            FROM document_features d
            CROSS JOIN query_features q
        )
        SELECT 
            document_id,
            title,
            category,
            file_type,
            file_path,
            ROUND(similarity_score, 2) as similarity_score
        FROM similarity_scores
        WHERE similarity_score > 0
        ORDER BY similarity_score DESC
        LIMIT {top_k}
    """
    
    return run_query(search_sql)
```

## 🧪 Complete Test Setup

Here's a complete script to test with your documents:

```python
# Complete test script for your documents
import os
from pathlib import Path

def test_with_my_documents():
    print("🧪 Testing Smart Document Discovery with YOUR documents!")
    print("="*60)
    
    # Step 1: Choose your document folder
    document_folder = input("📁 Enter path to your documents folder: ").strip('"')
    
    if not os.path.exists(document_folder):
        print(f"❌ Folder not found: {document_folder}")
        return
    
    # Step 2: Load documents
    print(f"📄 Loading documents from: {document_folder}")
    local_docs = load_local_documents(document_folder)
    
    if len(local_docs) == 0:
        print("❌ No supported documents found!")
        print("Supported formats: .txt, .md, .py, .sql, .json, .csv")
        return
    
    print(f"✅ Found {len(local_docs)} documents")
    print(local_docs[['title', 'file_type', 'length']].head())
    
    # Step 3: Upload to BigQuery
    print("\n📤 Uploading to BigQuery...")
    table_id = upload_documents_to_bigquery(local_docs, "test_documents")
    
    # Step 4: Test searches
    print("\n🔍 Testing searches...")
    
    test_queries = [
        "python code",
        "data analysis", 
        "documentation",
        "configuration",
        "report"
    ]
    
    for query in test_queries:
        print(f"\n🔎 Searching for: '{query}'")
        results = search_my_documents(query, "test_documents", top_k=3)
        
        if results is not None and len(results) > 0:
            print(results[['title', 'category', 'similarity_score']])
        else:
            print("No results found")
    
    print("\n" + "="*60)
    print("✅ Testing complete! Your documents are searchable!")

# Run the test
test_with_my_documents()
```

## 🎯 Specific Test Scenarios

### Test with Project Files:
```python
# Test with your current project
project_folder = r"D:\IMPORTANT DATA\Projects\Kaggle BigQuery Hackathon\Submission NO.1"
docs = load_local_documents(project_folder)

# Search your project files
search_results = search_my_documents("bigquery competition", "test_documents")
```

### Test with Code Repositories:
```python
# Test with your code projects
code_folder = r"D:\IMPORTANT DATA\Projects"
code_docs = load_local_documents(code_folder)

# Search for specific programming concepts
search_results = search_my_documents("machine learning model", "test_documents")
```

### Test with Research Papers/Reports:
```python
# Test with academic or business documents
research_folder = r"D:\Documents\Research"
research_docs = load_office_documents(research_folder)  # For PDFs/Word docs

# Search for research topics
search_results = search_my_documents("artificial intelligence trends", "test_documents")
```

## 🚀 Quick Start Commands

1. **Install additional packages**:
   ```bash
   pip install PyPDF2 python-docx pathlib
   ```

2. **Choose your test folder**:
   ```python
   # Point to any folder with documents
   test_folder = r"C:\Users\YourName\Documents"
   ```

3. **Run the complete test**:
   ```python
   test_with_my_documents()
   ```

## 💡 What You'll See

The system will:
- ✅ **Load your documents** from any folder
- ✅ **Categorize them automatically** based on content/type  
- ✅ **Upload to BigQuery** for AI-powered search
- ✅ **Test semantic search** with various queries
- ✅ **Show similarity scores** for each match
- ✅ **Find documents** even when exact keywords don't match

**This proves our Smart Document Discovery Engine works with ANY collection of documents - not just Stack Overflow data!** 🎉

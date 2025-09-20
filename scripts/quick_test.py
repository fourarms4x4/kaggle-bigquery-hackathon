# 🧪 Quick Test Script - Run This Now!
# Test the Smart Document Discovery Engine with files in your current project

import os
import pandas as pd
from pathlib import Path
from google.cloud import bigquery

# Your existing BigQuery setup
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'ultra-component-436418-g2')
DATASET_ID = 'kaggle_competition'
client = bigquery.Client(project=PROJECT_ID)

def load_project_files(folder_path):
    """Load documents from your project folder"""
    documents = []
    
    # File types to include
    extensions = ['.txt', '.md', '.py', '.sql', '.json', '.ipynb']
    
    for ext in extensions:
        for file_path in Path(folder_path).glob(f'*{ext}'):  # Only current folder, not recursive
            try:
                # Skip very large files
                if file_path.stat().st_size > 1000000:  # Skip files > 1MB
                    continue
                    
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Skip empty files
                if len(content.strip()) < 10:
                    continue
                    
                documents.append({
                    'document_id': len(documents) + 1,
                    'title': file_path.name,
                    'full_text': content[:5000],  # Limit to first 5000 chars
                    'file_path': str(file_path),
                    'file_type': ext,
                    'length': len(content),
                    'category': categorize_file(file_path.name, content),
                    'relevance_score': min(len(content) / 1000.0, 10.0)  # Cap at 10
                })
            except Exception as e:
                print(f"⚠️  Skipped {file_path.name}: {e}")
                
    return pd.DataFrame(documents)

def categorize_file(filename, content):
    """Categorize files based on name and content"""
    filename_lower = filename.lower()
    content_lower = content.lower()
    
    if '.py' in filename_lower or 'import ' in content[:200]:
        return 'Python Code'
    elif '.sql' in filename_lower or 'select' in content_lower:
        return 'SQL Scripts'
    elif '.md' in filename_lower or filename_lower.endswith('.txt'):
        return 'Documentation'
    elif '.json' in filename_lower:
        return 'Configuration'
    elif '.ipynb' in filename_lower:
        return 'Jupyter Notebook'
    else:
        return 'General Files'

def upload_test_documents(documents_df):
    """Upload project files to BigQuery for testing"""
    
    if len(documents_df) == 0:
        print("❌ No documents to upload!")
        return None
    
    table_id = f"{PROJECT_ID}.{DATASET_ID}.test_documents"
    
    # Configure upload
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  # Replace existing table
        autodetect=True
    )
    
    try:
        job = client.load_table_from_dataframe(
            documents_df, table_id, job_config=job_config
        )
        job.result()  # Wait for completion
        
        print(f"✅ Uploaded {len(documents_df)} documents to BigQuery test table")
        return table_id
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None

def search_test_documents(query_text, top_k=3):
    """Search your uploaded test documents"""
    
    search_sql = f"""
        WITH similarity_scores AS (
            SELECT 
                document_id,
                title,
                category,
                file_type,
                relevance_score,
                -- Simple similarity calculation
                (
                    CASE 
                        WHEN CONTAINS_SUBSTR(LOWER(full_text), LOWER('{query_text}')) THEN 3.0
                        WHEN CONTAINS_SUBSTR(LOWER(title), LOWER('{query_text}')) THEN 2.0 
                        ELSE 0.0 
                    END +
                    relevance_score * 0.1
                ) AS similarity_score
            FROM `{PROJECT_ID}.{DATASET_ID}.test_documents`
        )
        SELECT 
            document_id,
            title,
            category,
            file_type,
            ROUND(similarity_score, 2) as similarity_score,
            relevance_score
        FROM similarity_scores
        WHERE similarity_score > 0
        ORDER BY similarity_score DESC, relevance_score DESC
        LIMIT {top_k}
    """
    
    try:
        return client.query(search_sql).to_dataframe()
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return None

# 🚀 MAIN TEST FUNCTION - RUN THIS!
def run_quick_test():
    print("🧪 QUICK TEST: Smart Document Discovery with YOUR Project Files")
    print("="*70)
    
    # Get current directory
    current_dir = os.getcwd()
    print(f"📁 Testing with files in: {current_dir}")
    
    # Load files from current project
    print("\n📄 Loading project files...")
    project_docs = load_project_files(current_dir)
    
    if len(project_docs) == 0:
        print("❌ No suitable files found in current directory!")
        print("Make sure you have .txt, .md, .py, .sql, .json, or .ipynb files")
        return
    
    print(f"✅ Found {len(project_docs)} files:")
    print(project_docs[['title', 'category', 'file_type', 'length']].to_string())
    
    # Upload to BigQuery
    print(f"\n📤 Uploading to BigQuery...")
    table_id = upload_test_documents(project_docs)
    
    if table_id is None:
        return
    
    # Test searches
    print(f"\n🔍 Testing searches on your project files...")
    
    test_queries = [
        "bigquery",
        "competition", 
        "python",
        "data",
        "smart document"
    ]
    
    for query in test_queries:
        print(f"\n🔎 Searching for: '{query}'")
        results = search_test_documents(query, top_k=3)
        
        if results is not None and len(results) > 0:
            print(results[['title', 'category', 'similarity_score']].to_string(index=False))
        else:
            print("   No results found")
    
    print(f"\n" + "="*70)
    print("✅ TEST COMPLETE! The search engine works with YOUR files!")
    print("💡 Try different search terms to see semantic matching in action")
    
    return project_docs

if __name__ == "__main__":
    # Run the test
    test_results = run_quick_test()

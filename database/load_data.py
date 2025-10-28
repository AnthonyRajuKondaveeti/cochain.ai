#database/load_data.py
'''
Load your csv and PKL into supabase
'''
import pandas as pd
import pickle
from connection import supabase

def load_github_data():
    df = pd.read_csv('data/student_ideas_transformed.csv')
    
    print(f"Loading {len(df)} repositories ...")
    
    # More robust duplicate checking - get ALL existing titles
    print("🔍 Checking for existing records...")
    existing_titles = set()
    page_size = 1000
    offset = 0
    
    while True:
        try:
            result = supabase.table('github_references').select('title').range(offset, offset + page_size - 1).execute()
            if not result.data or len(result.data) == 0:
                break
            
            batch_titles = {repo['title'].strip() for repo in result.data if repo.get('title')}
            existing_titles.update(batch_titles)
            
            print(f"  Fetched {len(existing_titles)} unique titles so far...")
            offset += page_size
            
            # If we got less than page_size, we've reached the end
            if len(result.data) < page_size:
                break
                
        except Exception as e:
            print(f"Error fetching existing titles: {e}")
            break
    
    print(f"Found {len(existing_titles)} existing repositories in database")
    
    # Track statistics
    inserted_count = 0
    skipped_count = 0

    for idx, row in df.iterrows():
        title = str(row['title']).strip() if pd.notna(row['title']) else ""
        
        # Skip if title is empty or already exists
        if not title or title in existing_titles:
            skipped_count += 1
            if idx % 500 == 0:
                print(f"  Progress: {idx}/{len(df)} - Skipped: {skipped_count}, Inserted: {inserted_count}")
            continue
            
        try:
            data = {
                'title': title,
                'description': str(row['description']) if pd.notna(row['description']) else "",
                'domain': str(row['domain']) if pd.notna(row['domain']) else "",
                'required_skills': str(row['required_skills']) if pd.notna(row['required_skills']) else "",
                'complexity_level': str(row['complexity_level']) if pd.notna(row['complexity_level']) else "",
                'team_size': int(row['team_size']) if pd.notna(row['team_size']) else 1,
                'estimated_timeline': str(row['estimated_timeline']) if pd.notna(row['estimated_timeline']) else "",
                'repository_url': str(row['repository_url']) if pd.notna(row['repository_url']) else "",
                'original_stars': int(row.get('original_stars', 0)) if pd.notna(row.get('original_stars', 0)) else 0,
                'original_forks': int(row.get('original_forks', 0)) if pd.notna(row.get('original_forks', 0)) else 0,
                'technologies': str(row['technologies']) if pd.notna(row['technologies']) else "",
                'source': str(row['source']) if pd.notna(row['source']) else ""
            }

            result = supabase.table('github_references').insert(data).execute()
            existing_titles.add(title)  # Add to set to prevent duplicates in current run
            inserted_count += 1

            if inserted_count % 100 == 0:
                print(f"  Inserted {inserted_count} new repositories (skipped {skipped_count} duplicates)...")
                
        except Exception as e:
            print(f"Error inserting record {idx}: {e}")
            skipped_count += 1

    print(f"✅ Finished loading repositories: {inserted_count} inserted, {skipped_count} skipped")

def load_embeddings():
    with open('data/idea_embeddings.pkl', 'rb') as f:
        data = pickle.load(f)

    embeddings = data['embeddings']
    ideas = data['ideas']

    print(f"Loading {len(embeddings)} embeddings ...")
    print(f"Number of ideas: {len(ideas) if hasattr(ideas, '__len__') else 'Unknown'}")
    
    # Get ALL repositories with robust pagination
    print("🔍 Fetching all repositories...")
    all_repos = []
    page_size = 1000
    offset = 0
    
    while True:
        try:
            result = supabase.table('github_references').select('id', 'title').range(offset, offset + page_size - 1).execute()
            if not result.data or len(result.data) == 0:
                break
            all_repos.extend(result.data)
            offset += page_size
            print(f"  Fetched {len(all_repos)} repositories so far...")
            if len(result.data) < page_size:
                break
        except Exception as e:
            print(f"Error fetching repositories: {e}")
            break
    
    print(f"Found {len(all_repos)} repositories in database")
    id_map = {repo['title'].strip(): repo['id'] for repo in all_repos if repo.get('title')}
    
    # Get ALL existing embeddings with robust pagination
    print("🔍 Fetching existing embeddings...")
    existing_github_ids = set()
    offset = 0
    
    while True:
        try:
            result = supabase.table('github_embeddings').select('github_id').range(offset, offset + page_size - 1).execute()
            if not result.data or len(result.data) == 0:
                break
            batch_ids = {emb['github_id'] for emb in result.data if emb.get('github_id')}
            existing_github_ids.update(batch_ids)
            offset += page_size
            print(f"  Found {len(existing_github_ids)} existing embeddings so far...")
            if len(result.data) < page_size:
                break
        except Exception as e:
            print(f"Error fetching embeddings: {e}")
            break
    
    print(f"Found {len(existing_github_ids)} existing embeddings in database")
    
    inserted_count = 0
    skipped_count = 0
    not_found_count = 0

    for idx, (embedding, idea) in enumerate(zip(embeddings, ideas['title'])):
        idea_title = str(idea).strip() if pd.notna(idea) else ""
        
        if idea_title in id_map:
            github_id = id_map[idea_title]
            
            # Skip if embedding already exists for this repository
            if github_id in existing_github_ids:
                skipped_count += 1
                continue
                
            try:
                embedding_data = {
                    'github_id': github_id,
                    'embedding': embedding.tolist()  
                }

                supabase.table('github_embeddings').insert(embedding_data).execute()
                existing_github_ids.add(github_id)  # Add to set to prevent duplicates in current run
                inserted_count += 1

                if inserted_count % 100 == 0:
                    print(f"  Inserted {inserted_count} new embeddings (skipped {skipped_count} duplicates, {not_found_count} not found)...")
                    
            except Exception as e:
                print(f"Error inserting embedding {idx}: {e}")
                skipped_count += 1
        else:
            not_found_count += 1

    print(f"✅ Finished loading embeddings: {inserted_count} inserted, {skipped_count} skipped, {not_found_count} not found")


if __name__ == "__main__":
    load_github_data()
    load_embeddings()
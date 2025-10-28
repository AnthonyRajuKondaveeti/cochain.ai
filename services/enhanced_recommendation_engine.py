# services/enhanced_recommendation_engine.py
"""
Enhanced Recommendation Engine
Uses separate tables for user inputs and embeddings
Performs similarity search against github_embeddings
Includes analytics tracking
"""
from sentence_transformers import SentenceTransformer
from database.connection import supabase
from .analytics_service import RecommendationAnalytics
import numpy as np
import uuid

class EnhancedRecommendationEngine:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        print(f"🤖 Loading recommendation model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.analytics = RecommendationAnalytics()
        self.complexity_map = {
            1: "Beginner",
            2: "Intermediate", 
            3: "Advanced"
        }
        print("✅ Enhanced recommendation engine ready!")

    def _parse_user_input(self, user_input: dict):
        """Parse and clean user input"""
        # Extract and clean text fields
        project_idea = user_input.get('project_idea', '').strip()
        objectives = self._parse_text_field(user_input.get('objectives', ''))
        achievements = self._parse_text_field(user_input.get('achievements', ''))
        existing_skills = self._parse_text_field(user_input.get('existing_skills', ''))
        want_to_learn = self._parse_text_field(user_input.get('want_to_learn', ''))
        
        # Parse complexity and recommendations count
        complexity_level = user_input.get('complexity_level', 2)
        num_recommendations = user_input.get('num_recommendations', 10)
        
        return {
            'project_idea': project_idea,
            'objectives': objectives,
            'achievements': achievements,
            'existing_skills': existing_skills,
            'want_to_learn': want_to_learn,
            'complexity_level': complexity_level,
            'num_recommendations': num_recommendations
        }
    
    def _parse_text_field(self, field_value):
        """Parse comma-separated string or return as is"""
        if isinstance(field_value, str):
            return field_value.strip()
        return str(field_value) if field_value else ""

    def _build_query_text(self, parsed_input):
        """Build comprehensive query text from user input"""
        query_parts = []
        
        # Add project idea (highest weight)
        if parsed_input['project_idea']:
            query_parts.append(parsed_input['project_idea'])
        
        # Add objectives
        if parsed_input['objectives']:
            query_parts.append(parsed_input['objectives'])
        
        # Add achievements/goals
        if parsed_input['achievements']:
            query_parts.append(parsed_input['achievements'])
        
        # Add skills they want to learn (important for matching)
        if parsed_input['want_to_learn'] and parsed_input['want_to_learn'].lower() != 'nothing':
            query_parts.append(parsed_input['want_to_learn'])
        
        # Add existing skills (lower weight)
        if parsed_input['existing_skills']:
            query_parts.append(parsed_input['existing_skills'])
        
        return " ".join(query_parts)

    def _store_user_query(self, parsed_input, query_text):
        """Store user query in database"""
        try:
            query_data = {
                'project_idea': parsed_input['project_idea'],
                'objectives': parsed_input['objectives'],
                'achievements': parsed_input['achievements'],
                'existing_skills': parsed_input['existing_skills'],
                'want_to_learn': parsed_input['want_to_learn'],
                'complexity_level': parsed_input['complexity_level'],
                'num_recommendations': parsed_input['num_recommendations'],
                'query_text': query_text
            }
            
            result = supabase.table('user_queries').insert(query_data).execute()
            return result.data[0]['id'] if result.data else None
            
        except Exception as e:
            print(f"Warning: Could not store user query: {e}")
            return None

    def _store_user_embedding(self, user_query_id, embedding):
        """Store user query embedding"""
        try:
            if user_query_id:
                embedding_data = {
                    'user_query_id': user_query_id,
                    'embedding': embedding.tolist()
                }
                supabase.table('user_query_embeddings').insert(embedding_data).execute()
        except Exception as e:
            print(f"Warning: Could not store user embedding: {e}")

    def _get_github_embeddings(self, limit=None):
        """Get all github embeddings for similarity comparison"""
        try:
            query = supabase.table('github_embeddings').select('github_id, embedding')
            if limit:
                query = query.limit(limit)
            
            all_embeddings = []
            page_size = 1000
            offset = 0
            
            while True:
                result = query.range(offset, offset + page_size - 1).execute()
                if not result.data:
                    break
                all_embeddings.extend(result.data)
                offset += page_size
                if len(result.data) < page_size:
                    break
                    
            return all_embeddings
            
        except Exception as e:
            print(f"Error fetching github embeddings: {e}")
            return []

    def _calculate_similarities(self, user_embedding, github_embeddings):
        """Calculate cosine similarities between user embedding and github embeddings"""
        similarities = []
        user_vec = np.array(user_embedding)
        
        for gh_emb in github_embeddings:
            try:
                # Handle different embedding formats
                embedding_data = gh_emb['embedding']
                
                if isinstance(embedding_data, str):
                    # Parse string representation of array
                    import json
                    try:
                        # Try parsing as JSON first
                        github_vec = np.array(json.loads(embedding_data))
                    except:
                        # If that fails, try parsing as Python literal
                        import ast
                        github_vec = np.array(ast.literal_eval(embedding_data))
                elif isinstance(embedding_data, list):
                    # Already a list, convert to numpy array
                    github_vec = np.array(embedding_data)
                else:
                    # Try direct conversion
                    github_vec = np.array(embedding_data)
                
                # Ensure both vectors are float type
                user_vec = user_vec.astype(np.float64)
                github_vec = github_vec.astype(np.float64)
                
                # Calculate cosine similarity
                dot_product = np.dot(user_vec, github_vec)
                norm_user = np.linalg.norm(user_vec)
                norm_github = np.linalg.norm(github_vec)
                
                if norm_user > 0 and norm_github > 0:
                    similarity = dot_product / (norm_user * norm_github)
                else:
                    similarity = 0
                
                similarities.append({
                    'github_id': gh_emb['github_id'],
                    'similarity': float(similarity)
                })
                
            except Exception as e:
                print(f"Error calculating similarity for {gh_emb.get('github_id', 'unknown')}: {e}")
                continue
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities

    def _get_github_references(self, github_ids):
        """Get github reference details for the given IDs"""
        try:
            # Convert UUIDs to strings for the query
            id_strings = [str(gid) for gid in github_ids]
            
            result = supabase.table('github_references').select('*').in_('id', id_strings).execute()
            return result.data
            
        except Exception as e:
            print(f"Error fetching github references: {e}")
            return []

    def _filter_by_complexity(self, recommendations, target_complexity):
        """Filter and sort recommendations by complexity level"""
        if not target_complexity or target_complexity not in [1, 2, 3]:
            return recommendations
        
        target_complexity_str = self.complexity_map[target_complexity].lower()
        
        # Add complexity matching score
        for rec in recommendations:
            rec_complexity = rec.get('complexity_level', '').lower()
            
            if target_complexity_str in rec_complexity:
                rec['complexity_match'] = 2  # Exact match
            elif not rec_complexity:
                rec['complexity_match'] = 1  # No complexity info
            elif (target_complexity == 2 and any(level in rec_complexity for level in ['beginner', 'advanced'])) or \
                 (target_complexity == 1 and 'intermediate' in rec_complexity) or \
                 (target_complexity == 3 and 'intermediate' in rec_complexity):
                rec['complexity_match'] = 1  # Adjacent level
            else:
                rec['complexity_match'] = 0  # No match
        
        # Sort by complexity match first, then by similarity
        return sorted(recommendations, key=lambda x: (x.get('complexity_match', 0), x.get('similarity', 0)), reverse=True)

    def get_recommendations(self, user_input: dict):
        """
        Main method to get recommendations
        """
        try:
            # Parse user input
            parsed_input = self._parse_user_input(user_input)
            print(f"🔍 Processing request for {parsed_input['num_recommendations']} recommendations...")
            
            # Build query text
            query_text = self._build_query_text(parsed_input)
            print(f"📝 Query: {query_text[:100]}...")
            
            if not query_text.strip():
                return {"error": "Please provide at least a project idea or objectives"}
            
            # Store user query
            user_query_id = self._store_user_query(parsed_input, query_text)
            
            # Generate embedding
            print("🔄 Generating query embedding...")
            query_embedding = self.model.encode(query_text)
            
            # Store user embedding
            self._store_user_embedding(user_query_id, query_embedding)
            
            # Get all github embeddings
            print("📊 Fetching github embeddings...")
            github_embeddings = self._get_github_embeddings()
            
            if not github_embeddings:
                return {"error": "No github embeddings found in database"}
            
            print(f"🔍 Comparing against {len(github_embeddings)} github projects...")
            
            # Calculate similarities
            similarities = self._calculate_similarities(query_embedding, github_embeddings)
            
            # Filter by minimum similarity threshold
            min_similarity = 0.1  # Adjust as needed
            filtered_similarities = [s for s in similarities if s['similarity'] >= min_similarity]
            
            if not filtered_similarities:
                return {"error": "No similar projects found. Try adjusting your search criteria."}
            
            # Get top matches
            top_similarities = filtered_similarities[:parsed_input['num_recommendations'] * 2]  # Get more to filter
            github_ids = [s['github_id'] for s in top_similarities]
            
            # Get github reference details
            print("📋 Fetching project details...")
            github_references = self._get_github_references(github_ids)
            
            # Combine similarities with reference data
            recommendations = []
            similarity_map = {s['github_id']: s['similarity'] for s in top_similarities}
            
            for ref in github_references:
                ref_id = ref['id']
                if ref_id in similarity_map:
                    ref['similarity'] = similarity_map[ref_id]
                    recommendations.append(ref)
            
            # Sort by similarity
            recommendations.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            
            # Filter by complexity if specified
            if parsed_input['complexity_level']:
                recommendations = self._filter_by_complexity(recommendations, parsed_input['complexity_level'])
            
            # Limit to requested number
            final_recommendations = recommendations[:parsed_input['num_recommendations']]
            
            # Add user context to results
            for rec in final_recommendations:
                rec['user_context'] = {
                    'requested_complexity': self.complexity_map.get(parsed_input['complexity_level'], 'Any'),
                    'user_skills': parsed_input['existing_skills'],
                    'learning_goals': parsed_input['want_to_learn'],
                    'query_id': str(user_query_id) if user_query_id else None
                }
            
            # Track recommendation results for analytics
            if user_query_id:
                self.analytics.track_recommendation_results(user_query_id, final_recommendations)
            
            print(f"✅ Returning {len(final_recommendations)} personalized recommendations")
            return final_recommendations
            
        except Exception as e:
            print(f"❌ Error in recommendation engine: {e}")
            return {"error": f"Recommendation failed: {str(e)}"}

    def get_user_query_history(self, limit=10):
        """Get recent user queries for analytics"""
        try:
            result = supabase.table('user_queries').select('*').order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"Error fetching user history: {e}")
            return []

    def track_user_click(self, user_query_id, github_reference_id, rank_position, 
                        similarity_score, session_id=None, user_agent=None):
        """Track when user clicks on a recommendation"""
        return self.analytics.track_user_interaction(
            user_query_id=user_query_id,
            github_reference_id=github_reference_id,
            interaction_type='click',
            rank_position=rank_position,
            similarity_score=similarity_score,
            session_id=session_id,
            user_agent=user_agent
        )

    def track_user_feedback(self, user_query_id, github_reference_id, rating=None, 
                          feedback_text=None, is_relevant=None, is_helpful=None):
        """Track explicit user feedback"""
        return self.analytics.track_user_feedback(
            user_query_id=user_query_id,
            github_reference_id=github_reference_id,
            rating=rating,
            feedback_text=feedback_text,
            is_relevant=is_relevant,
            is_helpful=is_helpful
        )

    def get_analytics(self, days=30):
        """Get recommendation analytics"""
        return self.analytics.get_analytics_summary(days)
# services/personalized_recommendations.py
"""
Personalized Recommendation Service
Generates recommendations based on user profile and interests
"""
from sentence_transformers import SentenceTransformer
from database.connection import supabase
import numpy as np
import logging
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class PersonalizedRecommendationService:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.complexity_map = {
            'beginner': 1,
            'intermediate': 2,
            'advanced': 3,
            'expert': 3
        }
    
    def build_profile_query(self, profile):
        """Build query text from user profile"""
        query_parts = []
        
        # Add areas of interest
        if profile.get('areas_of_interest'):
            interests = profile['areas_of_interest']
            if isinstance(interests, list):
                query_parts.append(' '.join([interest.replace('_', ' ') for interest in interests]))
        
        # Add programming languages
        if profile.get('programming_languages'):
            langs = profile['programming_languages']
            if isinstance(langs, list):
                query_parts.append(' '.join(langs))
        
        # Add frameworks
        if profile.get('frameworks_known'):
            frameworks = profile['frameworks_known']
            if isinstance(frameworks, list):
                query_parts.append(' '.join(frameworks))
        
        # Add learning goals
        if profile.get('learning_goals'):
            query_parts.append(profile['learning_goals'])
        
        # Add field of study
        if profile.get('field_of_study'):
            query_parts.append(profile['field_of_study'])
        
        return ' '.join(query_parts)
    
    def _generate_profile_hash(self, profile):
        """Generate hash of user profile to detect changes"""
        # Create a normalized representation of the profile for hashing
        profile_for_hash = {
            'areas_of_interest': sorted(profile.get('areas_of_interest', [])) if profile.get('areas_of_interest') else [],
            'programming_languages': sorted(profile.get('programming_languages', [])) if profile.get('programming_languages') else [],
            'frameworks_known': sorted(profile.get('frameworks_known', [])) if profile.get('frameworks_known') else [],
            'learning_goals': profile.get('learning_goals', ''),
            'field_of_study': profile.get('field_of_study', ''),
            'overall_skill_level': profile.get('overall_skill_level', 'intermediate')
        }
        
        profile_str = json.dumps(profile_for_hash, sort_keys=True)
        return hashlib.md5(profile_str.encode()).hexdigest()
    
    def _get_cached_recommendations(self, user_id, profile_hash):
        """Get cached recommendations if available and profile hasn't changed"""
        try:
            result = supabase.table('user_cached_recommendations').select('*').eq('user_id', user_id).execute()
            
            if result.data and len(result.data) > 0:
                cached = result.data[0]
                
                # Check if profile hash matches (no changes)
                if cached.get('profile_hash') == profile_hash:
                    logger.info(f"Using cached recommendations for user {user_id}")
                    return cached.get('recommendations', [])
                else:
                    logger.info(f"Profile changed for user {user_id}, cache invalidated")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached recommendations for user {user_id}: {str(e)}")
            return None
    
    def _save_cached_recommendations(self, user_id, recommendations, profile_hash):
        """Save recommendations to cache"""
        try:
            cache_data = {
                'user_id': user_id,
                'recommendations': recommendations,
                'profile_hash': profile_hash,
                'updated_at': datetime.now().isoformat()
            }
            
            # Use upsert to handle both insert and update
            result = supabase.table('user_cached_recommendations').upsert(
                cache_data,
                on_conflict='user_id'
            ).execute()
            
            if result.data:
                logger.info(f"Cached {len(recommendations)} recommendations for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving cached recommendations for user {user_id}: {str(e)}")
    
    def invalidate_user_cache(self, user_id):
        """Invalidate cached recommendations for a user (call when profile is updated)"""
        try:
            result = supabase.table('user_cached_recommendations').delete().eq('user_id', user_id).execute()
            logger.info(f"Invalidated recommendation cache for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {str(e)}")
            return False
    
    def get_recommendations_for_user(self, user_id, num_recommendations=10, offset=0):
        """Get personalized recommendations based on user profile with caching"""
        try:
            # Get user profile (try user_profiles first, then users table)
            profile_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
            
            if not profile_result.data:
                # Fallback to users table for basic info
                user_result = supabase.table('users').select('*').eq('id', user_id).execute()
                if user_result.data:
                    logger.warning(f"User profile not found for {user_id}, using fallback")
                    profile = {
                        'areas_of_interest': ['web_development', 'machine_learning'],
                        'programming_languages': ['Python', 'JavaScript'],
                        'overall_skill_level': 'intermediate'
                    }
                else:
                    # User doesn't exist in either table - use default profile
                    logger.warning(f"User {user_id} not found in any table, using default profile")
                    profile = {
                        'areas_of_interest': ['web_development', 'machine_learning', 'data_science'],
                        'programming_languages': ['Python', 'JavaScript', 'Java'],
                        'overall_skill_level': 'intermediate',
                        'frameworks_known': ['React', 'Django', 'Flask'],
                        'learning_goals': 'Build interesting projects and learn new technologies'
                    }
            else:
                profile = profile_result.data[0]
                logger.info(f"Found user profile with interests: {profile.get('areas_of_interest', [])}")
            
            # Generate profile hash to check for changes
            profile_hash = self._generate_profile_hash(profile)
            
            # Try to get cached recommendations first
            cached_recommendations = self._get_cached_recommendations(user_id, profile_hash)
            
            if cached_recommendations:
                # Return cached recommendations with pagination
                total_cached = len(cached_recommendations)
                end_index = min(offset + num_recommendations, total_cached)
                paginated_recommendations = cached_recommendations[offset:end_index]
                
                logger.info(f"Returned {len(paginated_recommendations)} cached recommendations for user {user_id} (offset: {offset})")
                return {
                    'success': True,
                    'recommendations': paginated_recommendations,
                    'total_count': total_cached,
                    'cached': True
                }
            
            # No cache available, generate fresh recommendations
            logger.info(f"Generating fresh recommendations for user {user_id}")
            
            # Build query from profile
            query_text = self.build_profile_query(profile)
            
            if not query_text.strip():
                logger.warning(f"Empty profile query for user {user_id}, using fallback")
                query_text = "web development programming software"
            
            logger.info(f"Query text for user {user_id}: {query_text}")
            
            # Generate embedding
            query_embedding = self.model.encode(query_text)
            
            # Get all github embeddings
            github_embeddings = self._get_github_embeddings()
            
            if not github_embeddings:
                return {'error': 'No projects available'}
            
            # Calculate similarities
            similarities = self._calculate_similarities(query_embedding, github_embeddings)
            
            # Get complexity level
            complexity_level = self.complexity_map.get(profile.get('overall_skill_level', 'intermediate'), 2)
            
            # Get top matches (generate more than needed for better caching)
            cache_size = max(30, num_recommendations * 3)  # Cache at least 30 recommendations
            top_similarities = similarities[:cache_size]
            github_ids = [s['github_id'] for s in top_similarities]
            
            # Get github reference details
            github_references = self._get_github_references(github_ids)
            
            # Combine similarities with reference data
            recommendations = []
            similarity_map = {s['github_id']: s['similarity'] for s in top_similarities}
            
            for ref in github_references:
                ref_id = ref['id']
                if ref_id in similarity_map:
                    ref['similarity'] = similarity_map[ref_id]
                    ref['match_reason'] = self._generate_match_reason(ref, profile)
                    recommendations.append(ref)
            
            # Sort by similarity
            recommendations.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            
            # Filter by complexity
            if complexity_level:
                recommendations = self._filter_by_complexity(recommendations, complexity_level)
            
            # Cache the recommendations for future use
            self._save_cached_recommendations(user_id, recommendations, profile_hash)
            
            # Return paginated results
            total_recommendations = len(recommendations)
            end_index = min(offset + num_recommendations, total_recommendations)
            paginated_recommendations = recommendations[offset:end_index]
            
            logger.info(f"Generated and cached {total_recommendations} recommendations, returned {len(paginated_recommendations)} for user {user_id}")
            
            return {
                'success': True,
                'recommendations': paginated_recommendations,
                'total_count': total_recommendations,
                'cached': False,
                'profile_query': query_text,
                'user_level': profile.get('overall_skill_level'),
                'total_analyzed': len(github_embeddings)
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {str(e)}")
            return {'error': str(e)}
    
    def get_recommendations_by_interest(self, interest_area, skill_level='intermediate', limit=10):
        """Get recommendations for a specific interest area"""
        try:
            # Build query for interest area
            query_text = interest_area.replace('_', ' ')
            
            # Generate embedding
            query_embedding = self.model.encode(query_text)
            
            # Get all github embeddings
            github_embeddings = self._get_github_embeddings()
            
            if not github_embeddings:
                return []
            
            # Calculate similarities
            similarities = self._calculate_similarities(query_embedding, github_embeddings)
            
            # Get top matches
            top_similarities = similarities[:limit * 2]
            github_ids = [s['github_id'] for s in top_similarities]
            
            # Get github reference details
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
            
            # Filter by complexity
            complexity_level = self.complexity_map.get(skill_level, 2)
            recommendations = self._filter_by_complexity(recommendations, complexity_level)
            
            return recommendations[:limit]
            
        except Exception as e:
            print(f"Error getting interest recommendations: {e}")
            return []
    
    def _get_github_embeddings(self, limit=None):
        """Get all github embeddings"""
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
        """Calculate cosine similarities"""
        similarities = []
        user_vec = np.array(user_embedding)
        
        for gh_emb in github_embeddings:
            try:
                embedding_data = gh_emb['embedding']
                
                if isinstance(embedding_data, str):
                    import json
                    try:
                        github_vec = np.array(json.loads(embedding_data))
                    except:
                        import ast
                        github_vec = np.array(ast.literal_eval(embedding_data))
                elif isinstance(embedding_data, list):
                    github_vec = np.array(embedding_data)
                else:
                    github_vec = np.array(embedding_data)
                
                user_vec = user_vec.astype(np.float64)
                github_vec = github_vec.astype(np.float64)
                
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
                continue
        
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities
    
    def _get_github_references(self, github_ids):
        """Get github reference details"""
        try:
            id_strings = [str(gid) for gid in github_ids]
            result = supabase.table('github_references').select('*').in_('id', id_strings).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching github references: {e}")
            return []
    
    def _filter_by_complexity(self, recommendations, target_complexity):
        """Filter recommendations by complexity level"""
        complexity_map = {1: 'beginner', 2: 'intermediate', 3: 'advanced'}
        target_complexity_str = complexity_map.get(target_complexity, 'intermediate').lower()
        
        for rec in recommendations:
            rec_complexity = rec.get('complexity_level', '').lower()
            
            if target_complexity_str in rec_complexity:
                rec['complexity_match'] = 2
            elif not rec_complexity:
                rec['complexity_match'] = 1
            elif (target_complexity == 2 and any(level in rec_complexity for level in ['beginner', 'advanced'])) or \
                 (target_complexity == 1 and 'intermediate' in rec_complexity) or \
                 (target_complexity == 3 and 'intermediate' in rec_complexity):
                rec['complexity_match'] = 1
            else:
                rec['complexity_match'] = 0
        
        return sorted(recommendations, key=lambda x: (x.get('complexity_match', 0), x.get('similarity', 0)), reverse=True)
    
    def _generate_match_reason(self, project, profile):
        """Generate reason why project matches user profile"""
        reasons = []
        
        # Check interest match
        if profile.get('areas_of_interest'):
            project_domain = project.get('domain', '').lower()
            for interest in profile['areas_of_interest']:
                if interest.replace('_', ' ') in project_domain or project_domain in interest.replace('_', ' '):
                    reasons.append(f"Matches your interest in {interest.replace('_', ' ')}")
                    break
        
        # Check language match
        if profile.get('programming_languages'):
            project_skills = str(project.get('required_skills', '')).lower()
            for lang in profile['programming_languages']:
                if lang.lower() in project_skills:
                    reasons.append(f"Uses {lang} which you know")
                    break
        
        # Check level match
        project_complexity = project.get('complexity_level', '').lower()
        user_level = profile.get('overall_skill_level', '').lower()
        if user_level in project_complexity:
            reasons.append(f"Suitable for your {user_level} level")
        
        return ' • '.join(reasons) if reasons else "Good match based on your profile"
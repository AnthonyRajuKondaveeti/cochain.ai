"""
Verification Script: Check RL Recommendation System Activation
Verifies that the RL system is properly configured and functional
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_imports():
    """Check if all required modules can be imported"""
    print("=" * 60)
    print("1. CHECKING IMPORTS")
    print("=" * 60)
    
    required_modules = [
        ('services.rl_recommendation_engine', 'get_rl_engine'),
        ('services.contextual_bandit', 'get_contextual_bandit'),
        ('services.reward_calculator', 'get_reward_calculator'),
        ('services.background_tasks', 'start_background_tasks'),
        ('services.personalized_recommendations', 'PersonalizedRecommendationService'),
    ]
    
    all_good = True
    for module_name, class_name in required_modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"❌ {module_name}.{class_name}: {str(e)}")
            all_good = False
    
    return all_good

def check_rl_engine():
    """Check if RL engine can be initialized"""
    print("\n" + "=" * 60)
    print("2. CHECKING RL ENGINE INITIALIZATION")
    print("=" * 60)
    
    try:
        from services.rl_recommendation_engine import get_rl_engine
        
        rl_engine = get_rl_engine()
        print(f"✅ RL Engine initialized")
        print(f"   - Exploration rate: {rl_engine.exploration_rate}")
        print(f"   - Similarity weight: {rl_engine.similarity_weight}")
        print(f"   - Bandit weight: {rl_engine.bandit_weight}")
        
        # Check if base recommender is initialized
        if rl_engine.base_recommender:
            print(f"✅ Base recommender (similarity) initialized")
        else:
            print(f"❌ Base recommender not initialized")
            return False
        
        # Check if bandit is initialized
        if rl_engine.bandit:
            print(f"✅ Contextual bandit initialized")
        else:
            print(f"❌ Contextual bandit not initialized")
            return False
        
        # Check if reward calculator is initialized
        if rl_engine.reward_calculator:
            print(f"✅ Reward calculator initialized")
        else:
            print(f"❌ Reward calculator not initialized")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize RL engine: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_background_tasks():
    """Check if background tasks can be initialized"""
    print("\n" + "=" * 60)
    print("3. CHECKING BACKGROUND TASKS")
    print("=" * 60)
    
    try:
        from services.background_tasks import get_task_scheduler
        
        scheduler = get_task_scheduler()
        print(f"✅ Background task scheduler initialized")
        print(f"   - Scheduler state: {scheduler.scheduler.state}")
        
        # List scheduled jobs
        jobs = scheduler.scheduler.get_jobs()
        if jobs:
            print(f"✅ {len(jobs)} background jobs configured:")
            for job in jobs:
                print(f"   - {job.name} (ID: {job.id})")
        else:
            print(f"⚠️  No background jobs scheduled yet (will be added on start)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize background tasks: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_database_tables():
    """Check if required database tables exist"""
    print("\n" + "=" * 60)
    print("4. CHECKING DATABASE TABLES")
    print("=" * 60)
    
    try:
        from database.connection import supabase
        
        required_tables = [
            'user_interactions',
            'recommendation_results',
            'user_sessions',
            'github_embeddings',
            'github_references',
            'user_profiles'
        ]
        
        optional_tables = [
            'rl_training_history',
            'bandit_parameters',
            'user_feedback',
            'rl_ab_test',
            'user_ab_assignment'
        ]
        
        all_required = True
        for table in required_tables:
            try:
                result = supabase.table(table).select('*').limit(1).execute()
                print(f"✅ {table} (required)")
            except Exception as e:
                print(f"❌ {table} (required): {str(e)}")
                all_required = False
        
        for table in optional_tables:
            try:
                result = supabase.table(table).select('*').limit(1).execute()
                print(f"✅ {table} (optional)")
            except Exception as e:
                print(f"⚠️  {table} (optional): Not found or error - {str(e)[:50]}")
        
        return all_required
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def check_existing_data():
    """Check if there's interaction data for RL to learn from"""
    print("\n" + "=" * 60)
    print("5. CHECKING EXISTING INTERACTION DATA")
    print("=" * 60)
    
    try:
        from database.connection import supabase
        
        # Check interactions
        interactions = supabase.table('user_interactions').select('*', count='exact').execute()
        print(f"✅ User interactions: {interactions.count or 0} total")
        
        # Check by type
        clicks = supabase.table('user_interactions')\
            .select('*', count='exact')\
            .eq('interaction_type', 'click')\
            .execute()
        print(f"   - Clicks: {clicks.count or 0}")
        
        # Check recommendation results
        recs = supabase.table('recommendation_results').select('*', count='exact').execute()
        print(f"✅ Recommendation results: {recs.count or 0} total")
        
        # Check sessions
        sessions = supabase.table('user_sessions').select('*', count='exact').execute()
        print(f"✅ User sessions: {sessions.count or 0} total")
        
        # Calculate CTR
        if recs.count and recs.count > 0:
            ctr = (clicks.count or 0) / recs.count * 100
            print(f"\n📊 Current Metrics:")
            print(f"   - Click-through rate: {ctr:.2f}%")
            print(f"   - Interactions per session: {(interactions.count or 0) / max(sessions.count or 1, 1):.2f}")
        
        if (interactions.count or 0) > 0:
            print(f"\n✅ Sufficient data for RL training ({interactions.count} interactions)")
            return True
        else:
            print(f"\n⚠️  No interaction data yet - RL will use cold start (similarity only)")
            return True  # Not a failure, just a warning
        
    except Exception as e:
        print(f"❌ Failed to check interaction data: {str(e)}")
        return False

def test_recommendation_generation():
    """Test if recommendations can be generated"""
    print("\n" + "=" * 60)
    print("6. TESTING RECOMMENDATION GENERATION")
    print("=" * 60)
    
    try:
        from services.rl_recommendation_engine import get_rl_engine
        
        rl_engine = get_rl_engine()
        
        # Create a test user ID
        test_user_id = 'test_user_rl_verification'
        
        print(f"Testing with user ID: {test_user_id}")
        print("Generating 5 recommendations...")
        
        result = rl_engine.get_recommendations(
            user_id=test_user_id,
            num_recommendations=5,
            use_rl=True,
            offset=0
        )
        
        if result.get('success'):
            recs = result.get('recommendations', [])
            print(f"✅ Generated {len(recs)} recommendations")
            print(f"   - Method: {result.get('method', 'unknown')}")
            print(f"   - Duration: {result.get('duration_ms', 0):.2f}ms")
            print(f"   - Exploration rate: {result.get('exploration_rate', 0)}")
            
            if recs:
                print(f"\n   Sample recommendation:")
                sample = recs[0]
                print(f"   - Title: {sample.get('title', 'N/A')[:60]}")
                print(f"   - Similarity: {sample.get('similarity', 0):.4f}")
                print(f"   - RL Score: {sample.get('rl_score', 0):.4f}")
                print(f"   - Method: {sample.get('recommendation_method', 'N/A')}")
            
            return True
        else:
            print(f"❌ Failed to generate recommendations: {result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all verification checks"""
    print("\n" + "🔍" * 30)
    print("RL RECOMMENDATION SYSTEM ACTIVATION VERIFICATION")
    print("🔍" * 30 + "\n")
    
    results = {
        'Imports': check_imports(),
        'RL Engine': check_rl_engine(),
        'Background Tasks': check_background_tasks(),
        'Database Tables': check_database_tables(),
        'Interaction Data': check_existing_data(),
        'Recommendation Test': test_recommendation_generation()
    }
    
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - RL SYSTEM READY!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start your Flask app with: python app.py")
        print("2. Monitor RL performance at: /api/admin/analytics/rl-performance")
        print("3. Background training will run daily at 2:00 AM")
        print("4. Trigger manual training at: POST /api/admin/rl/trigger-training")
    else:
        print("⚠️  SOME CHECKS FAILED - PLEASE FIX ISSUES ABOVE")
        print("=" * 60)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

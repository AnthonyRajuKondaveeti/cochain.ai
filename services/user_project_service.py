"""
User Project Service
Handles user-created projects for collaboration
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any

class UserProjectService:
    def __init__(self):
        # In a real app, this would connect to a database
        # For demo, we'll use in-memory storage
        self.projects = self._create_mock_projects()
        self.collaboration_requests = []
    
    def _create_mock_projects(self) -> List[Dict]:
        """Create mock user projects for demo"""
        return [
            {
                'id': str(uuid.uuid4()),
                'title': 'E-Commerce Platform',
                'description': 'Building a modern e-commerce platform with React and Node.js. Looking for frontend developers and UI/UX designers.',
                'creator_id': 'user_1',
                'creator_name': 'Sarah Chen',
                'tech_stack': ['React', 'Node.js', 'MongoDB', 'Express'],
                'required_skills': ['Frontend Development', 'Backend Development', 'UI/UX Design'],
                'complexity_level': 'intermediate',
                'estimated_duration': '2-3 months',
                'max_collaborators': 5,
                'current_collaborators': 3,
                'domain': 'E-Commerce',
                'is_open_for_collaboration': True,
                'created_at': '2024-10-01T10:00:00Z',
                'status': 'active'
            },
            {
                'id': str(uuid.uuid4()),
                'title': 'AI Chatbot Assistant',
                'description': 'Creating an AI-powered customer service chatbot using Python and TensorFlow. Need ML engineers and backend developers.',
                'creator_id': 'user_2',
                'creator_name': 'Mike Johnson',
                'tech_stack': ['Python', 'TensorFlow', 'FastAPI', 'PostgreSQL'],
                'required_skills': ['Machine Learning', 'Backend Development', 'Natural Language Processing'],
                'complexity_level': 'advanced',
                'estimated_duration': '1 month',
                'max_collaborators': 6,
                'current_collaborators': 3,
                'domain': 'Artificial Intelligence',
                'is_open_for_collaboration': True,
                'created_at': '2024-10-05T14:30:00Z',
                'status': 'active'
            },
            {
                'id': str(uuid.uuid4()),
                'title': 'Mobile Fitness Tracker',
                'description': 'Developing a fitness tracking app with social features. Seeking mobile developers and designers.',
                'creator_id': 'user_3',
                'creator_name': 'Alex Rivera',
                'tech_stack': ['React Native', 'Firebase', 'TypeScript'],
                'required_skills': ['Mobile Development', 'UI/UX Design', 'Backend Development'],
                'complexity_level': 'beginner',
                'estimated_duration': '3 weeks',
                'max_collaborators': 4,
                'current_collaborators': 1,
                'domain': 'Health & Fitness',
                'is_open_for_collaboration': True,
                'created_at': '2024-10-08T09:15:00Z',
                'status': 'active'
            }
        ]
    
    def get_open_projects(self, limit: int = 20) -> List[Dict]:
        """Get all projects open for collaboration"""
        open_projects = [p for p in self.projects if p['is_open_for_collaboration']]
        return open_projects[:limit]
    
    def get_project(self, project_id: str) -> Dict:
        """Get specific project by ID"""
        for project in self.projects:
            if project['id'] == project_id:
                return project
        return None
    
    def create_project(self, project_data: Dict) -> Dict:
        """Create a new project"""
        project = {
            'id': str(uuid.uuid4()),
            'created_at': datetime.now().isoformat() + 'Z',
            'current_collaborators': 1,  # Creator counts as one
            'status': 'active',
            'is_open_for_collaboration': True,
            **project_data
        }
        self.projects.append(project)
        return {'success': True, 'project_id': project['id']}
    
    def get_user_projects(self, user_id: str) -> List[Dict]:
        """Get projects created by a specific user"""
        return [p for p in self.projects if p['creator_id'] == user_id]
    
    def send_collaboration_request(self, request_data: Dict) -> Dict:
        """Send a collaboration request"""
        request = {
            'id': str(uuid.uuid4()),
            'created_at': datetime.now().isoformat() + 'Z',
            'status': 'pending',
            **request_data
        }
        self.collaboration_requests.append(request)
        return {'success': True, 'request_id': request['id']}

# Global instance
project_service = UserProjectService()
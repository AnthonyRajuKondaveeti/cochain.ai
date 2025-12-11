# CoChain.ai - AI-Powered Project Recommendation System

A sophisticated recommendation system that helps students and developers discover relevant GitHub projects based on their skills, learning goals, and project ideas. Built with Flask, Supabase, and advanced machine learning embeddings.

## 🌟 Features

- **Intelligent Recommendations**: Uses SentenceTransformer embeddings to find semantically similar projects
- **Comprehensive Input Processing**: Accepts project ideas, objectives, skills, and complexity preferences
- **Advanced Analytics**: Tracks user interactions, click-through rates, and recommendation quality
- **Scalable Architecture**: Built with Flask API and PostgreSQL with pgvector for efficient similarity search
- **Real-time Analytics**: Monitor recommendation performance and user engagement

## 🛠 Tech Stack

- **Backend**: Flask (Python 3.12+)
- **Database**: Supabase (PostgreSQL with pgvector extension)
- **ML Model**: SentenceTransformer (all-MiniLM-L6-v2)
- **Vector Processing**: NumPy for similarity calculations
- **Data Processing**: Pandas for data manipulation

## 📋 Prerequisites

- Python 3.12 or higher
- Supabase account and project
- Basic understanding of REST APIs and machine learning concepts

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repository-url>
cd CoChain.ai
```

### 2. Create Virtual Environment

```bash
python -m venv env
env\Scripts\activate  # Windows
# source env/bin/activate  # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### 5. Database Setup

1. Go to your Supabase dashboard → SQL Editor
2. Copy and paste the contents of `database/enhanced_schema.sql`
3. Execute the SQL to create all required tables

### 6. Load Data

```bash
python database/load_data.py
```

This will:

- Load GitHub project data from `data/github_scraped.csv`
- Generate embeddings from `data/idea_embeddings.pkl`
- Populate the database with projects and their vector embeddings

### 7. Run the Application

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## 📚 API Documentation

### Get Recommendations

**Endpoint**: `POST /api/recommendations`

**Request Body**:

```json
{
  "project_idea": "I want to build a task management web application",
  "objectives": "Learn full-stack development and deploy to production",
  "achievements": "Complete a working web app with user authentication",
  "existing_skills": "HTML, CSS, basic JavaScript",
  "want_to_learn": "React, Node.js, database design",
  "complexity_level": "intermediate",
  "num_recommendations": 5
}
```

**Response**:

```json
{
  "recommendations": [
    {
      "id": "uuid-here",
      "github_id": "uuid-here",
      "title": "task-manager-react",
      "description": "A full-stack task management application...",
      "domain": "Web Development",
      "required_skills": ["React", "Node.js", "MongoDB"],
      "complexity_level": "Intermediate",
      "team_size": 2,
      "estimated_timeline": "2-3 months",
      "repository_url": "https://github.com/...",
      "stars": 1250,
      "similarity": 0.847,
      "user_query_id": "uuid-here"
    }
  ],
  "query_metadata": {
    "total_projects_analyzed": 2529,
    "processing_time": 1.23,
    "query_id": "uuid-here"
  }
}
```

### Track User Interaction

**Endpoint**: `POST /api/analytics/interaction`

**Request Body**:

```json
{
  "user_query_id": "uuid-from-recommendation",
  "github_reference_id": "uuid-from-recommendation",
  "interaction_type": "click",
  "rank_position": 1,
  "similarity_score": 0.847
}
```

### Submit Feedback

**Endpoint**: `POST /api/analytics/feedback`

**Request Body**:

```json
{
  "user_query_id": "uuid-from-recommendation",
  "github_reference_id": "uuid-from-recommendation",
  "rating": 4,
  "feedback_text": "Great recommendation! Very relevant to my needs."
}
```

### Get Analytics Summary

**Endpoint**: `GET /api/analytics/summary`

**Response**:

```json
{
  "total_queries": 150,
  "total_interactions": 89,
  "total_feedback": 23,
  "avg_rating": 4.2,
  "click_through_rate": 0.593,
  "popular_projects": [
    {
      "title": "react-task-manager",
      "click_count": 12,
      "avg_rating": 4.5
    }
  ]
}
```

## 🏗 Project Structure

```
CoChain.ai/
├── app.py                          # Main Flask application
├── app_config.py                   # Configuration settings
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (create this)
├── .gitignore                     # Git ignore file
├── data/                          # Data files
│   ├── github_scraped.csv         # GitHub project dataset
│   ├── idea_embeddings.pkl        # Pre-computed embeddings
│   └── student_ideas_transformed.csv
├── database/                      # Database related files
│   ├── connection.py              # Supabase connection
│   ├── enhanced_schema.sql        # Database schema
│   └── load_data.py              # Data loading utilities
└── services/                     # Core business logic
    ├── enhanced_recommendation_engine.py  # Main recommendation engine
    └── analytics_service.py       # Analytics and tracking
```

## 🧠 How It Works

### 1. Embedding Generation

- User input is processed and combined into a comprehensive query text
- SentenceTransformer generates a 384-dimensional embedding vector
- Query and embedding are stored for analytics

### 2. Similarity Search

- User embedding is compared against 2500+ pre-computed project embeddings
- Cosine similarity is calculated using NumPy for efficiency
- Projects are ranked by similarity score

### 3. Filtering & Ranking

- Results are filtered by complexity level preferences
- Final recommendations include project metadata and similarity scores
- User interactions are tracked for continuous improvement

### 4. Analytics Pipeline

- All user queries, interactions, and feedback are stored
- Real-time analytics provide insights into recommendation quality
- Click-through rates and user satisfaction metrics are calculated

## 🔧 Configuration

### Complexity Levels

- `1` or `"beginner"`: Simple projects suitable for learning
- `2` or `"intermediate"`: Moderate complexity with multiple features
- `3` or `"advanced"`: Complex projects requiring advanced skills

### Recommendation Engine Settings

- **Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Similarity**: Cosine similarity
- **Max Recommendations**: Configurable (default: 5)
- **Database Pagination**: 1000 records per batch

## 📊 Analytics Dashboard

The system tracks comprehensive analytics:

- **User Engagement**: Query patterns, interaction rates
- **Recommendation Quality**: Similarity scores, user ratings
- **Popular Projects**: Most clicked and highest rated
- **Performance Metrics**: Response times, success rates

## 🚀 Deployment

### Local Development

```bash
python app.py
```

### Production Deployment

1. Set up a production Supabase instance
2. Configure environment variables for production
3. Deploy to your preferred platform (Heroku, AWS, etc.)
4. Ensure proper error logging and monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit your changes: `git commit -m 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Common Issues

**"No similar projects found"**

- Ensure the database has embeddings loaded
- Check if Supabase connection is working
- Verify the embeddings table has data

**Import errors**

- Ensure virtual environment is activated
- Install all requirements: `pip install -r requirements.txt`
- Check Python version (3.12+ required)

**Database connection issues**

- Verify `.env` file has correct Supabase credentials
- Check Supabase project is active and accessible
- Ensure pgvector extension is enabled

### Getting Help

1. Check the troubleshooting section above
2. Review the API documentation for proper request format
3. Check application logs for detailed error messages
4. Open an issue in the repository with detailed problem description

## 🔮 Future Enhancements

- **Multi-language Support**: Extend beyond Python projects
- **Advanced Filtering**: Skills-based filtering and difficulty assessment
- **Recommendation Explanations**: Why specific projects were recommended
- **User Profiles**: Persistent user preferences and history
- **Integration APIs**: GitHub integration for automatic skill detection
- **Machine Learning Pipeline**: Continuous model improvement based on user feedback

---

Built with ❤️ for the developer community. Happy coding! 🚀

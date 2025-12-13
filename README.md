# CoChain.ai - AI-Powered Project Recommendation & Collaboration Platform

**Connect, Collaborate, and Create with the Power of AI.**

CoChain.ai is a sophisticated platform designed to help developers and students discover relevant GitHub projects, find collaborators, and build their portfolios. It leverages advanced machine learning to provide intelligent project recommendations and fosters a community of builders.

---

## 📖 The Story Behind CoChain.ai

### 💡 Inspiration
The journey of a developer is often solitary. Beginners struggle to find projects that match their skill level, while experienced developers find it hard to source committed collaborators for their ambitious ideas. 

**CoChain.ai was born from a simple question:** *How can we use AI to bridge the gap between "I want to build something" and "Here is the perfect project and team for you"?*

Inspired by the collaborative spirit of open source and the precision of modern recommendation systems (like Netflix or Spotify), we set out to build a platform that understands *code* and *context*, not just keywords.

### 🎯 Why It Was Created
We created CoChain.ai to solve three core problems:
1.  **Analysis Paralysis**: Students often spend more time looking for project ideas than actually coding.
2.  **The "Hello World" Plateau**: Moving from tutorials to real-world projects is hard without guidance.
3.  **Collaboration Friction**: Finding peers with complementary skills is difficult in a fragmented ecosystem.

### 👥 Who Is It For?
*   **Students & Bootcamper Grads**: To find portfolio-worthy projects that match their current skill level and learning goals.
*   **Indie Developers**: To find collaborators for their side projects.
*   **Open Source Maintainers**: To discover contributors who are genuinely interested in their project's domain.
*   **Educators**: To recommend tailored projects to students based on their curriculum.

---

## 🛠️ Development Choices & Architecture

Building CoChain.ai required making several key architectural decisions to balance performance, cost, and scalability.

### 1. The Brain: Hybrid AI Approach
We chose a **hybrid approach** for our recommendation engine:
*   **SentenceTransformer (all-MiniLM-L6-v2)**: We use this model to generate 384-dimensional embeddings of project descriptions. This allows for *semantic search*—understanding that "task manager" is similar to "todo list" even if the words don't match.
*   **Reinforcement Learning (RL)**: We implemented a PPO (Proximal Policy Optimization) agent to fine-tune recommendations based on user interactions (clicks, bookmarks). The system "learns" what users actually find interesting, not just what is mathematically similar.

### 2. The Database: Supabase & pgvector
Instead of a separate vector database (like Pinecone) and a relational database, we chose **Supabase (PostgreSQL)** with the `pgvector` extension.
*   **Why?** This unified architecture simplifies our stack. We can perform vector similarity searches and relational queries (e.g., "find projects similar to X but only in Python") in a single SQL query.

### 3. The Backend: Flask (Python)
We selected **Flask** for its lightweight nature and rich ecosystem of data science libraries. It allows us to seamlessly integrate our ML models with our web API.

### 4. A/B Testing Framework
To ensure our features actually help users, we built a custom **A/B Testing System**. This allows us to scientifically test different recommendation algorithms (e.g., "Pure Semantic" vs. "RL-Enhanced") and UI layouts to see which yields better user engagement.

---

## 🌟 Key Features

*   **Intelligent Recommendations**: Discover projects that match your skills and interests using AI.
*   **Live Collaboration**: Post your own projects and find team members.
*   **Smart Search**: Semantic search that understands intent.
*   **Analytics Dashboard**: Track your engagement and see how the system learns from you.
*   **A/B Testing**: Experience a platform that constantly evolves to serve you better.

---

## 🚀 Quick Start

### Prerequisites
*   Python 3.12+
*   Supabase Account

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/cochain-ai.git
    cd cochain-ai
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Create a `.env` file:
    ```env
    SUPABASE_URL=your_url
    SUPABASE_KEY=your_key
    SUPABASE_SERVICE_KEY=your_service_key
    ```

4.  **Run the App**
    ```bash
    python app.py
    ```
    Visit `http://localhost:5000` to start exploring!

---

## 👥 About the Developers

CoChain.ai is developed by a passionate team of engineers and data scientists dedicated to democratizing software development.

*   **Anthony Raju Kondaveeti** - *AI/ML Engineer & Data Scientist*
    *   **Role**: Lead Architect for the AI/ML pipeline and Backend.
    *   **Contributions**: Designed the RAG system architecture, implemented the ML recommendation engine, developed the Flask backend with Supabase, and optimized vector embeddings.
    *   **Website**: https://anthonyrajukondaveeti.github.io

*   **Benison Jacob Benny** - *Data Scientist & ML Engineer*
    *   **Role**: Lead for Frontend Engineering and User Experience.
    *   **Contributions**: Designed and implemented the responsive UI/UX using Tailwind CSS, optimized mobile performance, and conducted user experience testing.
    *   **Website**: https://benisonjac.github.io

We believe that the best way to learn is to build together.

---

## � Documentation

For more detailed technical information, check out our guides:
*   **[Deployment Guide](DEPLOYMENT_GUIDE.md)**: How to host CoChain.ai for free.
*   **[RL Training Report](RL_TRAINING_REPORT.md)**: Deep dive into our Reinforcement Learning model.
*   **[A/B Testing Explained](AB_TESTING_EXPLAINED.md)**: How we measure success.

---

*Built with ❤️ for the developer community.*

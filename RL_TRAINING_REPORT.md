# RL Training Report

**Date**: December 2025  
**System**: CoChain.ai Recommendation Engine v3.0

## 1. Introduction

The CoChain.ai recommendation engine uses a hybrid architecture that combines **Content-Based Filtering** (using SentenceTransformer embeddings) with **Reinforcement Learning (RL)** to personalize project suggestions. This report details the RL implementation, specifically the Contextual Bandit algorithm used to optimize user engagement.

## 2. Model Architecture

We employ a **Thompson Sampling Contextual Bandit** model. Unlike full RL agents (like DQN or PPO) that optimize for long-term horizons, bandit algorithms optimize for immediate rewards, which is ideal for recommendation scenarios where the "state" (user preference) evolves slowly but the "action" (showing a project) needs immediate feedback.

### Key Components:

*   **Base Recommender**: `SentenceTransformer` (all-MiniLM-L6-v2) generates 384-dimensional embeddings for projects and user profiles. It provides the initial candidate set based on semantic similarity.
*   **Contextual Bandit**: A specific implementation of Thompson Sampling that maintains a Beta distribution (`Beta(α, β)`) for each project.
    *   **Alpha (α)**: Represents "successes" (positive interactions).
    *   **Beta (β)**: Represents "failures" (negative interactions or ignored impressions).

### The Math

For each project $p$ and user $u$:

1.  **Similarity Score ($S_{u,p}$)**: Cosine similarity between user and project embeddings.
2.  **Thompson Sample ($T_p$)**: Sampled from $Beta(\alpha_p, \beta_p)$. This models the *uncertainty* of the project's quality.
3.  **Final Score**: 
    The system uses a hybrid **Epsilon-Greedy + Thompson Sampling** strategy to balance exploration.

    *   **Pure Exploration (15% chance)**: The system ignores similarity and scores purely based on the Thompson Sample ($T_p$). This ensures we test projects that might be semantically different but high quality.
    *   **Weighted Scoring (85% chance)**: The system combines similarity and quality to find relevant, high-quality projects.
        $$ Score = 0.7 \times S_{u,p} + 0.3 \times T_p $$
    
    *   **Exploitation**: The 70% weight on similarity in the weighted score ensures recommendations remain relevant to the user's skills.
    *   **Exploration**: The 30% weight on the Thompson sample allows high-potential but unproven projects to bubble up.

## 3. State & Action Space

### State Space (Context)
The "state" is implicitly defined by the **User Profile Embedding**, which encapsulates:
*   Bio & Interests
*   Skills (Languages, Frameworks)
*   Education Level
*   Past Interactions (implicitly via embedding updates)

### Action Space
The action is **recommending a specific GitHub project** from our database. The valid actions for any given request are the top $N$ semantically similar projects (usually 30-50) retrieved by the base recommender. The Bandit re-ranks these candidates.

## 4. Reward Function

The Reward Calculator (`services/reward_calculator.py`) converts explicit and implicit user actions into a scalar reward signal.

| Interaction Type | Reward Value | Rationale |
| :--- | :--- | :--- |
| **Bookmark** | `+10.0` | Strongest signal of intent. |
| **Click (Details)** | `+5.0` | Active interest. |
| **Hover (>3s)** | `+0.8` | Passive interest. |
| **Impression** | `0.0` | Neutral baseline. |
| **Quick Exit (<10s)** | `-2.0` | Clickbait penalty. |
| **Unbookmark** | `-3.0` | Reversal of interest. |
| **1-Star Rating** | `-5.0` | Explicit negative feedback. |

**Adjustments:**
*   **Position Bias**: Clicks on lower-ranked items (e.g., position 6+) get a `1.1x` multiplier to reward active exploration.
*   **Time Decay**: Older interactions have reduced weight to allow user preferences to drift.

## 5. Training Process

### Algorithm: Online Learning with Batch Updates

The system supports both **Online** and **Batch** learning modes, but currently defaults to a daily Batch Update strategy for stability.

1.  **Data Collection**:
    *   All user interactions (clicks, views, bookmarks) are logged to the `user_interactions` Supabase table.
    *   `recommendation_results` tracks exactly what was shown and in what order.

2.  **Parameter Update (Daily Batch Job)**:
    *   A background job (`services/background_tasks.py`) runs every 24 hours.
    *   It fetches all interactions from the last `N` days.
    *   For each project, it aggregates rewards.
    *   **Update Rule**:
        *   If `Reward > 0`: $\alpha \leftarrow \alpha + (Reward \times LearningRate)$
        *   If `Reward < 0`: $\beta \leftarrow \beta + (|Reward| \times LearningRate)$

### Prior Beliefs
*   **Initial Priors**: $\alpha=2.0, \beta=2.0$ (Weakly positive prior to encourage initial exploration).
*   **Learning Rate**: `0.5` (Conservative updates to prevent volatility).

## 6. Performance Metrics

We track the following metrics to evaluate the RL model:

1.  **Average Reward per User**: The primary optimization target.
2.  **CTR (Click-Through Rate)**: The ratio of Clicks to Impressions.
3.  **Positive Interaction Rate**: $\%$ of sessions with at least one Bookmark or Click.
4.  **Catalog Coverage**: $\%$ of total projects that have been recommended at least once (measure of exploration).

## 7. Future Improvements

*   **Contextual Bandits with User Features**: Currently, $\alpha$ and $\beta$ are global per project. We plan to introduce user-cluster specific parameters (e.g., separate params for "Python Developers" vs "Java Developers").
*   **Real-time Updates**: Move from daily batch updates to stream processing for instant adaptation.
*   **Multi-Objective Optimization**: Optimize for both "User Relevance" and "Project Diversity" simultaneously.

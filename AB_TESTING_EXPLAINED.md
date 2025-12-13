# A/B Testing Explained

**Date**: December 2025  
**System**: CoChain.ai Experimentation Framework v1.0

## 1. Overview

To scientifically validate the impact of our Reinforcement Learning (RL) recommendation engine, CoChain.ai includes a built-in **A/B Testing Service**. This framework allows us to run controlled experiments where different users are exposed to different recommendation strategies, ensuring that we only deploy changes that objectively improve user engagement.

## 2. Experiment Design

### Hypotheses
The core hypothesis being tested is typically:
> *Running recommendations through the RL Bandit algorithm leads to higher user engagement (CTR, Bookmarks) compared to pure Semantic Similarity.*

### Groups
Users are deterministically assigned to one of two groups based on a consistent hash of their User ID. This ensures a user always sees the same experience for the duration of a test.

*   **Control Group (Baseline)**: Receives recommendations generated purely by `SentenceTransformer` embeddings and cosine similarity.
    *   *Logic*: "Show me projects that look exactly like my profile."
*   **Treatment Group (RL)**: Receives recommendations that are re-ranked by the `ContextualBandit` (Thompson Sampling).
    *   *Logic*: "Show me projects that look like my profile, *but prioritize ones that others have actually liked* and *occasionally surprise me*."

### Assignment Logic
*   **Input**: `User ID` (UUID)
*   **Process**: `MD5(User ID) % 100`
*   **Split**: Configurable (e.g., 50/50 split).
    *   If value < 50 $\rightarrow$ Control
    *   If value $\ge$ 50 $\rightarrow$ Treatment

## 3. Metrics & Statistical Significance

We track several key metrics to evaluate performance. The system automatically calculates these daily.

### Primary Metrics
1.  **Click-Through Rate (CTR)**: $\frac{\text{Total Clicks}}{\text{Total Recommendation Impressions}} \times 100$
2.  **Engagement Rate**: $\frac{\text{Any Interaction (Click/Bookmark)}}{\text{Impressions}} \times 100$
3.  **Average Reward**: The mean reward value earned per session (as defined in `RewardCalculator`).

### Statistical Significance (P-Value)
We use a **Two-Proportion Z-Test** to determine if the difference in CTR between groups is statistically significant or just random noise.

*   **Confidence Level**: 95% ($\alpha = 0.05$)
*   **Null Hypothesis ($H_0$)**: $CTR_{treatment} = CTR_{control}$
*   **Alternative Hypothesis ($H_1$)**: $CTR_{treatment} \neq CTR_{control}$

If $p < 0.05$, we reject the null hypothesis and declare a statistically significant winner.

## 4. Implementation Details

The testing logic is encapsulated in `services/ab_test_service.py`.

### Lifecycle of a Test
1.  **Start**: Admin initiates a test via the API/Dashboard, setting variables like `control_percentage` (default 50%).
2.  **Assignment**: As users log in, they are assigned to a group. Assignments are persisted in the `ab_test_assignments` table.
3.  **Tracking**: Every recommendation request and subsequent interaction is tagged with the user's active group assignment.
4.  **Analysis**: The system computes cumulative metrics for both groups.
5.  **Conclusion**:
    *   If the Treatment group wins with significance, the feature is "rolled out" (RL becomes default for everyone).
    *   If there is no significant difference, we typically stick to the simpler model (Control) or extend the test.

## 5. Current Status

*   **Active Framework**: The code supports live A/B testing.
*   **Default Behavior**: If no test is running, the system defaults to the **RL (Treatment)** behavior, as early offline evaluation showed it superior to the baseline.

## 6. How to Run a Test

Admins can trigger a new test via the backend console or API:

```python
from services.ab_test_service import get_ab_test_service

service = get_ab_test_service()
service.start_new_test(
    test_name="RL_vs_Baseline_v1",
    control_percentage=50,
    duration_days=14,
    description="Testing bandit model with alpha=2.0"
)
```

## 7. Interpretation of Results

When analyzing results, we look for **Practical Significance** alongside Statistical Significance.
*   *Small Effect*: < 2% relative improvement.
*   *Moderate Effect*: 2-5% relative improvement.
*   *Strong Effect*: > 5% relative improvement.

We generally only adopt the RL model complexity if we see at least a **Moderate Effect**.

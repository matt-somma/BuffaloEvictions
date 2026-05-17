DROP TABLE IF EXISTS analytics.neighborhood_state_transitions;

CREATE TABLE analytics.neighborhood_state_transitions AS
WITH ordered AS (
    SELECT
        geoid,
        month_date,
        neighborhood_trajectory AS current_state,
        LEAD(neighborhood_trajectory) OVER (
            PARTITION BY geoid
            ORDER BY month_date
        ) AS next_state
    FROM analytics.tract_state_history
)

SELECT
    current_state,
    next_state,
    COUNT(*) AS transition_count
FROM ordered
WHERE next_state IS NOT NULL
GROUP BY current_state, next_state;
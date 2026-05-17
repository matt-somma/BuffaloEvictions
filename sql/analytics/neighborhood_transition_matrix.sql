DROP TABLE IF EXISTS analytics.neighborhood_transition_matrix;

CREATE TABLE analytics.neighborhood_transition_matrix AS
WITH totals AS (
    SELECT
        current_state,
        next_state,
        transition_count,
        SUM(transition_count) OVER (
            PARTITION BY current_state
        ) AS total_transitions_from_state
    FROM analytics.neighborhood_state_transitions
)

SELECT
    current_state,
    next_state,
    transition_count,
    total_transitions_from_state,
    transition_count::numeric
        / NULLIF(total_transitions_from_state, 0) AS transition_probability
FROM totals;
DROP TABLE IF EXISTS analytics.neighborhood_multistep_transition_matrix;

CREATE TABLE analytics.neighborhood_multistep_transition_matrix AS
WITH states AS (
    SELECT DISTINCT current_state AS state_name
    FROM analytics.neighborhood_transition_matrix

    UNION

    SELECT DISTINCT next_state AS state_name
    FROM analytics.neighborhood_transition_matrix
),

one_step AS (
    SELECT
        s1.state_name AS current_state,
        s2.state_name AS next_state,
        COALESCE(m.transition_probability, 0) AS probability_1m
    FROM states s1
    CROSS JOIN states s2
    LEFT JOIN analytics.neighborhood_transition_matrix m
        ON s1.state_name = m.current_state
       AND s2.state_name = m.next_state
),

three_step AS (
    SELECT
        a.current_state,
        c.next_state,
        SUM(
            a.probability_1m
          * b.probability_1m
          * c.probability_1m
        ) AS probability_3m
    FROM one_step a
    JOIN one_step b
        ON a.next_state = b.current_state
    JOIN one_step c
        ON b.next_state = c.current_state
    GROUP BY
        a.current_state,
        c.next_state
),

six_step AS (
    SELECT
        a.current_state,
        b.next_state,
        SUM(
            a.probability_3m
          * b.probability_3m
        ) AS probability_6m
    FROM three_step a
    JOIN three_step b
        ON a.next_state = b.current_state
    GROUP BY
        a.current_state,
        b.next_state
),

twelve_step AS (
    SELECT
        a.current_state,
        b.next_state,
        SUM(
            a.probability_6m
          * b.probability_6m
        ) AS probability_12m
    FROM six_step a
    JOIN six_step b
        ON a.next_state = b.current_state
    GROUP BY
        a.current_state,
        b.next_state
)

SELECT
    o.current_state,
    o.next_state,
    o.probability_1m,
    t.probability_3m,
    s.probability_6m,
    tw.probability_12m
FROM one_step o
LEFT JOIN three_step t
    ON o.current_state = t.current_state
   AND o.next_state = t.next_state
LEFT JOIN six_step s
    ON o.current_state = s.current_state
   AND o.next_state = s.next_state
LEFT JOIN twelve_step tw
    ON o.current_state = tw.current_state
   AND o.next_state = tw.next_state;
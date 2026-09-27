# Risk Engine

For each district, each Phase 7F estimator emits a raw score in the model's positive-class output. It is not a calibrated probability or verified-event likelihood. A hazard development signal is active when its score reaches the threshold selected on synthetic validation data.

The combined development score is the maximum of the six raw hazard scores; there are no cross-hazard weights. Alert levels are development-only labels: below threshold is NORMAL; threshold exceedance is WATCH, ELEVATED, or HIGH as the score-to-threshold ratio increases. These are not government warning levels and do not trigger external notifications.

Resource planning computes a separate 0-100 demonstration priority from normalized components: 30% raw model score, 25% simulated exposure index, 20% simulated vulnerability index, 15% development severity band, and 10% count-based signal urgency. The severity band is derived from the uncalibrated score; these weights are illustrative, not fitted to outcomes. This ranking must not be interpreted as an operational risk assessment.

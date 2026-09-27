# Resource Allocation

## Deterministic Demonstration

api/resource_planning.py combines synthetic development signals with simulated exposure and vulnerability. It merges compatible resource needs across active hazards, orders districts by the documented priority score, and chooses the nearest available compatible scenario record under a 240-minute simulated limit. Requested capacity is bounded by the record's available capacity. Resource IDs are globally consumed once per generated plan.

The scenario contains response teams, ambulances, medical kits, water/food supplies, shelters, hospitals, and resource depots. Each recommendation includes priority components, quantities, unique resource IDs, simulated travel estimates, unmet needs, and a reason.

## Limitations

There are no official resource inventories, facility locations, population/exposure values, vulnerability layers, road graph, dispatch capacity, or verified suitability rules. The weather coordinates are only illustrative nodes. Straight-line distance plus fixed assumptions is not road routing. All outputs are SIMULATION_ONLY_NOT_FOR_DISPATCH; no optimization is trained against the fabricated scenario and no external dispatch action exists.

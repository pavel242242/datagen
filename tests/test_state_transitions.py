"""
Tests for state transition modeling (Feature #4).
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from datagen.core.state_transition_utils import (
    simulate_state_transitions,
    get_current_states,
    calculate_state_statistics
)


class TestStateTransitionSimulation:
    """Test core state machine simulation."""

    def test_simple_two_state_machine(self):
        """Test simple active ⇄ paused transitions."""
        # Parent entities
        parent_df = pd.DataFrame({
            "user_id": [1, 2, 3],
            "created_at": pd.to_datetime([
                "2024-01-01",
                "2024-01-15",
                "2024-02-01"
            ])
        })

        # State model: active ⇄ paused (no terminal)
        state_model = {
            "initial_state": "active",
            "states": {
                "active": {
                    "transition_prob_per_period": 0.3,
                    "next_states": {
                        "paused": 1.0
                    }
                },
                "paused": {
                    "transition_prob_per_period": 0.5,
                    "next_states": {
                        "active": 1.0
                    }
                }
            },
            "period_unit": "month",
            "max_transitions": 5
        }

        # Simulate
        rng = np.random.default_rng(42)
        transitions = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="user_id",
            parent_created_at_col="created_at",
            timeframe_end=pd.Timestamp("2024-12-31"),
            rng=rng
        )

        # Assertions
        assert not transitions.empty
        assert "user_id" in transitions.columns
        assert "transition_time" in transitions.columns
        assert "from_state" in transitions.columns
        assert "to_state" in transitions.columns

        # All users should have at least initial state
        assert transitions["user_id"].nunique() == 3

        # Check initial states
        initial_transitions = transitions[transitions["from_state"].isna()]
        assert len(initial_transitions) == 3
        assert (initial_transitions["to_state"] == "active").all()

        # Check state alternation
        for user_id in [1, 2, 3]:
            user_transitions = transitions[transitions["user_id"] == user_id].sort_values("transition_time")
            states = user_transitions["to_state"].tolist()

            # Should alternate between active and paused
            for i in range(1, len(states)):
                assert states[i] != states[i-1], f"User {user_id} has consecutive same states"

    def test_terminal_state_reached(self):
        """Test that terminal states stop further transitions."""
        parent_df = pd.DataFrame({
            "customer_id": [1, 2, 3, 4, 5],
            "created_at": pd.to_datetime(["2024-01-01"] * 5)
        })

        # State model with terminal state
        state_model = {
            "initial_state": "trial",
            "states": {
                "trial": {
                    "transition_prob_per_period": 0.9,
                    "next_states": {
                        "active": 0.3,
                        "churned": 0.7
                    }
                },
                "active": {
                    "transition_prob_per_period": 0.1,
                    "next_states": {
                        "churned": 1.0
                    }
                },
                "churned": {
                    "terminal": True
                }
            },
            "period_unit": "month",
            "max_transitions": 10
        }

        rng = np.random.default_rng(42)
        transitions = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="customer_id",
            parent_created_at_col="created_at",
            timeframe_end=pd.Timestamp("2024-12-31"),
            rng=rng
        )

        # Check no transitions after churned
        for customer_id in [1, 2, 3, 4, 5]:
            customer_trans = transitions[transitions["customer_id"] == customer_id].sort_values("transition_time")

            # Find first churned state
            churned_idx = customer_trans[customer_trans["to_state"] == "churned"].index

            if len(churned_idx) > 0:
                first_churn_idx = churned_idx[0]

                # Get transitions after churn
                after_churn = customer_trans[customer_trans.index > first_churn_idx]

                # Should be no transitions after churned
                assert len(after_churn) == 0, f"Customer {customer_id} has transitions after churned"

    def test_max_transitions_limit(self):
        """Test max_transitions cap is respected."""
        parent_df = pd.DataFrame({
            "user_id": [1],
            "created_at": pd.to_datetime(["2024-01-01"])
        })

        # High probability transitions
        state_model = {
            "initial_state": "active",
            "states": {
                "active": {
                    "transition_prob_per_period": 0.9,
                    "next_states": {
                        "paused": 1.0
                    }
                },
                "paused": {
                    "transition_prob_per_period": 0.9,
                    "next_states": {
                        "active": 1.0
                    }
                }
            },
            "period_unit": "day",
            "max_transitions": 5
        }

        rng = np.random.default_rng(42)
        transitions = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="user_id",
            parent_created_at_col="created_at",
            timeframe_end=pd.Timestamp("2024-12-31"),
            rng=rng
        )

        # Should have at most max_transitions + 1 (including initial)
        assert len(transitions) <= 6, f"Too many transitions: {len(transitions)}"

    def test_segment_variation(self):
        """Test segment-based churn multipliers."""
        parent_df = pd.DataFrame({
            "customer_id": list(range(1, 101)),
            "tier": ["vip"] * 50 + ["budget"] * 50,
            "created_at": pd.to_datetime(["2024-01-01"] * 100)
        })

        state_model = {
            "initial_state": "active",
            "states": {
                "active": {
                    "transition_prob_per_period": 0.2,
                    "next_states": {
                        "churned": 1.0
                    }
                },
                "churned": {
                    "terminal": True
                }
            },
            "period_unit": "month",
            "max_transitions": 10,
            "segment_variation": {
                "vip": {"churn_multiplier": 0.5},
                "budget": {"churn_multiplier": 1.5}
            }
        }

        rng = np.random.default_rng(42)
        transitions = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="customer_id",
            parent_created_at_col="created_at",
            parent_segment_col="tier",
            timeframe_end=pd.Timestamp("2024-12-31"),
            rng=rng
        )

        # Get current states
        current = get_current_states(transitions, "customer_id")

        # Merge with segments
        current = current.merge(parent_df[["customer_id", "tier"]], on="customer_id")

        # Count churned by segment
        vip_churned = current[(current["tier"] == "vip") & (current["current_state"] == "churned")]
        budget_churned = current[(current["tier"] == "budget") & (current["current_state"] == "churned")]

        vip_churn_rate = len(vip_churned) / 50
        budget_churn_rate = len(budget_churned) / 50

        # Budget should churn more than VIP (not exact, but directional)
        assert budget_churn_rate > vip_churn_rate, \
            f"Budget churn ({budget_churn_rate:.2f}) should be > VIP churn ({vip_churn_rate:.2f})"

    def test_vintage_variation(self):
        """Test vintage effects on transition rates."""
        # Create entities at different times
        parent_df = pd.DataFrame({
            "user_id": list(range(1, 101)),
            "created_at": pd.to_datetime([
                "2024-01-01" if i < 50 else "2024-06-01"
                for i in range(1, 101)
            ])
        })

        state_model = {
            "initial_state": "active",
            "states": {
                "active": {
                    "transition_prob_per_period": 0.15,
                    "next_states": {
                        "churned": 1.0
                    }
                },
                "churned": {
                    "terminal": True
                }
            },
            "period_unit": "month",
            "max_transitions": 10
        }

        # Older entities churn less (retention improves with age)
        vintage_behavior = {
            "churn_multiplier_curve": [1.0, 0.8, 0.6, 0.5, 0.4, 0.3]
        }

        rng = np.random.default_rng(42)
        transitions = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="user_id",
            parent_created_at_col="created_at",
            timeframe_end=pd.Timestamp("2024-12-31"),
            vintage_behavior=vintage_behavior,
            rng=rng
        )

        # Get current states
        current = get_current_states(transitions, "user_id")
        current = current.merge(parent_df[["user_id", "created_at"]], on="user_id")

        # Split by cohort
        early_cohort = current[current["created_at"] == "2024-01-01"]
        late_cohort = current[current["created_at"] == "2024-06-01"]

        early_churned = (early_cohort["current_state"] == "churned").sum() / len(early_cohort)
        late_churned = (late_cohort["current_state"] == "churned").sum() / len(late_cohort)

        # Early cohort should churn less (had time for vintage effect to kick in)
        assert early_churned < late_churned, \
            f"Early cohort churn ({early_churned:.2f}) should be < late cohort ({late_churned:.2f})"

    def test_deterministic_behavior(self):
        """Test same seed produces identical transitions."""
        parent_df = pd.DataFrame({
            "user_id": [1, 2, 3],
            "created_at": pd.to_datetime(["2024-01-01"] * 3)
        })

        state_model = {
            "initial_state": "active",
            "states": {
                "active": {
                    "transition_prob_per_period": 0.3,
                    "next_states": {
                        "paused": 0.6,
                        "churned": 0.4
                    }
                },
                "paused": {
                    "transition_prob_per_period": 0.5,
                    "next_states": {
                        "active": 0.7,
                        "churned": 0.3
                    }
                },
                "churned": {
                    "terminal": True
                }
            },
            "period_unit": "month",
            "max_transitions": 5
        }

        # Run twice with same seed
        rng1 = np.random.default_rng(12345)
        transitions1 = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="user_id",
            parent_created_at_col="created_at",
            timeframe_end=pd.Timestamp("2024-12-31"),
            rng=rng1
        )

        rng2 = np.random.default_rng(12345)
        transitions2 = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="user_id",
            parent_created_at_col="created_at",
            timeframe_end=pd.Timestamp("2024-12-31"),
            rng=rng2
        )

        # Should be identical
        assert len(transitions1) == len(transitions2)

        # Sort and compare
        t1_sorted = transitions1.sort_values(["user_id", "transition_time"]).reset_index(drop=True)
        t2_sorted = transitions2.sort_values(["user_id", "transition_time"]).reset_index(drop=True)

        pd.testing.assert_frame_equal(t1_sorted, t2_sorted)


class TestStateHelpers:
    """Test helper functions."""

    def test_get_current_states(self):
        """Test getting current state per entity."""
        transitions = pd.DataFrame({
            "user_id": [1, 1, 1, 2, 2],
            "transition_time": pd.to_datetime([
                "2024-01-01",
                "2024-02-01",
                "2024-03-01",
                "2024-01-15",
                "2024-04-01"
            ]),
            "from_state": [None, "active", "paused", None, "active"],
            "to_state": ["active", "paused", "active", "active", "churned"]
        })

        current = get_current_states(transitions, "user_id")

        assert len(current) == 2
        assert current[current["user_id"] == 1]["current_state"].values[0] == "active"
        assert current[current["user_id"] == 2]["current_state"].values[0] == "churned"

    def test_calculate_state_statistics(self):
        """Test summary statistics calculation."""
        transitions = pd.DataFrame({
            "user_id": [1, 1, 1, 2, 2, 3],
            "transition_time": pd.to_datetime([
                "2024-01-01",
                "2024-02-01",
                "2024-03-01",
                "2024-01-15",
                "2024-04-01",
                "2024-01-20"
            ]),
            "from_state": [None, "active", "paused", None, "active", None],
            "to_state": ["active", "paused", "active", "active", "churned", "active"]
        })

        stats = calculate_state_statistics(transitions, "user_id")

        assert stats["total_entities"] == 3
        assert stats["total_transitions"] == 6
        assert stats["avg_transitions_per_entity"] == 2.0

        # Check state distribution (current states)
        assert "active" in stats["state_distribution"]
        assert "churned" in stats["state_distribution"]

        # Check transition matrix
        assert len(stats["transition_matrix"]) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_parent_df(self):
        """Test with no parent entities."""
        parent_df = pd.DataFrame({
            "user_id": [],
            "created_at": []
        })

        state_model = {
            "initial_state": "active",
            "states": {
                "active": {"terminal": True}
            },
            "period_unit": "month"
        }

        rng = np.random.default_rng(42)
        transitions = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="user_id",
            parent_created_at_col="created_at",
            rng=rng
        )

        assert transitions.empty

    def test_no_transitions_possible(self):
        """Test state with zero transition probability."""
        parent_df = pd.DataFrame({
            "user_id": [1, 2],
            "created_at": pd.to_datetime(["2024-01-01", "2024-01-01"])
        })

        # State with no transitions defined
        state_model = {
            "initial_state": "active",
            "states": {
                "active": {
                    "transition_prob_per_period": 0.0
                }
            },
            "period_unit": "month"
        }

        rng = np.random.default_rng(42)
        transitions = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="user_id",
            parent_created_at_col="created_at",
            timeframe_end=pd.Timestamp("2024-12-31"),
            rng=rng
        )

        # Should only have initial states
        assert len(transitions) == 2
        assert (transitions["from_state"].isna()).all()

    def test_timeframe_limits(self):
        """Test transitions respect timeframe boundaries."""
        parent_df = pd.DataFrame({
            "user_id": [1],
            "created_at": pd.to_datetime(["2024-01-01"])
        })

        state_model = {
            "initial_state": "active",
            "states": {
                "active": {
                    "transition_prob_per_period": 0.9,
                    "next_states": {
                        "paused": 1.0
                    }
                },
                "paused": {
                    "transition_prob_per_period": 0.9,
                    "next_states": {
                        "active": 1.0
                    }
                }
            },
            "period_unit": "day",
            "max_transitions": 100
        }

        # Very short timeframe
        rng = np.random.default_rng(42)
        transitions = simulate_state_transitions(
            parent_df=parent_df,
            state_model=state_model,
            parent_id_col="user_id",
            parent_created_at_col="created_at",
            timeframe_end=pd.Timestamp("2024-01-10"),  # Only 9 days
            rng=rng
        )

        # All transitions should be before end date
        assert (transitions["transition_time"] <= pd.Timestamp("2024-01-10")).all()

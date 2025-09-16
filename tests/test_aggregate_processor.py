from pi_tx.domain.channel_store import ChannelStore


def test_aggregate_basic_sum_and_clamp():
    cs = ChannelStore(size=6)
    cs.configure_processors(
        {
            "aggregate": [
                {
                    "channels": [
                        {"id": "ch1", "value": 0.4},
                        {"id": "ch2", "value": 0.1},
                        {"id": "ch3", "value": 0.5},
                    ],
                    "target": "ch6",
                }
            ]
        }
    )
    cs.set_many({1: -1.0, 2: 0.25, 3: 0.75})
    snap = cs.snapshot()
    assert abs(snap[5] - 0.8) < 1e-6


def test_aggregate_no_target_uses_first_source_as_target():
    cs = ChannelStore(size=4)
    cs.configure_processors(
        {
            "aggregate": [
                {"channels": [{"id": "ch1", "value": 0.25}, {"id": "ch2", "value": 0.25}]}
            ]
        }
    )
    cs.set_many({1: 0.4, 2: -0.8})
    snap = cs.snapshot()
    assert abs(snap[0] - 0.3) < 1e-6
    assert abs(snap[1] - (-0.8)) < 1e-6


def test_aggregate_sum_clamps_only_final_result():
    cs = ChannelStore(size=3)
    cs.configure_processors(
        {
            "aggregate": [
                {
                    "channels": [
                        {"id": "ch1", "value": 1.0},
                        {"id": "ch2", "value": 1.0},
                        {"id": "ch3", "value": 1.0},
                    ]
                }
            ]
        }
    )
    cs.set_many({1: 0.7, 2: 0.6, 3: 0.9})
    snap = cs.snapshot()
    assert snap[0] == 1.0
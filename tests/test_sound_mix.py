from pi_tx.domain.channel_store import ChannelStore


def test_aggregate_basic_sum_and_clamp():
    cs = ChannelStore(size=6)
    # configure: aggregate of channels with distinct weights targeting channel 6
    cs.configure_processors(
        {
            "aggregate": [
                {
                    "channels": [
                        {"id": 1, "value": 0.4},
                        {"id": 2, "value": 0.1},
                        {"id": 3, "value": 0.5},
                    ],
                    "target": 6,
                }
            ]
        }
    )
    # set channels with bipolar style values within -1..1
    cs.set_many({1: -1.0, 2: 0.25, 3: 0.75})
    snap = cs.snapshot()
    # expected weighted sum: 1*0.4 + 0.25*0.1 + 0.75*0.5 = 0.4 + 0.025 + 0.375 = 0.8
    assert abs(snap[5] - 0.8) < 1e-6


def test_aggregate_no_target_uses_first_source_as_target():
    cs = ChannelStore(size=4)
    cs.configure_processors(
        {
            "aggregate": [
                {"channels": [{"id": 1, "value": 0.25}, {"id": 2, "value": 0.25}]}
            ]
        }
    )
    cs.set_many({1: 0.4, 2: -0.8})
    snap = cs.snapshot()
    # first source replaced by aggregate; second source unchanged
    assert abs(snap[0] - 0.3) < 1e-6  # (0.4+0.8)*0.25
    assert abs(snap[1] - (-0.8)) < 1e-6


def test_aggregate_sum_clamps_only_final_result():
    cs = ChannelStore(size=3)
    # scale within 0..1; large raw sum should clamp only at final stage
    cs.configure_processors(
        {
            "aggregate": [
                {
                    "channels": [
                        {"id": 1, "value": 1.0},
                        {"id": 2, "value": 1.0},
                        {"id": 3, "value": 1.0},
                    ]
                }
            ]
        }
    )
    cs.set_many({1: 0.7, 2: 0.6, 3: 0.9})  # abs sum = 2.2 -> clamp to 1.0
    snap = cs.snapshot()
    # written into first source channel (1)
    assert snap[0] == 1.0

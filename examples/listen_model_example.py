"""
Example: Using the Model.listen() method to monitor input events.

This demonstrates how to use the async listen() method to debug and monitor
all input events for a model configuration.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import pi_tx
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable DEBUG logging to see input events
from pi_tx.logging_config import init_logging

init_logging(level="DEBUG")

from pi_tx.domain.models import (
    Model,
    Channel,
    Endpoint,
    VirtualControl,
)
from pi_tx.input.mappings.stick_mapping import (
    left_stick,
    right_stick,
    ControlType,
)


# Create a simple test model
test_model = Model(
    name="listen_test",
    model_id="test-model-listen-example",
    rx_num=1,
    channels=[
        Channel(
            name="left_y",
            control=left_stick.axes.stick_y,
            reversed=True,
        ),
        Channel(
            name="left_x",
            control=left_stick.axes.stick_x,
        ),
        Channel(
            name="throttle",
            control=left_stick.axes.throttle,
        ),
        Channel(
            name="trigger",
            control=left_stick.buttons.trigger,
        ),
        Channel(
            name="right_y",
            control=right_stick.axes.stick_y,
        ),
        Channel(
            name="right_x",
            control=right_stick.axes.stick_x,
        ),
    ],
)


async def main():
    print(f"Model: {test_model.name}")
    print(f"Channels: {len(test_model.channels)}")
    print()
    print("Channels configured:")
    for ch in test_model.channels:
        print(f"  {ch.name}: {ch.control.name}")
        if ch.reversed:
            print(f"        Reversed: Yes")
    print()
    print("=" * 60)
    print("Starting to listen for input events...")
    print("Move joysticks and press buttons to see debug output")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        # Listen for 30 seconds (or until Ctrl+C)
        await test_model.listen(duration=30)
    except KeyboardInterrupt:
        print("\nStopped by user")


if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nStopped by user")

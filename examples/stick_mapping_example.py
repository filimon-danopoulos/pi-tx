"""
Example: Using the static stick mapping.

This demonstrates how to use the new class-based stick mapping with
full autocomplete support.
"""

from pi_tx.input.mappings.stick_mapping import left_stick, right_stick


def main():
    print("Static Stick Mapping Usage Example")
    print("=" * 60)
    print()

    # Access controls with full autocomplete support
    print("1. Accessing axis controls:")
    print(f"   left_stick.axes.stick_y = {left_stick.axes.stick_y.name}")
    print(f"   Event code: {left_stick.axes.stick_y.event_code}")
    print(f"   Type: {left_stick.axes.stick_y.control_type.value}")
    print()

    print("2. Accessing button controls:")
    print(f"   left_stick.buttons.trigger = {left_stick.buttons.trigger.name}")
    print(f"   Event code: {left_stick.buttons.trigger.event_code}")
    print()

    print("3. Normalizing axis values:")
    test_values = [0, 4096, 8192, 12288, 16383]
    for raw in test_values:
        normalized = left_stick.axes.stick_y.normalize(raw)
        print(f"   Raw {raw:5d} -> Normalized {normalized:6.3f}")
    print()

    print("4. All available axes on left stick:")
    for attr in dir(left_stick.axes):
        if not attr.startswith("_"):
            axis = getattr(left_stick.axes, attr)
            if hasattr(axis, "name"):
                print(f"   left_stick.axes.{attr} -> {axis.name}")
    print()

    print("5. All available buttons on left stick:")
    for attr in dir(left_stick.buttons):
        if not attr.startswith("_"):
            button = getattr(left_stick.buttons, attr)
            if hasattr(button, "name"):
                print(f"   left_stick.buttons.{attr} -> {button.name}")
    print()

    print("6. Comparing left and right sticks:")
    print(f"   Left throttle: {left_stick.axes.throttle.name}")
    print(f"   Right throttle: {right_stick.axes.throttle.name}")
    print()

    print("Benefits:")
    print("  ✓ Full IDE autocomplete support")
    print("  ✓ Type-safe - no typos in control names")
    print("  ✓ Self-documenting - just type '.' to see all controls")
    print("  ✓ Easy refactoring - rename propagates everywhere")
    print("  ✓ No dictionary lookups needed")


if __name__ == "__main__":
    main()

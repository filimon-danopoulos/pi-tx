#!/usr/bin/env bash

# Script to run pi-tx with debug UART enabled
# This allows you to test UART functionality without real hardware

echo "Starting pi-tx with debug UART interface..."
echo "This will capture and display UART frames without needing real hardware."
echo ""

export PI_TX_DEBUG_UART=1
export PI_TX_UART_VERBOSE=1  # Enable verbose frame logging
export PI_TX_UART_TRACE=0    # Enable detailed error tracing if needed

# Run the application
cd "$(dirname "$0")"
.venv/bin/python -m pi_tx

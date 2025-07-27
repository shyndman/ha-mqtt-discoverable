#!/bin/bash

# Test script for ha-mqtt-discoverable
# Starts mosquitto MQTT broker, runs tests, and cleans up

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Variables
MOSQUITTO_PID=""
MOSQUITTO_CONFIG="tests/mosquitto.conf"
MQTT_PORT=1883
TEST_TIMEOUT=120  # 2 minutes timeout for tests

# Cleanup function
cleanup() {
    if [ -n "$MOSQUITTO_PID" ]; then
        print_status "Stopping mosquitto (PID: $MOSQUITTO_PID)..."
        kill $MOSQUITTO_PID 2>/dev/null || true
        wait $MOSQUITTO_PID 2>/dev/null || true
        print_status "Mosquitto stopped"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Check if mosquitto is available
if ! command -v mosquitto &> /dev/null; then
    print_error "mosquitto command not found. Please install mosquitto broker."
    print_error "  Ubuntu/Debian: sudo apt-get install mosquitto"
    print_error "  macOS: brew install mosquitto"
    print_error "  Other: Check your package manager or visit https://mosquitto.org/"
    exit 1
fi

# Check if config file exists
if [ ! -f "$MOSQUITTO_CONFIG" ]; then
    print_error "Mosquitto config file not found: $MOSQUITTO_CONFIG"
    exit 1
fi

# Check if port is already in use
if lsof -Pi :$MQTT_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_error "Port $MQTT_PORT is already in use. Please stop any running MQTT brokers."
    exit 1
fi

print_status "Starting mosquitto MQTT broker..."
print_status "Config: $MOSQUITTO_CONFIG"
print_status "Port: $MQTT_PORT"

# Start mosquitto in background
mosquitto -c "$MOSQUITTO_CONFIG" -d
if [ $? -ne 0 ]; then
    print_error "Failed to start mosquitto"
    exit 1
fi

# Wait a moment for mosquitto to start
sleep 2

# Find mosquitto PID
MOSQUITTO_PID=$(pgrep -f "mosquitto.*$MOSQUITTO_CONFIG" | head -1)
if [ -z "$MOSQUITTO_PID" ]; then
    print_error "Could not find mosquitto process"
    exit 1
fi

print_status "Mosquitto started with PID: $MOSQUITTO_PID"

# Verify mosquitto is responding
print_status "Verifying mosquitto is responding..."
timeout 5 bash -c "echo 'test' | mosquitto_pub -h localhost -p $MQTT_PORT -t test/topic -l" 2>/dev/null
if [ $? -ne 0 ]; then
    print_warning "Could not verify mosquitto connectivity (mosquitto_pub not available or connection failed)"
    print_warning "Continuing with tests anyway..."
fi

# Run the tests
print_status "Running tests..."
print_status "Test timeout: ${TEST_TIMEOUT}s"

# Use timeout to prevent tests from hanging indefinitely
timeout $TEST_TIMEOUT poetry run pytest "$@"
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_status "All tests passed! ✅"
elif [ $TEST_EXIT_CODE -eq 124 ]; then
    print_error "Tests timed out after ${TEST_TIMEOUT}s"
    exit 1
else
    print_error "Tests failed with exit code: $TEST_EXIT_CODE"
    exit $TEST_EXIT_CODE
fi

print_status "Test run completed successfully"
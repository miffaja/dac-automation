#!/usr/bin/env bash
# =============================================================================
# Equium Miner - Single Instance Launcher with Auto-Restart
# =============================================================================
# Enhanced launcher script for the Equium CLI miner. Provides:
#   - Auto-build if binary not found
#   - Auto-restart on crash with exponential backoff
#   - Log output to file with timestamps
#   - Clean shutdown on Ctrl+C
#
# For multi-instance mining, use enhanced_miner.py instead.
#
# Usage:
#   ./run_miner.sh
#   EQUIUM_RPC_URL=https://my-rpc.com ./run_miner.sh
# =============================================================================

set -uo pipefail

# Load config.env if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/config.env" ]; then
    # shellcheck disable=SC1091
    set -a
    source "$SCRIPT_DIR/config.env"
    set +a
fi

# Configuration (from env or defaults)
RPC_URL="${EQUIUM_RPC_URL:-https://api.mainnet-beta.solana.com}"
KEYPAIR_PATH="${EQUIUM_KEYPAIR_PATH:-$HOME/.config/solana/id.json}"
MAX_NONCES="${EQUIUM_MAX_NONCES:-65536}"
CU_LIMIT="${EQUIUM_CU_LIMIT:-1400000}"
SOURCE_DIR="${EQUIUM_SOURCE_DIR:-/projects/sandbox/equium}"
BINARY_PATH="${EQUIUM_BINARY_PATH:-$SOURCE_DIR/target/release/equium-miner}"
AUTO_RESTART="${EQUIUM_AUTO_RESTART:-true}"
RESTART_DELAY="${EQUIUM_RESTART_DELAY_SECS:-3}"
MAX_RESTART_DELAY="${EQUIUM_MAX_RESTART_DELAY_SECS:-60}"
LOG_DIR="${EQUIUM_LOG_DIR:-$SCRIPT_DIR/logs}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# State
CURRENT_DELAY=$RESTART_DELAY
RESTART_COUNT=0
CHILD_PID=""

# Create log directory
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/miner_$(date +%Y%m%d_%H%M%S).log"

# Cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down miner...${NC}"
    if [ -n "$CHILD_PID" ] && kill -0 "$CHILD_PID" 2>/dev/null; then
        kill -TERM "$CHILD_PID" 2>/dev/null
        wait "$CHILD_PID" 2>/dev/null
    fi
    echo -e "${GREEN}Miner stopped. Restarts: $RESTART_COUNT${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Build if binary not found
ensure_binary() {
    if [ -x "$BINARY_PATH" ]; then
        return 0
    fi
    echo -e "${YELLOW}Binary not found at $BINARY_PATH${NC}"
    echo -e "${CYAN}Building from source...${NC}"
    
    if [ ! -d "$SOURCE_DIR" ]; then
        echo -e "${RED}ERROR: Source directory not found: $SOURCE_DIR${NC}"
        exit 1
    fi
    
    export RUSTFLAGS="${RUSTFLAGS:-} -C target-cpu=native"
    cargo build \
        --manifest-path "$SOURCE_DIR/Cargo.toml" \
        -p equium-cli-miner \
        --release
    
    if [ ! -x "$BINARY_PATH" ]; then
        echo -e "${RED}ERROR: Build completed but binary not found at $BINARY_PATH${NC}"
        exit 1
    fi
    echo -e "${GREEN}Build successful!${NC}"
}

# Run miner once
run_miner() {
    echo -e "${CYAN}Starting equium-miner...${NC}"
    echo -e "  RPC:       $RPC_URL"
    echo -e "  Keypair:   $KEYPAIR_PATH"
    echo -e "  Max Nonces: $MAX_NONCES"
    echo -e "  CU Limit:  $CU_LIMIT"
    echo -e "  Log:       $LOG_FILE"
    echo ""
    
    "$BINARY_PATH" \
        --rpc-url "$RPC_URL" \
        --keypair "$KEYPAIR_PATH" \
        --max-nonces-per-round "$MAX_NONCES" \
        --cu-limit "$CU_LIMIT" \
        2>&1 | tee -a "$LOG_FILE" &
    
    CHILD_PID=$!
    wait "$CHILD_PID"
    local exit_code=$?
    CHILD_PID=""
    return $exit_code
}

# Main loop
main() {
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  Equium Miner - Single Instance Launcher${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    
    ensure_binary
    
    while true; do
        run_miner
        local exit_code=$?
        
        if [ "$AUTO_RESTART" != "true" ]; then
            echo -e "${YELLOW}Miner exited with code $exit_code. Auto-restart disabled.${NC}"
            break
        fi
        
        RESTART_COUNT=$((RESTART_COUNT + 1))
        echo ""
        echo -e "${YELLOW}Miner exited (code $exit_code). Restart #$RESTART_COUNT in ${CURRENT_DELAY}s...${NC}"
        
        # Interruptible sleep
        sleep "$CURRENT_DELAY" &
        wait $!
        
        # Exponential backoff
        CURRENT_DELAY=$(echo "$CURRENT_DELAY * 2" | bc)
        if (( $(echo "$CURRENT_DELAY > $MAX_RESTART_DELAY" | bc -l) )); then
            CURRENT_DELAY=$MAX_RESTART_DELAY
        fi
    done
}

main

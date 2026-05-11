#!/usr/bin/env bash
# =============================================================================
# Equium Miner - Optimized Build Script
# =============================================================================
# Builds the Rust equium-miner binary with maximum performance optimizations.
#
# Usage:
#   ./build.sh                    # Build with defaults
#   ./build.sh --clean            # Clean build (removes target/release first)
#   EQUIUM_SOURCE_DIR=/path ./build.sh  # Custom source dir
#
# Optimizations applied:
#   - LTO (Link-Time Optimization): fat
#   - codegen-units=1: better optimization at cost of compile time
#   - target-cpu=native: use all CPU features (AVX2, etc.)
#   - opt-level=3: maximum optimization
#   - overflow-checks=true: safety preserved (required by on-chain verifier)
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
EQUIUM_SOURCE_DIR="${EQUIUM_SOURCE_DIR:-/projects/sandbox/equium}"
BINARY_NAME="equium-miner"
PACKAGE_NAME="equium-cli-miner"
CLEAN_BUILD=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--clean] [--help]"
            echo ""
            echo "Environment variables:"
            echo "  EQUIUM_SOURCE_DIR  Path to equium source (default: /projects/sandbox/equium)"
            exit 0
            ;;
    esac
done

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  Equium Miner - Optimized Build${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# Verify source directory
if [ ! -d "$EQUIUM_SOURCE_DIR" ]; then
    echo -e "${RED}ERROR: Source directory not found: $EQUIUM_SOURCE_DIR${NC}"
    echo "Set EQUIUM_SOURCE_DIR to the equium repository path."
    exit 1
fi

if [ ! -f "$EQUIUM_SOURCE_DIR/Cargo.toml" ]; then
    echo -e "${RED}ERROR: No Cargo.toml in $EQUIUM_SOURCE_DIR${NC}"
    exit 1
fi

# Verify Rust toolchain
if ! command -v cargo &> /dev/null; then
    echo -e "${RED}ERROR: cargo not found. Install Rust: https://rustup.rs${NC}"
    exit 1
fi

echo -e "${GREEN}Source:${NC}  $EQUIUM_SOURCE_DIR"
echo -e "${GREEN}Rust:${NC}    $(rustc --version 2>/dev/null || echo 'unknown')"
echo -e "${GREEN}Cargo:${NC}   $(cargo --version 2>/dev/null || echo 'unknown')"
echo ""

# Clean if requested
if [ "$CLEAN_BUILD" = true ]; then
    echo -e "${YELLOW}Cleaning previous build...${NC}"
    cargo clean --manifest-path "$EQUIUM_SOURCE_DIR/Cargo.toml" --release 2>/dev/null || true
fi

# Set RUSTFLAGS for native CPU optimization
export RUSTFLAGS="${RUSTFLAGS:-} -C target-cpu=native"
echo -e "${GREEN}RUSTFLAGS:${NC} $RUSTFLAGS"
echo ""

# Build
echo -e "${CYAN}Building $PACKAGE_NAME (release)...${NC}"
echo "This may take several minutes on first build."
echo ""

BUILD_START=$(date +%s)

cargo build \
    --manifest-path "$EQUIUM_SOURCE_DIR/Cargo.toml" \
    -p "$PACKAGE_NAME" \
    --release \
    2>&1 | tee /tmp/equium-build.log

BUILD_END=$(date +%s)
BUILD_TIME=$((BUILD_END - BUILD_START))

# Verify binary
BINARY_PATH="$EQUIUM_SOURCE_DIR/target/release/$BINARY_NAME"
if [ ! -f "$BINARY_PATH" ]; then
    echo ""
    echo -e "${RED}ERROR: Binary not found at expected path: $BINARY_PATH${NC}"
    echo "Build log: /tmp/equium-build.log"
    exit 1
fi

# Print results
BINARY_SIZE=$(du -h "$BINARY_PATH" | cut -f1)
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  BUILD SUCCESSFUL${NC}"
echo -e "${GREEN}================================================${NC}"
echo -e "  Binary:     ${CYAN}$BINARY_PATH${NC}"
echo -e "  Size:       $BINARY_SIZE"
echo -e "  Build time: ${BUILD_TIME}s"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Run the miner:"
echo "  $BINARY_PATH --rpc-url YOUR_RPC --keypair ~/.config/solana/id.json"
echo ""
echo "Or use the enhanced orchestrator:"
echo "  python3 enhanced_miner.py --binary $BINARY_PATH"

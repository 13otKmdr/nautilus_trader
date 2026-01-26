# CLAUDE.md

This file provides guidance for AI assistants working with the NautilusTrader codebase.

## Project Overview

NautilusTrader is a high-performance, production-grade algorithmic trading platform for backtesting
and live trading. It uses a hybrid architecture with:

- **Rust** for core performance-critical components
- **Cython** for Python/C interop and some domain logic
- **Python** for the user-facing API and strategy development

The platform is AI-first, event-driven, and asset-class agnostic, supporting FX, Equities, Futures,
Options, Crypto (CEX/DEX), and Betting markets.

## Repository Structure

```
nautilus_trader/
├── crates/                    # Rust workspace with core crates
│   ├── adapters/              # Exchange/venue adapter implementations
│   │   ├── binance/
│   │   ├── bybit/
│   │   ├── databento/
│   │   └── ...
│   ├── core/                  # Core types: time, UUID, correctness
│   ├── model/                 # Domain model: orders, positions, instruments
│   ├── common/                # Shared utilities, logging, actors
│   ├── data/                  # Data engine and aggregation
│   ├── execution/             # Execution engine
│   ├── backtest/              # Backtesting engine
│   ├── live/                  # Live trading engine
│   ├── persistence/           # Data persistence (Parquet, catalog)
│   ├── infrastructure/        # Redis, PostgreSQL integrations
│   ├── network/               # HTTP, WebSocket clients
│   ├── serialization/         # JSON, MessagePack, Cap'n Proto
│   ├── pyo3/                  # PyO3 Python bindings
│   └── ...
├── nautilus_trader/           # Python package
│   ├── adapters/              # Python adapter wrappers
│   ├── backtest/              # Backtesting components
│   ├── cache/                 # Caching layer
│   ├── common/                # Common utilities
│   ├── core/                  # Core Python/Cython modules
│   ├── data/                  # Data handling
│   ├── execution/             # Execution handling
│   ├── indicators/            # Technical indicators (Cython)
│   ├── live/                  # Live trading components
│   ├── model/                 # Domain model Python bindings
│   ├── persistence/           # Persistence layer
│   ├── portfolio/             # Portfolio management
│   ├── risk/                  # Risk management
│   ├── serialization/         # Serialization utilities
│   ├── system/                # System kernel
│   ├── test_kit/              # Testing utilities
│   └── trading/               # Trading strategies
├── tests/                     # Test suite
│   ├── unit_tests/
│   ├── integration_tests/
│   ├── acceptance_tests/
│   ├── performance_tests/
│   └── test_data/
├── examples/                  # Example backtests and live trading
│   ├── backtest/
│   └── live/
├── docs/                      # Documentation source
├── schema/                    # SQL schemas for PostgreSQL
└── scripts/                   # Build and utility scripts
```

## Build System

### Prerequisites

- **Rust**: 1.92.0+ (latest stable)
- **Python**: 3.12-3.14
- **Clang**: Required for compilation
- **uv**: Recommended package manager

### Key Build Commands

```bash
# Install with all dependencies (release mode)
make install

# Build in debug mode (faster, recommended for development)
make build-debug

# Build in release mode
make build

# Clean build artifacts
make clean
```

### Environment Variables

- `BUILD_MODE`: `debug`, `release`, or `debug-pyo3`
- `HIGH_PRECISION`: `true` (default) for 128-bit precision, `false` for 64-bit
- `PARALLEL_BUILD`: `true` (default) for parallel compilation

## Testing

### Python Tests

```bash
# Run all Python tests with pytest
make pytest

# Run with parallel execution
uv run pytest --new-first --failed-first -n logical
```

### Rust Tests

```bash
# Run all Rust tests with cargo-nextest
make cargo-test

# Run tests for a specific crate
make cargo-test-crate-nautilus-model

# Run with extra features (capnp, hypersync)
make cargo-test-extras
```

### Test Organization

- Unit tests: `tests/unit_tests/`
- Integration tests: `tests/integration_tests/`
- Performance tests: `tests/performance_tests/`
- Rust tests: Located within each crate in `crates/*/src/`

## Code Quality

### Pre-commit Hooks

Pre-commit is mandatory. Install with:

```bash
pip install pre-commit
pre-commit install
```

### Formatting

```bash
# Format all code (Rust + Python)
make format

# Rust only (requires nightly)
cargo +nightly fmt

# Python only
uv run ruff format .
```

### Linting

```bash
# Run all checks (clippy + ruff)
make check-code

# Clippy with auto-fix
make clippy-fix

# Ruff with auto-fix
make ruff
```

### Pre-flight Checks

Before submitting PRs:

```bash
make pre-flight  # Runs format, check-code, cargo-test, build-debug, pytest
```

## Coding Conventions

### File Headers

All source files must include the copyright header:

**Rust:**
```rust
// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  ...
// -------------------------------------------------------------------------------------------------
```

**Python/Cython:**
```python
# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  ...
# -------------------------------------------------------------------------------------------------
```

### Rust Conventions

- **Edition**: Rust 2024
- **Formatting**: Use `cargo +nightly fmt` (nightly required for `group_imports`)
- **Imports**: Group by std, external crates, then internal (`imports_granularity = "Crate"`)
- **Error handling**: Use `anyhow` for applications, `thiserror` for libraries
- **Lint level**: Workspace lints defined in `Cargo.toml` under `[workspace.lints.clippy]`
- **PyO3 naming**: Follow PyO3 conventions for Python bindings
- **Testing**: Use `rstest` for fixtures, tests in same file under `#[cfg(test)]`
- **Cognitive complexity**: Maximum 10 (enforced by clippy)

### Python Conventions

- **Target version**: Python 3.12+
- **Line length**: 100 characters
- **Formatter**: Ruff (configured in `pyproject.toml`)
- **Linter**: Ruff with extensive rule set including flake8-bugbear, perflint, etc.
- **Type hints**: Required, mypy enforced
- **Imports**: Single-line imports, sorted by isort/ruff

### Naming Conventions

- Rust: `snake_case` for functions/variables, `PascalCase` for types
- Python: `snake_case` for functions/variables, `PascalCase` for classes
- Constants: `SCREAMING_SNAKE_CASE`
- Error variables: Must follow naming conventions (enforced by pre-commit)

## Architecture Patterns

### Domain Model

The domain model (`crates/model`, `nautilus_trader/model`) is:

- Asset-class agnostic
- Type-safe with strong typing
- Immutable where possible
- Serializable (JSON, MessagePack, Cap'n Proto)

Key domain types:

- `Instrument`: Trading instruments (equities, futures, options, crypto)
- `Order`: Order representations with full lifecycle
- `Position`: Position tracking with P&L
- `Bar`, `QuoteTick`, `TradeTick`: Market data types
- `AccountId`, `InstrumentId`, etc.: Strongly-typed identifiers

### Event-Driven Architecture

- Components communicate via message bus
- Events are immutable
- Actors process events asynchronously
- Cache provides fast state access

### Adapter Pattern

Exchange integrations follow the adapter pattern:

- Each adapter in `crates/adapters/` and `nautilus_trader/adapters/`
- Implements common interfaces for data/execution
- Translates venue API to normalized domain model

## Feature Flags (Rust)

Common feature flags across crates:

- `ffi`: C FFI bindings via cbindgen
- `python`: PyO3 Python bindings
- `high-precision`: 128-bit value types (default on Linux/macOS)
- `defi`: DeFi domain model extensions
- `stubs`: Test stubs and fixtures

## Documentation

- User docs: https://nautilustrader.io/docs/
- Build docs locally: `make docs`
- Rust docs: `make docs-rust`
- Python API docs: `make docs-python`

### Documentation style

- Headings H2 and below use sentence case
- Follow existing patterns in `docs/` directory

## Contributing Guidelines

1. Open an issue first for discussion
2. Fork the `develop` branch
3. Install pre-commit hooks
4. Follow coding conventions
5. Include tests for new functionality
6. Run `make pre-flight` before submitting PR
7. Target PRs to `develop` branch

### Branch Strategy

- `master`: Latest stable release
- `nightly`: Daily snapshots from develop
- `develop`: Active development (PR target)

## Key Dependencies

### Rust

- `tokio`: Async runtime
- `serde`: Serialization
- `pyo3`: Python bindings
- `reqwest`: HTTP client
- `tokio-tungstenite`: WebSocket client
- `arrow`/`parquet`: Data formats
- `redis`: Redis client
- `sqlx`: PostgreSQL client

### Python

- `numpy`, `pandas`: Data handling
- `pyarrow`: Arrow/Parquet support
- `msgspec`: Fast serialization
- `uvloop`: Fast event loop (Unix)

## Troubleshooting

### Build Issues

- Ensure Rust toolchain is up to date: `rustup update`
- Clean build: `make clean && make build-debug`
- Check clang is installed: `clang --version`

### Test Issues

- Set `PYTHONHOME` for Rust tests with uv-installed Python
- For infrastructure tests, run: `make init-services`

### Windows Notes

- High-precision mode not supported (uses 64-bit)
- Requires Visual Studio Build Tools with Clang

## Quick Reference

| Task | Command |
|------|---------|
| Install dependencies | `make install-just-deps` |
| Build (debug) | `make build-debug` |
| Build (release) | `make build` |
| Run Python tests | `make pytest` |
| Run Rust tests | `make cargo-test` |
| Format code | `make format` |
| Lint code | `make check-code` |
| Pre-commit checks | `make pre-commit` |
| Full pre-flight | `make pre-flight` |
| Clean all | `make clean` |
| Show all targets | `make help` |

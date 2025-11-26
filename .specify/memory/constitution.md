<!-- 
  SYNC IMPACT REPORT: Constitution v1.0.0 INITIAL
  ================================================
  Version change: TEMPLATE → 1.0.0 (Initial constitution)
  Modified principles: N/A (initial adoption)
  Added sections: All
  Removed sections: N/A
  Templates updated:
    - ✅ .specify/templates/plan-template.md (Constitution Check section exists)
    - ✅ .specify/templates/spec-template.md (aligned)
    - ✅ .specify/templates/tasks-template.md (aligned)
  Follow-up TODOs: None
-->

# RF Impedance Matching Tool Constitution

## Core Principles

### I. Pythonic & Pragmatic

Write code that is clear, maintainable, and follows Python idioms. Avoid overengineering solutions; prioritize simplicity and directness. Use built-in Python features and standard library when practical; minimize external dependencies. Code MUST be readable and testable above all else.

### II. Test-Driven Development (NON-NEGOTIABLE)

Tests MUST be written before implementation. Follow Red-Green-Refactor cycle strictly: (1) Write failing test, (2) Get user approval on test intent, (3) Implement minimal code to pass, (4) Refactor. All features require unit test coverage with clear acceptance criteria. No code merges without passing tests.

### III. Independently Testable Features

Every user-facing feature MUST be independently deployable and testable. If only ONE feature is implemented, it must still deliver measurable value. Features are organized as discrete user stories with explicit acceptance scenarios; each story can be tested and validated in isolation.

### IV. Minimal Viable Product (MVP) Focus

Start with the smallest viable implementation that solves the core problem. Use YAGNI (You Aren't Gonna Need It) principle: do not add speculative features. Add complexity only when justified by explicit requirements or user feedback. Keep scope tight and iterate.

### V. Observability & Debuggability

All components MUST support debugging and monitoring. Text I/O protocols (stdin/args → stdout) ensure clarity. Structured logging required for any runtime decisions. Error messages MUST be actionable; include context (not just "Error: failed"). Support both human-readable and JSON output formats where applicable.

## Technical Constraints

**Language & Platform**: Python 3.9+ (or latest stable) | Target: Linux/macOS/Windows CLI compatibility  
**Dependencies**: Minimize external packages; justify each dependency with rationale  
**Testing Framework**: pytest (or equivalent Python standard)  
**Type Hints**: MUST use type hints on all public functions (Python 3.9+) for clarity and maintainability  
**Performance**: Optimize for correctness first, performance second; document any performance-critical sections  
**Code Style**: Follow PEP 8; enforce via linter (e.g., flake8, black) in CI/CD

## Development Workflow

1. **Planning Phase**: Create feature specification with user stories, acceptance scenarios, and success criteria.
2. **Design Phase**: Validate compliance with this constitution; document any justified deviations in Implementation Plan.
3. **Implementation Phase**: TDD mandatory; write tests first, get approval, implement, refactor. Code review required before merge.
4. **Testing Phase**: Unit tests + integration tests required for contract changes or cross-component communication. 100% coverage on new code; document exclusions.
5. **Review Gates**: All PRs must verify compliance with constitution principles; use checklists to enforce.

## Governance

This constitution supersedes all other practices in this project. All design decisions, architectural choices, and code reviews MUST verify compliance against these principles.

**Amendment Process**: 
- Breaking changes to principles (removal/redefinition) require major version bump and team consensus.
- New principles or material expansions require minor version bump and documentation in commit.
- Clarifications/wording fixes require patch version bump.

**Compliance Review**: Constitution Check section in all Implementation Plans (`.specify/templates/plan-template.md`) MUST be completed before Phase 0 research begins. Any violations MUST be explicitly justified and tracked.

**Guidance**: Refer to `.specify/templates/` for runtime development guidance; all templates align with this constitution.

**Version**: 1.0.0 | **Ratified**: 2025-11-26 | **Last Amended**: 2025-11-26

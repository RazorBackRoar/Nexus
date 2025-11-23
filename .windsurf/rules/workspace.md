---
trigger: always_on
---

# Comprehensive AI Development Standards

## Fundamental Philosophy

- KISS (Keep It Simple, Stupid): Write the simplest solution that works
- DRY (Don't Repeat Yourself): Extract common functionality, avoid duplication
- YAGNI (You Aren't Gonna Need It): Don't build features until actually needed
- Simplicity First: Choose the simplest solution over complex alternatives
- Readability Priority: Code must be clear and understandable to any developer

## SOLID Principles

- Single Responsibility: Each class/function has one job
- Open/Closed: Open for extension, closed for modification
- Liskov Substitution: Subtypes must be substitutable for base types
- Interface Segregation: Many specific interfaces over one general
- Dependency Inversion: Depend on abstractions, not concretions

## Development Standards

### Core Standards

- Dependency Minimalism: No new libraries without approval
- Industry Standards: Follow conventions for the language/framework
- Strategic Documentation: Only comment on complex or critical code
- Test-Driven Thinking: Design code to be easily testable
- Consistent Naming: Use meaningful, descriptive, and consistent names
- Modularity: Break code into small, reusable functions and components
- Security: Follow safe coding practices and validate all inputs
- Performance: Optimize for efficiency and responsiveness
- Shell Robustness: Always use set -euo pipefail for strict error handling
- Path Safety: Quote all variables and use proper path expansion
- Terminal Integration: Design for seamless drag & drop workflows
- User Feedback: Provide clear progress indicators and notifications
- Atomic Operations: Ensure file operations complete fully or rollback
- Signal Handling: Trap interrupts and cleanup properly on exit
- Resource Cleanup: Always cleanup temporary files and processes
- Idempotency: Operations should be safely repeatable

### Global AI Programming Rules

- Fail Fast: Detect and report errors as early as possible in the development cycle
- Principle of Least Surprise: Code behavior should match developer expectations
- Separation of Concerns: Keep different aspects of the program isolated from each other
- Composition Over Inheritance: Favor object composition over class inheritance
- Explicit is Better Than Implicit: Code should be self-documenting and obvious
- Single Source of Truth: Each piece of knowledge should have one authoritative representation
- Defensive Programming: Assume inputs are invalid and external systems will fail
- Progressive Enhancement: Build core functionality first, then add advanced features
- Immutability Preference: Favor immutable data structures when possible
- Stateless Design: Minimize shared mutable state between components
- Twelve-Factor App: Follow cloud-native application development principles

### Workflow Standards

- Atomic Changes (AC): Make small, self-contained modifications to improve traceability and rollback capability
- Commit Discipline (CD): Recommend regular commits with semantic messages using conventional commit format
- Transparent Reasoning (TR): When generating code, explicitly reference which global rules influenced decisions
- Context Window Management (CWM): Be mindful of AI context limitations. Suggest new sessions when necessary
- Preserve Existing Code (PEC): Must not overwrite or break functional code unless explicitly instructed otherwise
- Code Smell Detection (CSD): Proactively identify and suggest refactoring for functions exceeding 30 lines, files exceeding 300 lines, nested conditionals beyond 2 levels, classes with more than 5 public methods
- Minimal Changes Focus: Make only changes related to current dialog, respecting existing code style and understanding codebase before suggesting modifications

### Code Quality Guarantees

- DRY Principle (DRY): No duplicate code. Reuse or extend existing functionality
- Clean Architecture (CA): Generate cleanly formatted, logically structured code with consistent patterns
- Robust Error Handling (REH): Integrate appropriate error handling for all edge cases and external interactions with clear, actionable error messages
- Input Validation (IV): All external data must be validated before processing
- Resource Management (RM): Close connections and free resources appropriately
- Constants Over Magic Values (CMV): No magic strings or numbers. Use named constants
- Security-First Thinking (SFT): Implement proper authentication, authorization, and data protection
- Performance Awareness (PA): Consider computational complexity and resource usage

## Programming Style Standards

- Prefer functional programming over OOP
- Use separate OOP classes only for connectors and interfaces to external systems
- Write all other logic with pure functions (clear input/output, no hidden state changes)
- Functions must ONLY modify their return values - never modify input parameters, global state, or any data not explicitly returned
- Make minimal, focused changes
- Follow DRY, KISS, and YAGNI principles
- Use strict typing (function returns, variables) in all languages
- Use named parameters in function calls when possible
- Avoid unnecessary wrapper functions without clear purpose
- Prefer strongly-typed collections over generic ones when dealing with complex data structures
- Consider creating proper type definitions for non-trivial data structures
- Never use default parameter values in function definitions - make all parameters explicit

## Technology-Specific Implementation

### zsh Scripting Excellence

#### Shell Script Template

```zsh
#!/usr/bin/env zsh

set -euo pipefail
setopt EXTENDED_GLOB NULL_GLOB

# Better error trap for zsh
trap 'print -ru2 "Error on line $LINENO: $funcfiletrace"' ZERR

# Cleanup on exit/signals
cleanup() {
  [[ -n "${TMPFILE:-}" && -e "$TMPFILE" ]] && rm -f -- "$TMPFILE"
}
trap cleanup INT TERM EXIT

# Unescape, absolutize, and canonicalize a path
sanitize_path() {
  emulate -L zsh -o pipefail
  local raw="$1"
  [[ -z "${raw:-}" ]] && { print -ru2 "Error: Path required"; return 1; }
  local cleaned=${(Q)raw}      # remove quotes/escapes
  cleaned=${cleaned:A}         # absolute path
  # Optional physical canonicalization (resolves symlinks if exists)
  [[ -e $cleaned ]] && cleaned=${cleaned:P}
  print -r -- "$cleaned"
}
```

#### zsh-Specific Best Practices

- Use ZERR trap instead of ERR for zsh error handling
- Use `${(Q)}` parameter expansion for unquoting escaped strings
- Use `--` in rm commands to handle filenames starting with dashes
- Use autoload for function libraries and lazy loading to improve startup performance
- Leverage zsh's associative arrays for complex data structures
- Implement completion functions for custom commands
- Use zsh's built-in parameter modifiers: :h, :t, :r, :e for path manipulation
- Take advantage of recursive globbing \*\* and qualifiers (N)
- Always use `local` for function variables to prevent global scope pollution
- Use `emulate -L zsh` in functions to ensure consistent behavior regardless of user settings
- Validate file existence with `[[ -e "$file" ]]` before operations to prevent errors
- Use `${var:?error message}` for required parameter validation with descriptive errors
- Handle array expansion safely with `"${array[@]}"` to preserve whitespace and special characters

### macOS Integration Excellence

#### macOS Version Handling

```zsh
get_macos_version() {
  emulate -L zsh
  local version
  version=$(sw_vers -productVersion)
  local major=${version%%.*}
  local minor=${version#*.}
  minor=${minor%%.*}
  print -r -- "${major}.${minor}"
}

# Usage example
macos_version=$(get_macos_version)
case $macos_version in
  14.*|15.*) echo "Sonoma/Sequoia features available" ;;
  13.*) echo "Ventura compatibility mode" ;;
  *) echo "Legacy macOS version" ;;
esac
```

#### macOS File System Considerations

- Respect macOS file naming conventions and length limits (255 chars)
- Handle case-insensitive but case-preserving file system (HFS+/APFS)
- Handle special directories (.DS_Store, .localized, etc.)
- Skip system files automatically in batch operations
- Preserve file creation/modification dates during renames
- Handle App Bundle directories (.app) as single entities, not individual files
- Check and remove quarantine attributes from downloaded files using xattr
- Use mdfind for Spotlight-based file searching instead of find when appropriate
- Validate Xcode Command Line Tools availability with xcode-select --print-path
- Handle different macOS version behaviors using sw_vers for version detection
- Use Homebrew paths when available: $(brew --prefix)/bin takes precedence

#### App Bundle Handling

- Treat .app directories as single entities using `-d` test
- Use `open -a AppName` instead of direct .app path manipulation
- Check app bundle validity with `mdls -name kMDItemContentType app.app`
- Handle app bundle resources in Contents/Resources/
- Respect app bundle structure when processing

### Approved Tools & Performance

#### Performance & Security

- Atomic Operations: Use temporary files and atomic moves
- Progress Indicators with meaningful feedback for long operations
- Validate all drag & drop inputs before processing
- Permission Checks before attempting file operations
- System File Protection - automatically skip protected files
- Secure Defaults - fail safe, require explicit confirmation
- Cleanup Handlers - always cleanup on script exit/interrupt

## Quality Validation

### Before Coding

- Is this the simplest solution that works?
- Does it follow DRY principles?
- Is it actually needed (YAGNI)?
- Are all inputs validated?
- Is error handling implemented?

### Code Quality

- Consistent naming conventions
- No code duplication
- Modular, reusable components
- Security considerations addressed

### zsh & Terminal Specific

- Uses set -euo pipefail for strict error handling
- Uses ZERR trap instead of ERR for zsh-specific error handling
- Uses emulate -L zsh inside functions to localize shell behavior
- Uses zsh parameter expansion ${(Q)} for proper unquoting
- Uses zsh path modifiers :A and :P for path canonicalization
- Quotes all variables properly: "$variable"
- Uses $() for command substitution, not backticks
- Handles arrays correctly: "${array[@]}"
- Implements proper signal traps for cleanup
- Uses -- in rm commands to handle filenames starting with dashes
- Sanitizes drag & drop paths using proper zsh methods
- Provides meaningful progress feedback with macOS notifications

---

**Remember: Build reliable, fast, delightful tools. Prioritize user experience and data safety above all else.**

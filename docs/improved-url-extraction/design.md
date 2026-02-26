# Design Document

## Overview

This design enhances the existing URLProcessor class in Nexus.py to provide more
robust and accurate URL extraction from various text formats. The solution
focuses on improving the regex patterns, text preprocessing, and post-processing
logic to handle edge cases that currently cause URLs to be missed or incorrectly
parsed.

## Architecture

The enhanced URL extraction system will maintain the existing URLProcessor class
structure but improve its internal methods:

```text
URLProcessor
├── **init**() - Enhanced regex patterns
├── sanitize_text_for_extraction() - Improved text preprocessing
├── extract_urls() - Enhanced extraction logic
├── _filter_and_validate_urls() - Better validation and deduplication
├── _is_valid_url() - Improved validation logic
├── _normalize_url() - Enhanced URL normalization
└── _split_concatenated_urls() - NEW: Handle stacked URLs
```

## Components and Interfaces

### Enhanced URLProcessor Class

**Current Issues Identified:**

1. Regex pattern in `**init**()` may miss URLs that are concatenated without

   spaces

2. `sanitize_text_for_extraction()` removes too many characters that might be

   part of valid URLs

3. No handling for URLs that are split across lines or have embedded whitespace
4. Limited support for various URL formats and edge cases

**Enhanced Methods:**

#### 1. Improved Regex Patterns

- Multiple regex patterns for different URL formats
- Pattern for detecting concatenated URLs
- Pattern for URLs with missing protocols
- Pattern for shortened URLs

#### 2. Enhanced Text Preprocessing

```python
def sanitize_text_for_extraction(self, text: str) -> str:

```
# Preserve more URL-relevant characters
# Handle line breaks within URLs
# Normalize various whitespace types
# Preserve URL delimiters

```text

```

#### 3. New URL Splitting Logic

```python
def _split_concatenated_urls(self, text: str) -> List[str]:

```
# Detect and split URLs that are stacked together
# Handle cases like "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<https://site1.comhttps://site2.com">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Use domain boundary detection

```text

```

#### 4. Improved Validation and Normalization

```python
def _enhanced_url_validation(self, url: str) -> bool:

```
# More comprehensive URL validation
# Handle edge cases and malformed URLs
# Support for various protocols and formats

```text

```

## Data Models

### URL Extraction Result

```python
@dataclass
class URLExtractionResult:

```
original_text: str
extracted_urls: List[str]
filtered_urls: List[str]
invalid_urls: List[str]
extraction_stats: Dict[str, int]

```text

```

### URL Processing Configuration

```python
@dataclass
class URLProcessingConfig:

```
enable_concatenated_splitting: bool = True
auto_add_protocol: bool = True
remove_duplicates: bool = True
max_url_length: int = 2048
supported_protocols: List[str] = field(default_factory=lambda: ['http', 'https', 'ftp'])

```text

```

## Error Handling

### Graceful Degradation

- If enhanced regex fails, fall back to original pattern
- Log extraction issues for debugging without breaking functionality
- Handle malformed input gracefully

### Validation Layers

1. **Syntax Validation**: Basic URL structure checks
2. **Protocol Validation**: Ensure supported protocols
3. **Length Validation**: Prevent extremely long URLs
4. **Blacklist Validation**: Existing extension filtering

## Testing Strategy

### Unit Tests

- Test various URL formats (shortened, extended, concatenated)
- Test edge cases (missing protocols, trailing punctuation)
- Test text preprocessing with different input types
- Test validation and normalization logic

### Integration Tests

- Test with URLTableWidget drag-drop functionality
- Test with clipboard paste operations
- Test with HTML content processing
- Test end-to-end URL extraction workflow

### Test Data Sets

- Collection of real-world note examples with various URL formats
- Edge case scenarios (malformed URLs, mixed content)
- Performance tests with large text blocks

## Implementation Approach

### Phase 1: Enhanced Regex Patterns

- Implement multiple specialized regex patterns
- Add concatenated URL detection logic
- Improve text preprocessing

### Phase 2: Validation and Normalization

- Enhance URL validation logic
- Improve normalization for edge cases
- Add comprehensive error handling

### Phase 3: Integration and Testing

- Update URLTableWidget integration
- Add extraction result feedback
- Implement comprehensive testing

### Phase 4: Performance Optimization

- Optimize regex performance for large texts
- Add caching for repeated extractions
- Profile and optimize bottlenecks

## Backward Compatibility

The enhanced URLProcessor will maintain the same public interface as the current
implementation, ensuring no breaking changes to existing code. All improvements
will be internal to the class methods.

## Configuration Options

New configuration options will be added to the Config class:

- `ENABLE_ENHANCED_URL_EXTRACTION`: Toggle for new features
- `MAX_URL_EXTRACTION_LENGTH`: Limit for processing large texts
- `URL_EXTRACTION_TIMEOUT`: Timeout for complex regex operations

# Requirements Document

## Introduction

The current URL extraction functionality in Nexus has limitations when
processing URLs from notes and text content. Users report that URLs are not
being detected consistently, especially when they appear in various formats -
some are shortened, some are extended, some have spaces between them, and some
are stacked together without spaces. This feature will enhance the URLProcessor
class to handle diverse URL formats and improve extraction accuracy from pasted
notes and text content.

## Requirements

### Requirement 1

**User Story:** As a user, I want to paste notes containing URLs in various
formats and have all valid URLs detected and extracted accurately, so that I can
efficiently process multiple URLs without manual formatting.

#### Acceptance Criteria

1. WHEN text contains URLs separated by spaces THEN the system SHALL extract

   each URL individually

2. WHEN text contains URLs stacked together without spaces THEN the system SHALL

   identify and separate each URL correctly

3. WHEN text contains shortened URLs (like bit.ly, tinyurl) THEN the system

   SHALL detect and extract them

4. WHEN text contains extended URLs with multiple parameters THEN the system

   SHALL extract the complete URL including all parameters

5. WHEN text contains URLs with various protocols (http, https, ftp) THEN the

   system SHALL extract all valid protocols

6. WHEN text contains URLs mixed with regular text THEN the system SHALL extract

   only the URLs while ignoring surrounding text

### Requirement 2

**User Story:** As a user, I want the URL extraction to handle malformed or
partial URLs gracefully, so that I don't lose valid URLs due to minor formatting
issues.

#### Acceptance Criteria (2)

1. WHEN text contains URLs with missing protocols THEN the system SHALL

   automatically add https:// prefix

2. WHEN text contains URLs with trailing punctuation (periods, commas) THEN the

   system SHALL remove trailing punctuation

3. WHEN text contains URLs with extra whitespace THEN the system SHALL trim

   whitespace and extract clean URLs

4. WHEN text contains URLs with line breaks in the middle THEN the system SHALL

   reconstruct the complete URL

5. WHEN text contains partial URLs that are clearly incomplete THEN the system

   SHALL skip them to avoid invalid entries

### Requirement 3

**User Story:** As a user, I want the system to provide feedback on URL
extraction results, so that I can understand what was found and verify the
accuracy.

#### Acceptance Criteria (3)

1. WHEN URLs are extracted from text THEN the system SHALL display the count of

   URLs found

2. WHEN duplicate URLs are found THEN the system SHALL remove duplicates and

   show unique URLs only

3. WHEN invalid URLs are filtered out THEN the system SHALL log the filtering

   process for debugging

4. WHEN no URLs are found in text THEN the system SHALL provide clear feedback

   to the user

5. WHEN URL extraction completes THEN the system SHALL update the URL counter

   display immediately

### Requirement 4

**User Story:** As a user, I want the URL extraction to work consistently across
different input methods (paste, drag-drop, typing), so that I have a reliable
experience regardless of how I input the text.

#### Acceptance Criteria (4)

1. WHEN text is pasted via Ctrl+V THEN the system SHALL extract URLs using the

   same logic as other input methods

2. WHEN text is dragged and dropped THEN the system SHALL process URLs with the

   same accuracy as pasted text

3. WHEN HTML content is pasted THEN the system SHALL extract both href links and

   plain text URLs

4. WHEN text is typed directly THEN the system SHALL process URLs in real-time

   or on demand

5. WHEN mixed content (HTML + plain text) is processed THEN the system SHALL

   handle both formats correctly

# searchengine

Search functionality for activities, exchanges, and other LCA data.

## Overview

This directory implements the search engine that enables users to quickly find activities, databases, methods, and other items across their LCA data.

## Features

### Full-Text Search
- Search across activity names
- Search in comments and descriptions
- Search in product/flow names
- Search in metadata fields

### Filtered Search
- Filter by database
- Filter by location
- Filter by unit
- Filter by activity type

### Advanced Search
- Boolean operators (AND, OR, NOT)
- Wildcard matching
- Regular expressions
- Field-specific queries

### Fast Indexing
- Incremental index updates
- Background indexing
- Efficient data structures
- Cached results

## Architecture

The search engine consists of:

1. **Indexer** - Builds searchable index from Brightway2 data
2. **Query Parser** - Parses user search queries
3. **Search Engine** - Performs actual search operations
4. **Result Ranker** - Orders results by relevance
5. **Cache** - Stores recent search results

## Usage Pattern

```python
from activity_browser.bwutils.searchengine import SearchEngine

engine = SearchEngine()

# Simple search
results = engine.search("electricity")

# Filtered search
results = engine.search(
    query="electricity",
    database="ecoinvent",
    location="CH"
)

# Advanced search
results = engine.search("(wind OR solar) AND electricity")
```

## Index Management

The search index is automatically maintained:
- Built on first use
- Updated when databases change
- Rebuilt when necessary
- Stored in user data directory

### Triggering Updates
```python
from activity_browser import app

# Index automatically updates on these signals:
app.signals.database_changed.emit()
app.signals.activity_modified.emit()
```

## Search Results

Results include:
- Activity key (database, code)
- Activity name
- Product name
- Location
- Unit
- Relevance score
- Highlighted matches

```python
for result in results:
    print(f"{result['name']} ({result['location']})")
    print(f"Score: {result['score']}")
```

## Performance Considerations

### Optimization Strategies
- Index only relevant fields
- Use appropriate data structures (tries, inverted indexes)
- Cache frequent queries
- Limit result set size
- Lazy loading of full activity data

### Threading
Search operations run in background threads:
```python
from activity_browser.ui.core.threading import ABThread

worker = ABThread(engine.search, query)
worker.finished.connect(display_results)
worker.start()
```

## Search Syntax

### Basic Search
```
electricity
```

### Phrase Search
```
"wind power"
```

### Boolean Operators
```
wind AND electricity
solar OR wind
electricity NOT coal
```

### Field-Specific
```
name:electricity location:CH unit:kWh
```

### Wildcards
```
electr*     # Prefix matching
*city       # Suffix matching
el*city     # Both
```

## Integration with UI

Search is accessible via:
- Global search bar in toolbar
- Database browser filter
- Activity browser search
- Quick search dialogs
- Context menu search

## Development Guidelines

When working with search:

1. **Index incrementally** - Update index, don't rebuild
2. **Run in background** - Don't block UI
3. **Limit results** - Provide pagination for large result sets
4. **Highlight matches** - Show why result matched
5. **Sort by relevance** - Put best matches first
6. **Support fuzzy matching** - Handle typos gracefully
7. **Cache wisely** - Balance memory vs. speed
8. **Profile performance** - Ensure searches complete quickly

## Testing

Test search with:
- Small and large databases
- Various query types
- Edge cases (special characters, unicode)
- Performance benchmarks
- Index rebuild scenarios

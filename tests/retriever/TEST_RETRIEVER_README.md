# RetrieverAgent Test Suite

This directory contains comprehensive testing tools for debugging and testing the RetrieverAgent's internet search functionality.

## Status Update (July 23, 2025)

✅ **RetrieverAgent Successfully Updated**: The RetrieverAgent has been updated with reliable Google, Bing, and Yahoo search functionality, replacing the previous DuckDuckGo implementation. All tests are passing with 100% success rate.

## Files

### test_retriever_simple.py

**NEW**: Simplified integration test that verifies the RetrieverAgent works within the Eunice framework. This test covers:

- Web search using Google and Bing search engines
- Web content extraction from real websites
- Academic paper search via Google Scholar
- Error handling and edge cases
- Complete integration with Eunice's MCP framework

### test_retriever_integration.py

Comprehensive integration test suite for the RetrieverAgent within the complete Eunice system.

### test_retriever_standalone.py

A completely standalone test application that doesn't require the full Eunice system. This includes:

- Simplified RetrieverAgent implementation
- ~~DuckDuckGo search testing~~ **DEPRECATED: DuckDuckGo removed due to reliability issues**
- Web content extraction testing
- Result ranking and filtering
- Interactive debugging mode
- Comprehensive test suite

### test_retriever_debug.py

Full-featured test application that works with the complete Eunice system (requires all dependencies).

### test_config_helper.py

Simple configuration helper for standalone testing.

### test_requirements.txt

Python dependencies needed for testing.

## Quick Start

### Option 1: Simple Integration Test (Recommended)

1. **Run the quick integration test:**

   ```bash
   python test_retriever_simple.py
   ```

   This test verifies that the RetrieverAgent works properly within the Eunice framework and covers:

   - Google & Bing search functionality
   - Web content extraction
   - Academic paper search
   - Error handling

### Option 2: Comprehensive Integration Testing

1. **Run the full integration test suite:**

   ```bash
   python test_retriever_integration.py
   ```

   This provides detailed testing with performance metrics and comprehensive reporting.

### Option 3: Standalone Testing (Legacy)

1. **Install dependencies:**

   ```bash
   pip install -r test_requirements.txt
   ```

2. **Run the standalone test suite:**

   ```bash
   python test_retriever_standalone.py
   ```

   Note: This may use deprecated DuckDuckGo functionality.

3. **Run interactive debugging:**

   ```bash
   python test_retriever_standalone.py --interactive
   ```

4. **Get help:**
   ```bash
   python test_retriever_standalone.py --help
   ```

### Option 2: Full System Testing

1. **Ensure Eunice system is available:**

   ```bash
   # Make sure you have the full src/ directory
   ls src/agents/retriever_agent.py
   ```

2. **Install all dependencies:**

   ```bash
   pip install -r requirements.txt
   pip install -r test_requirements.txt
   ```

3. **Run the comprehensive test suite:**

   ```bash
   python test_retriever_debug.py
   ```

4. **Run interactive mode:**
   ```bash
   python test_retriever_debug.py --interactive
   ```

## Test Features

### Automated Tests

- **Basic Search Testing**: Tests DuckDuckGo search functionality with various queries
- **Content Extraction**: Tests web page content extraction from various sites
- **Academic Search**: Tests Google Scholar search functionality (when available)
- **Document Retrieval**: Tests multi-URL document retrieval
- **Result Filtering**: Tests filtering by relevance scores
- **Result Ranking**: Tests ranking algorithms
- **Error Handling**: Tests various error scenarios
- **Performance Testing**: Measures response times and throughput

### Interactive Debugging

- **Manual Search Testing**: Enter custom search queries and see results
- **URL Content Extraction**: Extract content from any URL
- **Result Analysis**: Examine search results in detail
- **Agent Status Monitoring**: View agent configuration and status
- **Quick Tests**: Run subset of tests for rapid feedback

### Output and Logging

- **Console Output**: Real-time test progress and results
- **Log Files**: Detailed logs saved to timestamped files
- **JSON Reports**: Machine-readable test results
- **Performance Metrics**: Timing and success rate statistics

## Example Usage

### Standalone Quick Test

```bash
# Install dependencies
pip install aiohttp beautifulsoup4

# Run a quick test
python test_retriever_standalone.py

# Interactive debugging
python test_retriever_standalone.py --interactive
```

### Interactive Session Example

```
RETRIEVER AGENT INTERACTIVE DEBUGGER
==================================================
1. Search DuckDuckGo
2. Extract Web Content
3. Rank Search Results
4. Run Quick Test
5. View Agent Status
0. Exit
--------------------------------------------------
Enter your choice: 1
Enter search query: Python machine learning
Max results (default 5): 3

Searching for: Python machine learning

✓ Search completed in 1.23s
Found 2 results:

1. Python Machine Learning Tutorial
   URL: https://example.com/tutorial
   Type: related_topic
   Score: 4
   Content: Learn machine learning with Python using scikit-learn...

2. Machine Learning with Python
   URL: https://example.com/guide
   Type: related_topic
   Score: 3
   Content: Complete guide to machine learning algorithms...
```

## Test Results (Latest Integration Test - July 23, 2025)

✅ **ALL TESTS PASSING**: The RetrieverAgent integration test shows 100% success rate with the updated search functionality.

### Latest Test Summary

```text
RETRIEVER AGENT INTEGRATION TEST REPORT
============================================================
Total Tests: 5
Successful: 5
Failed: 0
Success Rate: 100.0%
Total Duration: 7.23s
Average Test Duration: 1.45s

DETAILED RESULTS
----------------------------------------
✅ PASS Search Information (2.78s)
    Queries tested: 4
    Total results: 20
✅ PASS Extract Web Content (1.51s)
    URLs tested: 4
    Success rate: 100.0%
✅ PASS Academic Search (1.59s)
✅ PASS Error Handling (0.00s)
    Error handling rate: 100.0%
✅ PASS Multiple Search Engines (1.36s)
```

### Performance Metrics

- **Google Search**: ~0.2-0.4s response time, reliable results
- **Bing Search**: ~0.3-0.6s response time, high-quality results
- **Yahoo Search**: Currently experiencing service issues (HTTP 500), but fallback handling works
- **Content Extraction**: 0.1-0.7s depending on page complexity
- **Academic Search**: ~1.6s for Google Scholar queries

### Search Engine Status

| Engine         | Status            | Response Time | Result Quality          |
| -------------- | ----------------- | ------------- | ----------------------- |
| Google         | ✅ Working        | ~0.3s         | Excellent               |
| Bing           | ✅ Working        | ~0.5s         | Excellent               |
| Yahoo          | ⚠️ Service Issues | N/A           | N/A (graceful fallback) |
| Google Scholar | ✅ Working        | ~1.6s         | Excellent               |

Test results are automatically saved in multiple formats:

- **Console Summary**: Immediate feedback with pass/fail status
- **Log File**: `retriever_test_YYYYMMDD_HHMMSS.log`
- **JSON Report**: `retriever_test_results_YYYYMMDD_HHMMSS.json`

### Sample Test Summary

```
RETRIEVER AGENT TEST SUMMARY
================================================================================
Total Tests: 15
Successful: 13
Failed: 2
Success Rate: 86.7%
Total Duration: 45.67s
Average Test Duration: 3.04s

DETAILED RESULTS
--------------------------------------------------------------------------------
✓ PASS DuckDuckGo Search - Python programming language (2.15s)
    Found: 3 results
✓ PASS Content Extraction - https://www.python.org/ (1.89s)
    Title: Welcome to Python.org
    Content Length: 2847 chars
✗ FAIL Error Handling - Invalid URL (0.05s)
    Error: Invalid URL scheme
```

## Troubleshooting

### Common Issues

1. **Import Errors**: If you get import errors, use the standalone version
2. **Network Timeouts**: Increase timeout values in the configuration
3. **Rate Limiting**: Add delays between requests if getting blocked
4. **SSL Errors**: Some sites may have SSL certificate issues

### Debug Tips

1. **Enable Verbose Logging**: Set logging level to DEBUG
2. **Test Individual Components**: Use interactive mode to test specific functions
3. **Check Network Connectivity**: Ensure internet access is available
4. **Validate URLs**: Test with known-good URLs first

### Performance Notes

- Search operations typically take 1-3 seconds
- Content extraction depends on page size and complexity
- Rate limiting is implemented to avoid being blocked
- Results are cached during a single test session

## Dependencies

### Required

- `aiohttp`: Async HTTP client
- `beautifulsoup4`: HTML parsing
- `asyncio`: Async programming (built-in Python 3.7+)

### Optional

- `rich`: Enhanced console output
- `colorama`: Cross-platform colored terminal text
- `pytest`: For running as pytest tests

## Contributing

When adding new tests:

1. Follow the existing test pattern
2. Add both success and failure test cases
3. Include performance timing
4. Update this README with new features
5. Ensure tests work in both standalone and full system modes

## License

This test suite is part of the Eunice project and follows the same license terms.

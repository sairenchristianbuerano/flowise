#!/bin/bash

################################################################################
# Flowise Services Endpoint Test Script
#
# This script tests all endpoints in the Flowise Component Generator and
# Component Index services, excluding endpoints that use Claude API credits.
#
# Usage:
#   bash test_endpoints.sh
#   OR
#   ./test_endpoints.sh (if executable)
#
# Requirements:
#   - Docker containers must be running (component-generator, component-index)
#   - curl must be installed
#   - jq (optional, for JSON parsing)
#
# Output:
#   - Console output with color-coded results
#   - test_results.log file with detailed results
################################################################################

# Configuration
GENERATOR_URL="http://localhost:8085"
INDEX_URL="http://localhost:8086"
LOG_FILE="test_results.log"
ORIGIN_HEADER="Origin: http://localhost:3000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=15
PASSED_TESTS=0
FAILED_TESTS=0

# Test data variables (populated during tests)
COMPONENT_ID=""
COMPONENT_NAME="TestComponent"

################################################################################
# Helper Functions
################################################################################

# Print colored output
print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    echo "[PASS] $1" >> "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo "[FAIL] $1" >> "$LOG_FILE"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[INFO] $1" >> "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[WARN] $1" >> "$LOG_FILE"
}

# Test endpoint function
test_endpoint() {
    local test_num=$1
    local test_name=$2
    local method=$3
    local url=$4
    local data=$5
    local expected_status=${6:-200}

    print_info "Test $test_num/$TOTAL_TESTS - $test_name"

    # Make the request
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" -H "$ORIGIN_HEADER" -H "Content-Type: application/json" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" -H "$ORIGIN_HEADER" -H "Content-Type: application/json" -d "$data" 2>&1)
    fi

    # Extract status code (last line)
    http_code=$(echo "$response" | tail -n1)

    # Extract body (all but last line)
    body=$(echo "$response" | sed '$d')

    # Check status code
    if [ "$http_code" -eq "$expected_status" ]; then
        print_success "Test $test_num/$TOTAL_TESTS - $test_name (HTTP $http_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))

        # Return the body for further processing
        echo "$body"
        return 0
    else
        print_error "Test $test_num/$TOTAL_TESTS - $test_name (Expected HTTP $expected_status, got $http_code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "$body" >> "$LOG_FILE"
        return 1
    fi
}

# Initialize log file
init_log() {
    echo "========================================" > "$LOG_FILE"
    echo "Flowise Services Endpoint Test Results" >> "$LOG_FILE"
    echo "========================================" >> "$LOG_FILE"
    echo "Test Date: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    echo "Services: Component Generator ($GENERATOR_URL), Component Index ($INDEX_URL)" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
}

# Print summary
print_summary() {
    local success_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi

    echo ""
    echo "========================================"
    echo "SUMMARY"
    echo "========================================"
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo "Success Rate: $success_rate%"
    echo "========================================"

    echo "" >> "$LOG_FILE"
    echo "========================================" >> "$LOG_FILE"
    echo "SUMMARY" >> "$LOG_FILE"
    echo "========================================" >> "$LOG_FILE"
    echo "Total Tests: $TOTAL_TESTS" >> "$LOG_FILE"
    echo "Passed: $PASSED_TESTS" >> "$LOG_FILE"
    echo "Failed: $FAILED_TESTS" >> "$LOG_FILE"
    echo "Success Rate: $success_rate%" >> "$LOG_FILE"
    echo "========================================" >> "$LOG_FILE"

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
    else
        echo -e "${RED}Some tests failed. Check test_results.log for details.${NC}"
    fi
}

################################################################################
# Main Test Suite
################################################################################

echo "========================================"
echo "Flowise Services Endpoint Test Suite"
echo "========================================"
echo ""

# Initialize log
init_log

################################################################################
# Component Generator Tests
################################################################################

echo -e "${BLUE}>>> Testing Component Generator Service ($GENERATOR_URL)${NC}"
echo ""

# Test 1: Health Check
test_endpoint 1 "Component Generator Health Check" "GET" "$GENERATOR_URL/api/flowise/component-generator/health" "" 200 > /dev/null

# Test 2: Sample Generation (Note: This may take 30 seconds)
test_endpoint 2 "Component Generator Sample Generation" "POST" "$GENERATOR_URL/api/flowise/component-generator/generate/sample" "" 200 > /dev/null

echo ""

################################################################################
# Component Index Tests - Health & Stats
################################################################################

echo -e "${BLUE}>>> Testing Component Index Service ($INDEX_URL)${NC}"
echo ""

# Test 3: Health Check
test_endpoint 3 "Component Index Health Check" "GET" "$INDEX_URL/api/flowise/component-index/health" "" 200 > /dev/null

# Test 4: Component Stats
test_endpoint 4 "Component Index Stats" "GET" "$INDEX_URL/api/flowise/component-index/components/stats" "" 200 > /dev/null

# Test 5: List Components
test_endpoint 5 "Component Index List Components" "GET" "$INDEX_URL/api/flowise/component-index/components?limit=10" "" 200 > /dev/null

echo ""

################################################################################
# Component Index Tests - CRUD Operations
################################################################################

echo -e "${BLUE}>>> Testing Component Registry CRUD Operations${NC}"
echo ""

# Test 6: Register Component
register_data='{
  "name": "TestComponent",
  "display_name": "Test Component",
  "description": "A test component for endpoint testing",
  "category": "tools",
  "platform": "flowise",
  "version": "1.0.0",
  "author": "Test Script",
  "code_size": 1000,
  "dependencies": ["axios"],
  "validation_passed": true,
  "deployment_status": "pending"
}'

# Use temp file to capture response without subshell (to preserve PASSED_TESTS counter)
TEMP_RESPONSE="/tmp/test_endpoint_response_$$.json"
test_endpoint 6 "Register Component" "POST" "$INDEX_URL/api/flowise/component-index/components/register" "$register_data" 200 > "$TEMP_RESPONSE"

# Extract component_id from response (using grep and sed for portability)
COMPONENT_ID=$(grep -o '"component_id":"[^"]*"' "$TEMP_RESPONSE" | sed 's/"component_id":"\([^"]*\)"/\1/')
rm -f "$TEMP_RESPONSE"

if [ -z "$COMPONENT_ID" ]; then
    print_warning "Could not extract component_id from registration response"
else
    print_info "Registered component with ID: $COMPONENT_ID"
fi

# Test 7: Get Component by Name
test_endpoint 7 "Get Component by Name" "GET" "$INDEX_URL/api/flowise/component-index/components/name/$COMPONENT_NAME" "" 200 > /dev/null

# Test 8: Get Component by ID
if [ -n "$COMPONENT_ID" ]; then
    test_endpoint 8 "Get Component by ID" "GET" "$INDEX_URL/api/flowise/component-index/components/$COMPONENT_ID" "" 200 > /dev/null
else
    print_warning "Skipping Test 8 - No component ID available"
    TOTAL_TESTS=$((TOTAL_TESTS - 1))
fi

# Test 9: Update Deployment Status
if [ -n "$COMPONENT_ID" ]; then
    test_endpoint 9 "Update Deployment Status" "PATCH" "$INDEX_URL/api/flowise/component-index/components/$COMPONENT_ID/deployment?status=deployed" "" 200 > /dev/null
else
    print_warning "Skipping Test 9 - No component ID available"
    TOTAL_TESTS=$((TOTAL_TESTS - 1))
fi

echo ""

################################################################################
# Component Index Tests - Pattern Search (RAG)
################################################################################

echo -e "${BLUE}>>> Testing Pattern Search Operations${NC}"
echo ""

# Test 10: Pattern Stats
test_endpoint 10 "Pattern Search Stats" "GET" "$INDEX_URL/api/flowise/component-index/patterns/stats" "" 200 > /dev/null

# Test 11: Search Patterns
search_data='{
  "query": "calculator tool for mathematical operations",
  "n_results": 3
}'
test_endpoint 11 "Search Patterns" "POST" "$INDEX_URL/api/flowise/component-index/patterns/search" "$search_data" 200 > /dev/null

# Test 12: Find Similar Patterns
similar_data='{
  "description": "A component that performs calculations",
  "category": "tools",
  "n_results": 3
}'
test_endpoint 12 "Find Similar Patterns" "POST" "$INDEX_URL/api/flowise/component-index/patterns/similar" "$similar_data" 200 > /dev/null

# Test 13: Reindex Patterns
reindex_data='{
  "force_reindex": false
}'
test_endpoint 13 "Reindex Patterns" "POST" "$INDEX_URL/api/flowise/component-index/patterns/index" "$reindex_data" 200 > /dev/null

echo ""

################################################################################
# Cleanup - Delete Test Component
################################################################################

echo -e "${BLUE}>>> Cleanup${NC}"
echo ""

# Test 14: Delete Component (Cleanup)
if [ -n "$COMPONENT_ID" ]; then
    test_endpoint 14 "Delete Test Component" "DELETE" "$INDEX_URL/api/flowise/component-index/components/$COMPONENT_ID" "" 200 > /dev/null
else
    print_warning "Skipping Test 14 - No component ID available"
    TOTAL_TESTS=$((TOTAL_TESTS - 1))
fi

################################################################################
# Additional CORS Verification Test
################################################################################

echo -e "${BLUE}>>> CORS Verification${NC}"
echo ""

# Test 15: CORS Preflight (OPTIONS request)
print_info "Test 15/$TOTAL_TESTS - CORS Preflight Request"
cors_response=$(curl -s -w "\n%{http_code}" -X OPTIONS "$INDEX_URL/api/flowise/component-index/health" \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: Content-Type" \
    2>&1)

cors_status=$(echo "$cors_response" | tail -n1)

if [ "$cors_status" -eq 200 ] || [ "$cors_status" -eq 204 ]; then
    print_success "Test 15/$TOTAL_TESTS - CORS Preflight Request (HTTP $cors_status)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "Test 15/$TOTAL_TESTS - CORS Preflight Request (Expected HTTP 200/204, got $cors_status)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo ""

################################################################################
# Print Summary
################################################################################

print_summary

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    exit 0
else
    exit 1
fi

# API Tests

This directory contains Postman collections and environment files for testing the WebClerk3 API.

## Files

### Collections

- **`UniversalAPI.postman_collection.json`** - Comprehensive test suite for all Universal API endpoints
- **`webclerk3_smoke.postman_collection.json`** - Basic smoke tests to verify API availability

### Environments

- **`local.postman_environment.json`** - Local development environment configuration
- **`webclerk3_local.postman_environment.json`** - Alternative local environment setup

## Usage

1. Import the collection(s) and environment file into Postman
2. Select the appropriate environment
3. Run the tests to verify API functionality

## Setup

The environment files contain variables for:

- Base URL
- Authentication tokens
- Test data IDs

Update these variables to match your local/development environment.

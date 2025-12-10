# eRaktKosh Agent

An agentic interface for the eRaktKosh blood bank portal, built with FastMCP, Playwright, and LangGraph. This system enables AI agents to query real-time blood stock availability using natural language.

## Features
- **Hybrid Architecture**: Combines cached hierarchy data (Cold Path) with live scraping (Hot Path).
- **Fuzzy Normalization**: Maps user queries (e.g., "Pune", "Maha") to official eRaktKosh codes.
- **Human-in-the-Loop**: Detects ambiguous locations and asks for clarification.
- **FastMCP Server**: Exposes tools for location normalization and stock fetching.
- **Pagination Support**: Automatically fetches up to 50 results (5 pages) for high-traffic searches.
- **Smart Defaults**: Defaults search to "Packed Red Blood Cells" if no specific component is requested.

## Prerequisites

- Python 3.10+
- `uv` (Project manager)
- Google API Key (for Gemini models)

## Installation

1.  **Install dependencies**:
    ```bash
    uv sync
    ```

2.  **Install Playwright browsers**:
    ```bash
    uv run playwright install
    ```

3.  **Setup Environment Variables**:
    - Create a `.env` file in the root directory.
    - Add your `GOOGLE_API_KEY`:
      ```env
      GOOGLE_API_KEY=your_api_key_here
      ```

## Usage

### Running the Server
Start the FastMCP server:
```bash
uv run server.py
```
> **Note**: The first run will take a few minutes to scrape and cache the state/district hierarchy (`hierarchy.json`). Subsequent runs will load from the cache.

### Running Verification
Run the end-to-end verification script to test normalization and live scraping:
```bash
uv run test_agent.py
```

## Project Structure
- `server.py`: Main FastMCP server and lifespan manager.
- `scraper.py`: Playwright scraper for eRaktKosh.
- `graph.py`: LangGraph orchestration and state machine.
- `models.py`: Pydantic models for data validation.
- `utils.py`: Helper functions for fuzzy matching and caching.
- `hierarchy.json`: Cached State/District mapping.

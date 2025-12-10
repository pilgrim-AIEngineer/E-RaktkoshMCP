# Best Practices & Contribution Guidelines

## Code Style
- Follow PEP 8 guidelines.
- Use type hints for all function signatures.
- Keep dependencies managed via `uv`.

## Architecture
- **Scraper**: Keep scraping logic isolated in `scraper.py`. Do not mix business logic with DOM manipulation.
- **Server**: `server.py` should only handle MCP protocol and routing.
- **Graph**: Complex decision-making logic resides in `graph.py` (LangGraph).

## Testing
- Run verification checks before committing:
  ```bash
  uv run test_agent.py
  ```

## Security
- Never commit `.env` files.
- Do not hardcode API keys.

## Pagination
- The scraper is currently limited to 5 pages (approx 50 records) to balance performance and utility. Adjust logic in `scraper.py` if needed.

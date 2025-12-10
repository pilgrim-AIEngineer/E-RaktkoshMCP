import asyncio
import os
from server import lifespan, mcp, _normalize_location, _fetch_stock
from fastmcp import FastMCP

async def main():
    print("Starting verification...")
    
    # Mock server instance for lifespan
    # We can just use the 'mcp' object imported from server
    
    async with lifespan(mcp):
        print("\n--- Testing Normalization ---")
        # Test 1: Valid State
        print("Test 1: Normalizing 'Maharashtra'")
        res = await _normalize_location("Maharashtra")
        print(res)
        
        # Test 2: Valid District
        print("\nTest 2: Normalizing 'Pune'")
        res = await _normalize_location("Pune")
        print(res)
        
        # Test 3: Ambiguous/Typo
        print("\nTest 3: Normalizing 'Rampur' (Ambiguous)")
        res = await _normalize_location("Rampur")
        print(res)

        print("\n--- Testing Stock Fetching (Hot Path) ---")
        # Test 4: Fetch Stock
        # Note: This will actually hit the website.
        print("Test 4: Fetching stock for 'Pune', 'O+'")
        stock = await _fetch_stock("Pune", "O+")
        print(stock[:500] + "..." if len(stock) > 500 else stock)
        
        # Test 5: Fetch Stock with Ambiguity
        print("\nTest 5: Fetching stock for 'Rampur', 'A+'")
        stock = await _fetch_stock("Rampur", "A+")
        print(stock)

        # Test 6: Fetch Stock for Valid State (Andhra Pradesh)
        print("\nTest 6: Fetching stock for 'Andhra Pradesh', 'All'")
        stock = await _fetch_stock("Andhra Pradesh", "All")
        print(stock[:500] + "..." if len(stock) > 500 else stock)

        # Test 7: Fetch Stock with Component
        print("\nTest 7: Fetching stock for 'Andhra Pradesh', 'O+', 'Whole Blood'")
        stock = await _fetch_stock("Andhra Pradesh", "O+", "Whole Blood")
        print(stock[:500] + "..." if len(stock) > 500 else stock)

if __name__ == "__main__":
    asyncio.run(main())

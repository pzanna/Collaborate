#!/usr/bin/env python3
"""
Database Service Main Entry Point

This is the main entry point for the database service.
"""

from database_service import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

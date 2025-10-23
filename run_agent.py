#!/usr/bin/env python3
"""
Simple test script to run the LangChain ReAct agent
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🚀 MCP Agent Comparison")
    print("=" * 50)
    print("1. Original MCP Agent (main.py)")
    print("2. LangChain ReAct Agent (langchain_react_agent.py)")
    print("3. FastAPI Web Interface (app.py)")
    print("=" * 50)
    
    choice = input("Choose an option (1-3): ").strip()
    
    if choice == "1":
        print("\n🔧 Starting Original MCP Agent...")
        from main import interactive_chat
        asyncio.run(interactive_chat())
        
    elif choice == "2":
        print("\n🧠 Starting LangChain ReAct Agent...")
        try:
            from langchain_react_agent import main
            mcp_url = os.getenv("MCP_URL", "http://localhost:3002/sse")
            asyncio.run(main(mcp_url=mcp_url))
        except ImportError as e:
            print(f"❌ Error: {e}")
            print("Install LangChain with: pip install langchain langchain-openai langchainhub")
            
    elif choice == "3":
        print("\n🌐 Starting FastAPI Web Interface...")
        print("Run: uvicorn app:app --reload --host 0.0.0.0 --port 8000")
        print("Then open: http://localhost:8000")
        
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
 

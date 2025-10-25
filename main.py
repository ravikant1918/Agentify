import asyncio
import json
import os
from datetime import datetime
from src.mcp_client import MCPClient
from dotenv import load_dotenv
load_dotenv()
mcp_url = os.getenv("MCP_URL", "http://localhost:8000")

def save_chat_history(chat_history, filename="chat_history.json"):
    """Save chat history to a JSON file"""
    try:
        history_data = {
            "timestamp": datetime.now().isoformat(),
            "conversations": chat_history
        }
        with open(filename, 'w') as f:
            json.dump(history_data, f, indent=2)
        print(f"💾 Chat history saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving chat history: {e}")

def load_chat_history(filename="chat_history.json"):
    """Load chat history from a JSON file"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                history_data = json.load(f)
            print(f"📂 Loaded chat history from {filename} (saved: {history_data.get('timestamp', 'unknown')})")
            return history_data.get('conversations', [])
        return []
    except Exception as e:
        print(f"❌ Error loading chat history: {e}")
        return []

async def interactive_chat():
    client = MCPClient()

    async with client.sse_client_lifecycle(mcp_url) as session:
        client.session = session

        available_tools = await client.list_tools()

        # Initialize tool session map so each tool name has a valid MCP session object
        tool_session_map = {tool['function']['name']: session for tool in available_tools}

        # Initialize conversation history
        chat_history = load_chat_history()

        print("\n🤖 Connected to MCP Agent!")
        print(f"📋 Available tools: {len(available_tools)}")
        if available_tools:
            tool_names = [tool['function']['name'] for tool in available_tools]
            print(f"🔧 Tools: {', '.join(tool_names)}")
        if chat_history:
            print(f"📚 Loaded {len(chat_history)} previous conversations")
        print("Type 'exit' to quit, 'clear' to clear history, 'save' to save history, or 'history' to view chat history.\n")

        while True:
            user_query = input("👉 You: ").strip()

            if user_query.lower() in ['exit', 'quit']:
                print("🚀 Exiting chat...")
                break
            
            if user_query.lower() == 'clear':
                chat_history = []
                client.messages = []  # Clear the client's message history too
                print("🗑️ Chat history cleared!\n")
                continue
                
            if user_query.lower() == 'save':
                save_chat_history(chat_history)
                continue
                
            if user_query.lower() == 'history':
                print("\n📚 Chat History:")
                if not chat_history:
                    print("   No history yet.")
                else:
                    for i, (user_msg, agent_msg) in enumerate(chat_history, 1):
                        print(f"   {i}. You: {user_msg}")
                        print(f"      Agent: {agent_msg[:100]}{'...' if len(agent_msg) > 100 else ''}")
                print()
                continue

            # Set the chat history in the client before processing
            if chat_history:
                # Build the full conversation history
                client.messages = []
                for prev_user, prev_agent in chat_history:
                    client.messages.append({"role": "user", "content": prev_user})
                    client.messages.append({"role": "assistant", "content": prev_agent})

            response = await client.process_user_query(
                available_tools=available_tools,
                user_query=user_query,
                tool_session_map=tool_session_map
            )

            # Add this interaction to chat history
            chat_history.append((user_query, response))

            print(f"\n🧠 Agent: {response}\n")

    # Auto-save chat history on exit
    if chat_history:
        save_chat_history(chat_history)

    await client.close()
    print("[INFO] Client closed cleanly.")


if __name__ == "__main__":
    asyncio.run(interactive_chat())

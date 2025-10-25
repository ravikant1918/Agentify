# 🤖 Agen## 🧠 Overview
**Agentify** is an open-source web application that lets you instantly create a functional AI chat assistant using your own **MCP tools**, **LLM provider**, and custom **system prompt**. It combines a modern web interface with powerful backend capabilities including LangChain ReAct agents for advanced reasoning.

With **zero coding**, developers can configure their preferred:
- 🛠️ MCP tools and endpoints
- 🤖 LLM provider (OpenAI, Azure, Anthropic, Groq, etc.)
- 💭 System instructions and behavior
- 🎨 Web interface customization

> 💡 *Think of it as your personal AI assistant builder — just configure your tools and models, then start chatting!*
**Turn config into a working agent.**

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Status](https://img.shields.io/badge/Status-Active-success)

---

## 🧠 Overview
**Agentify** is an open-source framework that lets you instantly create a functional problem-solving agent using your own **MCP URL**, **system prompt**, and **LLM configuration**.  

With **zero coding**, developers can simply clone the repo, fill in their config, and start solving problems right away.  

> 💡 *Think of it as a plug-and-play agent builder — just configure, and you’re ready to go.*

---

## ⚙️ Features
- 🌐 **Modern Web Interface** — Clean, responsive chat UI with real-time updates
- 🔌 **MCP Integration** — Connect to any MCP-compatible tool server
- 🧠 **Multi-LLM Support** — Works with OpenAI, Azure, Anthropic, Groq, and custom endpoints
- ⚡ **LangChain ReAct** — Advanced reasoning and autonomous tool usage
- 💾 **Session Management** — Persistent chat history and context
- 🛠️ **Docker Ready** — Easy deployment with Docker Compose
- 🔧 **Customizable** — Simple configuration via UI or `.env`
- 🎨 **Themeable UI** — Clean, modern design with customizable styles
- 📱 **Responsive Design** — Works on desktop and mobile devices
- 🌍 **Open Source** — MIT licensed and free to use

---

## 📦 Project Structure
```
.
├── app.py                     # FastAPI web application entry point
├── deploy.sh                  # Deployment automation script
├── docker-compose.yml         # Docker container orchestration
├── Dockerfile                 # Docker image configuration
├── langchain_react_agent.py   # LangChain ReAct agent implementation
├── main.py                    # Main MCP client application
├── requirement.txt            # Project dependencies
├── run_agent.py              # Agent execution script
├── src/                      # Core source code
│   ├── __init__.py
│   ├── agent.py             # Agent implementation
│   ├── config_manager.py    # Secure configuration management
│   ├── llm_factory.py       # LLM provider configuration
│   ├── mcp_client.py        # MCP integration client
│   └── session_manager.py   # Session management
├── static/                   # Static web assets
│   └── styles.css           # UI styling
└── templates/               # HTML templates
    ├── config.html         # Configuration management UI
    └── index.html         # Main chat interface
```
.
├── app.py                     # FastAPI web application entry point
├── deploy.sh                  # Deployment automation script
├── docker-compose.yml         # Docker container orchestration
├── Dockerfile                 # Docker image configuration
├── langchain_react_agent.py   # LangChain ReAct agent implementation
├── main.py                    # Main MCP client application
├── requirement.txt            # Project dependencies
├── run_agent.py              # Agent execution script
├── src/                      # Core source code
│   ├── __init__.py
│   ├── agent.py             # Agent implementation
│   ├── llm_factory.py       # LLM provider configuration
│   ├── mcp_client.py        # MCP integration client
│   └── session_manager.py   # Session management
├── static/                   # Static web assets
│   └── styles.css           # UI styling
└── templates/               # HTML templates
    └── index.html          # Main chat interface
```

---

## 🚀 Quick Start

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/agentify.git
cd agentify
```

### 2️⃣ Set Up Environment
Copy the example environment file:
```bash
cp .env.example .env
```

Edit the `.env` file and fill in your configuration:

```bash
MCP_URL=https://your-mcp-url.com
SYSTEM_PROMPT="You are a helpful AI assistant that solves user queries."
LLM_API_KEY=your-api-key-here
MODEL_NAME=gpt-4o
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run Quickstart Example
```bash
python examples/quickstart.py
```

✅ Your agent is now live and ready to solve problems!

---

## 🧩 Example Usage
```python
from agentify.agent_runner import AgentRunner

agent = AgentRunner()
response = agent.solve("How do I optimize my Python code?")
print(response)
```

---

## 🔧 Configuration Management

### Web Interface
Agentify now includes a comprehensive configuration management UI accessible at `/config`. Here you can:

- 🔄 **Manage Multiple MCP Servers**
  - Add, edit, and remove MCP server configurations
  - Set server URLs, authentication, and custom settings
  - Switch between different MCP servers in real-time

- 🔑 **LLM Settings**
  - Configure multiple LLM providers (OpenAI, Azure, etc.)
  - Securely store API keys and endpoints
  - Set model preferences and parameters

- 💾 **Persistent Storage**
  - All configurations are securely stored in Redis
  - Sensitive data is encrypted at rest
  - Easy backup and restore functionality

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_URL` | Redis connection URL for config storage | `redis://localhost:6379` | Yes |
| `ENCRYPTION_KEY` | Key for securing sensitive data | - | Yes |
| `DEFAULT_MCP_URL` | Default MCP server URL | `http://localhost:8000` | No |
| `DEFAULT_LLM_PROVIDER` | Default LLM provider | `azure` | No |
| `LLM_API_KEY` | Default API key for LLM | - | Yes |
| `AZURE_ENDPOINT` | Azure OpenAI endpoint (if using Azure) | - | No |
| `MODEL_NAME` | Default model to use | `gpt-4` | No |

### Redis Setup

1. Install Redis:
   ```bash
   # macOS with Homebrew
   brew install redis
   brew services start redis

   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis-server
   ```

2. Set the encryption key:
   ```bash
   export ENCRYPTION_KEY=$(openssl rand -hex 32)
   ```

3. Verify Redis connection:
   ```bash
   redis-cli ping
   ```

### Configuration API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mcp/servers` | GET | List all MCP servers |
| `/api/mcp/servers` | POST | Add new MCP server |
| `/api/mcp/servers/{id}` | DELETE | Remove MCP server |
| `/api/mcp/servers/{id}` | PATCH | Update MCP server |
| `/api/llm/config` | POST | Update LLM settings |

### Configuration File Example
```json
{
  "mcp_servers": [
    {
      "id": "dev-server",
      "url": "http://localhost:8000",
      "auth_type": "none"
    },
    {
      "id": "prod-server",
      "url": "https://mcp.example.com",
      "auth_type": "bearer",
      "auth_token": "xxx"
    }
  ],
  "llm_config": {
    "provider": "azure",
    "model": "gpt-4",
    "api_version": "2024-12-01-preview",
    "azure_endpoint": "https://your-endpoint.openai.azure.com"
  }
}

---

## 📚 Folder Details
- `agentify/core.py` → Core logic for agent workflow  
- `agentify/config_loader.py` → Loads environment/config variables  
- `agentify/agent_runner.py` → Executes the agent using loaded config  
- `examples/quickstart.py` → Demo entry point for testing your setup  

---

## 🤝 Contributing
Contributions are welcome!  
If you’d like to improve **Agentify**, fork the repo and submit a pull request.

1. Fork the repository  
2. Create your feature branch (`git checkout -b feature-name`)  
3. Commit your changes (`git commit -m 'Add new feature'`)  
4. Push to your branch (`git push origin feature-name`)  
5. Open a Pull Request  

---

## 🧾 License
This project is licensed under the [MIT License](LICENSE).  
You’re free to use, modify, and distribute it — just keep the license file.

---

## ❤️ Support
If you find **Agentify** useful, please ⭐ star the repo and share it with others.  
For issues or feature requests, open a [GitHub Issue](https://github.com/your-username/agentify/issues).

---

> **Agentify — Turn config into a working agent.**
> Clone. Configure. Create.


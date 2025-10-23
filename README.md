# 🤖 Agentify  
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
- 🔌 **Plug-and-play setup** — configure once, run anywhere  
- 🧠 **MCP + LLM ready** — works with any compatible model or endpoint  
- ⚡ **Lightweight & flexible** — extend, customize, or integrate easily  
- 🧩 **Developer-friendly** — simple `.env` configuration  
- 🌍 **Open-source & free to use**

---

## 📦 Project Structure
```
agentify/
├── agentify/
│   ├── __init__.py
│   ├── core.py
│   ├── config_loader.py
│   └── agent_runner.py
├── examples/
│   └── quickstart.py
├── .env.example
├── requirements.txt
└── README.md
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

## 🔧 Configuration Options

| Variable | Description | Example |
|-----------|-------------|----------|
| `MCP_URL` | Your MCP service endpoint | `https://your-mcp-url.com` |
| `SYSTEM_PROMPT` | Defines how your agent behaves | `"You are a helpful AI assistant"` |
| `LLM_API_KEY` | API key for your model provider | `sk-abc123` |
| `MODEL_NAME` | The LLM to use | `gpt-4o`, `claude-3`, etc. |

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


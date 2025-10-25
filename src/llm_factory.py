# llm_factory.py
import os
from langchain_openai import ChatOpenAI, AzureChatOpenAI, GeminiChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()


class LLMClientFactory:
    """Factory class to create LangChain-compatible LLM clients for different providers."""

    @staticmethod
    def create(provider: str):
        provider = provider.lower().strip()
        temperature = 0.1

        if provider == "azure":
            print("[INFO] Using Azure OpenAI for LangChain ReAct agent")
            return AzureChatOpenAI(
                azure_deployment=os.getenv("MODEL", "gpt-35-turbo"),
                api_version=os.getenv("AZURE_API_VERSION", "2023-05-15"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT", ""),
                api_key=os.getenv("LLM_API_KEY", ""),
                temperature=temperature
            )

        elif provider == "openai":
            print("[INFO] Using OpenAI for LangChain ReAct agent")
            return ChatOpenAI(
                base_url=os.getenv("BASE_URL", "https://api.openai.com/v1"),
                api_key=os.getenv("LLM_API_KEY", ""),
                model=os.getenv("MODEL", "gpt-4o-mini"),
                temperature=temperature
            )

        elif provider == "groq":
            print("[INFO] Using Groq for LangChain ReAct agent")
            return ChatGroq(
                api_key=os.getenv("LLM_API_KEY", ""),
                model=os.getenv("MODEL", "llama3-8b-8192"),
                temperature=temperature
            )

        elif provider == "gemini":
            print("[INFO] Using Google Gemini for LangChain ReAct agent")
            return ChatGoogleGenerativeAI(
                model=os.getenv("GOOGLE_MODELS", "gemini-1.5-flash"),
                api_key=os.getenv("GOOGLE_API_KEY", ""),
                temperature=temperature
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

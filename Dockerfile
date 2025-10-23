FROM python:3.13-slim 
ARG PORT
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY="localhost,127.0.0.1"

# Set environment variables for runtime proxy settings
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=${NO_PROXY}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

COPY . .

EXPOSE ${PORT}

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

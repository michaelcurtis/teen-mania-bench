FROM python:3.12-slim

# The chat agent calls Anthropic or OpenAI models; the judge calls Anthropic.
RUN pip install --no-cache-dir anthropic==2.8.0 openai==3.51.0

WORKDIR /app

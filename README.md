# Collaborate

A Python project for AI collaboration using OpenAI and XAI SDKs.

## Setup

### 1. Python Environment

This project uses Python 3.12.8 with a virtual environment located at `.venv/`.

### 2. Dependencies

- `openai` - OpenAI API client
- `xai-sdk` - XAI SDK for AI services

### 3. Installation

The Python environment and dependencies are already configured. To verify the setup:

```bash
python test_env.py
```

### 4. Configuration

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Add your API keys to `.env`:

   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   XAI_API_KEY=your_xai_api_key_here
   ```

### 5. Usage

Run the main script to test API connections:

```bash
python src/main.py
```

## Project Structure

```text
├── src/
│   ├── __init__.py
│   └── main.py          # Main application with AI SDK integration
├── .env.example         # Environment variables template
├── requirements.txt     # Python dependencies
├── test_env.py         # Environment test script
└── README.md           # This file
```

## Features

- OpenAI API integration
- XAI SDK integration
- Environment variable management
- Modular project structure

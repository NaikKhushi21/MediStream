#!/bin/bash

# MediStream Backend Startup Script

echo "🚀 Starting MediStream Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads checkpoints

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
fi

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium || echo "⚠️  Playwright installation skipped (optional)"

# Start the server
echo "✅ Starting FastAPI server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000

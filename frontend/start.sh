#!/bin/bash

# MediStream Frontend Startup Script

echo "🚀 Starting MediStream Frontend..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start the dev server
echo "✅ Starting Vite dev server..."
npm run dev

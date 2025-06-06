#!/bin/bash

echo "Setting up Pictures - Phase 1"
echo "FastAPI + Supabase + Next.js Stack"

# Backend setup
echo "Setting up backend..."
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt

# Copy environment file
cp .env.example .env

echo ""
echo "Setting up frontend..."
cd frontend

# Install Node.js dependencies
npm install

# Create frontend .env.local
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

cd ..

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env with your API keys (especially Supabase credentials)"
echo "2. In Supabase SQL editor, run the table creation SQL"
echo "3. Start the backend: source venv/bin/activate && uvicorn app.main:app --reload"
echo "4. Start the frontend: cd frontend && npm run dev"
echo ""
echo "🔗 URLs:"
echo "  • Frontend: http://localhost:3000"
echo "  • Backend API: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs" 
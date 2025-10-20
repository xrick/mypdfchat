#!/bin/bash
# Fix script for langchain dependency issues
# Resolves: ModuleNotFoundError: No module named 'langchain_core.pydantic_v1'

set -e  # Exit on error

echo "🔧 Fixing LangChain dependency issues..."
echo

# Step 1: Delete broken virtual environment
echo "📦 Step 1/5: Cleaning up broken virtual environment..."
if [ -d ".chatenv" ]; then
    echo "  Removing .chatenv/"
    rm -rf .chatenv
else
    echo "  No existing .chatenv found"
fi
echo

# Step 2: Create fresh virtual environment
echo "🐍 Step 2/5: Creating fresh virtual environment..."
python3 -m venv .chatenv
echo "  ✅ Virtual environment created"
echo

# Step 3: Activate and upgrade pip
echo "⬆️  Step 3/5: Activating environment and upgrading pip..."
source .chatenv/bin/activate
pip install --upgrade pip --quiet
echo "  ✅ Pip upgraded"
echo

# Step 4: Install all dependencies from requirements.txt
echo "📥 Step 4/5: Installing all dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install --no-cache-dir -r requirements.txt --quiet
    echo "  ✅ All dependencies installed from requirements.txt"
else
    # Fallback: Install manually if requirements.txt missing
    echo "  ⚠️  requirements.txt not found, installing manually..."
    pip install --no-cache-dir \
      "langchain==0.1.13" \
      "langchain-core>=0.1.33,<0.2.0" \
      "langchain-community==0.0.29" \
      "langchain-huggingface==0.0.2" \
      "langchain-text-splitters<0.1" \
      "streamlit==1.32.2" \
      "pypdf==4.1.0" \
      "sentence-transformers>=2.5" \
      --quiet
    echo "  ✅ Essential packages installed"
fi
echo

# Step 5: Verify no conflicts
echo "🔍 Step 5/5: Verifying dependency resolution..."
echo "  (Checking for conflicts...)"
echo

# Verification
echo "🧪 Verification:"
echo "  Checking langchain versions..."
python -c "
import sys
try:
    import langchain
    import langchain_core
    import langchain_community
    print(f'  ✅ langchain: {langchain.__version__}')
    print(f'  ✅ langchain-core: {langchain_core.__version__}')
    print(f'  ✅ langchain-community: {langchain_community.__version__}')
except ImportError as e:
    print(f'  ❌ Import error: {e}')
    sys.exit(1)
"

echo
echo "  Testing pydantic_v1 availability..."
python -c "
import sys
try:
    from langchain_core.pydantic_v1 import Extra
    print('  ✅ langchain_core.pydantic_v1 is available')
except ImportError:
    print('  ❌ langchain_core.pydantic_v1 NOT found')
    sys.exit(1)
"

echo
echo "  Testing app.py imports..."
python -c "
import sys
try:
    from langchain.chains.question_answering import load_qa_chain
    from langchain.chains import ConversationalRetrievalChain
    print('  ✅ All required imports work')
except ImportError as e:
    print(f'  ❌ Import error: {e}')
    sys.exit(1)
"

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Fix completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source .chatenv/bin/activate"
echo
echo "  2. Run your app:"
echo "     streamlit run app.py"
echo
echo "For more details, see: claudedocs/langchain-dependency-fix.md"

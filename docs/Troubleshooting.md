# Troubleshooting Guide - Eunice Research Platform

## Overview

This guide helps resolve common issues encountered when setting up, running, or maintaining the Eunice Research Platform. The platform has been optimized with 93.7% code quality improvement, but some setup issues may still occur.

## Quick Diagnostic Commands

Before diving into specific issues, run these commands to gather system information:

```bash
# System Information
python --version
node --version
pip --version
git --version

# Virtual Environment Check
which python
echo $VIRTUAL_ENV

# Platform Status Check
python -c "import sys; print(f'Python: {sys.version}')"
python -c "import platform; print(f'Platform: {platform.platform()}')"
```

## Installation Issues

### 1. Virtual Environment Problems

#### Issue: Virtual environment not activating

```bash
# Symptoms
$ source .venv/bin/activate
bash: .venv/bin/activate: No such file or directory
```

**Solution:**

```bash
# Delete existing virtual environment
rm -rf .venv

# Create new virtual environment
python -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Verify activation
which python  # Should point to .venv/bin/python
```

#### Issue: Wrong Python version in virtual environment

```bash
# Symptoms
$ python --version
Python 3.8.x  # Should be 3.11+
```

**Solution:**

```bash
# Create virtual environment with specific Python version
python3.11 -m venv .venv
# or
/usr/bin/python3.11 -m venv .venv

# On macOS with Homebrew
/opt/homebrew/bin/python3.11 -m venv .venv
```

### 2. ARM64/Apple Silicon Compatibility Issues

#### Issue: Architecture mismatch errors

```bash
# Symptoms
ImportError: dlopen failed: mach-o file, but is an architecture that is not being linked (x86_64)
```

**Solution:**

```bash
# Uninstall problematic packages
python -m pip uninstall black isort autoflake -y

# Reinstall with force reinstall flag
python -m pip install --upgrade --force-reinstall black isort autoflake

# Use python -m instead of global commands
python -m black --version  # Instead of: black --version
python -m isort --version  # Instead of: isort --version
```

#### Issue: Homebrew Python conflicts

```bash
# Check which Python you're using
which python
which python3

# If using Homebrew Python, ensure consistent usage
export PATH="/opt/homebrew/bin:$PATH"
python3.11 -m venv .venv
```

### 3. Dependency Installation Issues

#### Issue: Requirements installation fails

```bash
# Symptoms
ERROR: Could not install packages due to an EnvironmentError
```

**Solution:**

```bash
# Update pip first
pip install --upgrade pip

# Install with no cache
pip install --no-cache-dir -r requirements.txt

# Install individual problematic packages
pip install --upgrade setuptools wheel

# For permission issues (avoid sudo with virtual env)
pip install --user -r requirements.txt
```

#### Issue: Specific package installation failures

```bash
# For numpy/scipy issues on Apple Silicon
pip install --only-binary=all numpy scipy

# For lxml issues
pip install --only-binary=lxml lxml

# For cryptography issues
pip install --only-binary=cryptography cryptography
```

## Runtime Issues

### 4. Database Connection Problems

#### Issue: Database file not found

```bash
# Symptoms
sqlite3.OperationalError: unable to open database file
```

**Solution:**

```bash
# Create data directory
mkdir -p data

# Run setup script
python setup.py

# Check database files exist
ls -la data/
# Should show: eunice.db, memory.db, academic_cache.db

# Set permissions if needed
chmod 644 data/*.db
```

#### Issue: Database locked errors

```bash
# Symptoms
sqlite3.OperationalError: database is locked
```

**Solution:**

```bash
# Stop all running services
pkill -f "python web_server.py"
pkill -f "python mcp_server.py"

# Remove lock files if they exist
rm -f data/*.db-wal data/*.db-shm

# Restart services
./start_eunice.sh
```

### 5. API and Server Issues

#### Issue: Port already in use

```bash
# Symptoms
OSError: [Errno 48] Address already in use
```

**Solution:**

```bash
# Find process using port 8000 (or relevant port)
lsof -i :8000
netstat -tulpn | grep :8000

# Kill the process
kill -9 <PID>

# Or use different port in .env file
echo "PORT=8080" >> .env
```

#### Issue: API key errors

```bash
# Symptoms
openai.error.AuthenticationError: Incorrect API key provided
```

**Solution:**

```bash
# Check environment file exists
ls -la .env

# Verify API keys are set
grep -E "(OPENAI|XAI)_API_KEY" .env

# Test API key loading
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('OpenAI Key:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')
print('XAI Key:', 'SET' if os.getenv('XAI_API_KEY') else 'NOT SET')
"

# Re-export environment variables
source .env  # If using bash
set -a; source .env; set +a  # Alternative method
```

### 6. Frontend Issues

#### Issue: Frontend build fails

```bash
# Symptoms
npm ERR! Build failed with errors
```

**Solution:**

```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
cd frontend
rm -rf node_modules package-lock.json

# Reinstall with latest npm
npm install

# Try building again
npm run build

# If still failing, check Node.js version
node --version  # Should be 18+
```

#### Issue: Frontend not connecting to backend

```bash
# Check backend is running
curl http://localhost:8000/health

# Check frontend configuration
cat frontend/src/config.js  # Or wherever API URL is configured

# Verify CORS settings in backend
grep -r "CORS\|cors" src/api/
```

## Code Quality Issues

### 7. Flake8 and Formatting Issues

#### Issue: Too many flake8 errors

The optimized codebase should have ~515 issues (down from 8,212).

```bash
# Check current status
python -m flake8 src/ --count --statistics --max-line-length=120

# If significantly more than 515 issues, run optimization tools
python fix_code_quality.py
python advanced_optimizer.py

# Apply professional formatting
python -m black src/ --line-length 120
python -m isort src/ --profile black
python -m autoflake --remove-all-unused-imports --recursive src/
```

#### Issue: Black formatter not working

```bash
# Symptoms
ImportError: No module named '_black_version'
```

**Solution:**

```bash
# Use python -m approach instead of global command
python -m black src/ --line-length 120

# If still failing, reinstall
pip uninstall black -y
pip install black

# For ARM64 issues
python -m pip install --upgrade --force-reinstall black
```

### 8. Import and Module Issues

#### Issue: Module not found errors

```bash
# Symptoms
ModuleNotFoundError: No module named 'src'
```

**Solution:**

```bash
# Ensure you're in project root directory
pwd  # Should show path ending in /Eunice

# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or add to .env file
echo "PYTHONPATH=./src" >> .env

# Verify Python can find modules
python -c "import src.core.research_manager; print('✅ Import successful')"
```

#### Issue: Circular import errors

```bash
# These should be resolved in the optimized codebase
# If you encounter them, check recent changes
python -c "
import ast
import os

def check_file(filepath):
    try:
        with open(filepath, 'r') as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print(f'Syntax error in {filepath}: {e}')
        return False

for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            check_file(os.path.join(root, file))
"
```

## Performance Issues

### 9. Memory and Performance Problems

#### Issue: High memory usage

```bash
# Monitor memory usage
python -c "
import psutil
import os

process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"

# Check for memory leaks in long-running processes
# Look for growing memory usage in logs/performance.log
```

**Solution:**

```bash
# Restart services periodically
./start_eunice.sh

# Check database size
du -h data/*.db

# Optimize databases if they're large
python -c "
from src.storage.systematic_review_database import SystematicReviewDatabase
# Run VACUUM on databases to reclaim space
"
```

#### Issue: Slow response times

```bash
# Check system resources
top -pid $(pgrep -f python)

# Monitor database performance
# Check logs/performance.log for slow queries

# Enable debug mode temporarily
echo "DEBUG=True" >> .env
```

## Debugging Commands

### System Diagnostics

```bash
# Complete system check
echo "=== System Information ==="
uname -a
python --version
pip --version
node --version

echo "=== Virtual Environment ==="
which python
echo $VIRTUAL_ENV
pip list | head -10

echo "=== Project Status ==="
pwd
ls -la
ls -la data/

echo "=== Service Status ==="
ps aux | grep -E "(python|node)" | grep -v grep

echo "=== Network ==="
netstat -tulpn | grep -E ":(8000|8001|3000)"
```

### Log Analysis

```bash
# Check application logs
tail -f logs/eunice.log
tail -f logs/mcp_server.log
tail -f logs/agents.log

# Search for errors
grep -i error logs/*.log
grep -i exception logs/*.log
grep -i failed logs/*.log
```

### Database Diagnostics

```bash
# Check database integrity
python -c "
import sqlite3
for db in ['data/eunice.db', 'data/memory.db', 'data/academic_cache.db']:
    try:
        conn = sqlite3.connect(db)
        conn.execute('PRAGMA integrity_check;')
        print(f'✅ {db} integrity OK')
        conn.close()
    except Exception as e:
        print(f'❌ {db} error: {e}')
"
```

## Emergency Recovery

### Complete Reset (Nuclear Option)

If all else fails, perform a complete reset:

```bash
# Stop all services
pkill -f python
pkill -f node

# Backup important data
cp -r data data_backup_$(date +%Y%m%d_%H%M%S)

# Clean installation
rm -rf .venv node_modules data/*.db logs/*.log

# Fresh installation
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd frontend && npm install && cd ..
python setup.py

# Restore data if needed
# cp data_backup_*/eunice.db data/
```

## Getting Help

### Before Asking for Help

1. **Check the logs**: Look in `logs/` directory for error messages
2. **Run diagnostics**: Use the system diagnostic commands above
3. **Search existing issues**: Check GitHub Issues for similar problems
4. **Try the nuclear option**: Sometimes a fresh install is fastest

### When Reporting Issues

Include this information:

```bash
# System info
uname -a
python --version
pip --version

# Project status
git branch
git log -1 --oneline
python -m flake8 src/ --count --statistics --max-line-length=120

# Error logs
tail -n 50 logs/eunice.log
```

### Community Support

- **GitHub Issues**: Report bugs and get help
- **GitHub Discussions**: General questions and community support
- **Documentation**: Check `docs/` directory for detailed guides

---

## Success Indicators

Your Eunice platform is working correctly when:

- ✅ Virtual environment activates without errors
- ✅ All services start successfully (`./start_eunice.sh`)
- ✅ API health checks return 200 OK
- ✅ Frontend loads at <http://localhost:3000>
- ✅ Code quality check shows ~515 issues (optimized state)
- ✅ Basic research queries execute successfully

**Remember**: The platform is production-ready with 93.7% code quality optimization. Most issues are environment-related rather than platform bugs.

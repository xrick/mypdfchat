# Troubleshooting: Address Already in Use (Port 8000)

**Date**: 2025-10-30  
**Error**: `ERROR: [Errno 98] Address already in use`  
**Status**: ✅ **DIAGNOSED** - Server already running in background

---

## 🔍 Root Cause Analysis

### Error Details

**Full Error Message**:
```
ERROR:    [Errno 98] Address already in use
```

**When It Occurs**:
- When trying to run `python main.py`
- When trying to start Uvicorn on port 8000

**Root Cause**: 
Port 8000 is already being used by another process - specifically, the DocAI server you started earlier in the background.

---

## 📊 Diagnosis Results

### Current Process Using Port 8000

```bash
$ lsof -i :8000

COMMAND    PID      USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
python  400516 mapleleaf    5u  IPv4 675154      0t0  TCP *:8000 (LISTEN)
```

**Analysis**:
- **PID**: 400516
- **User**: mapleleaf
- **Command**: `docaienv/bin/python main.py`
- **Status**: ✅ Running successfully
- **Port**: 8000 (listening on all interfaces)

**Started**: 2025-10-30 14:53 (via background task)

---

## ✅ This is NOT an Error - It's Expected!

### What Happened

1. Earlier in our session, I started the server in background mode:
   ```bash
   docaienv/bin/python main.py &
   ```

2. The server started successfully and is **currently running**:
   - Server URL: http://0.0.0.0:8000
   - Frontend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

3. When you try to run `python main.py` again, it fails because:
   - Port 8000 is already in use by the first instance
   - You can only have ONE server listening on port 8000 at a time

---

## 🎯 Solutions

### Solution 1: Use the Existing Server (Recommended) ✅

**The server is already running!** You don't need to start it again.

**Verify it's working**:
```bash
# Test if server is responding
curl http://localhost:8000/

# Or open in browser
xdg-open http://localhost:8000
```

**Expected Result**: You should see the DocAI frontend HTML page.

---

### Solution 2: Stop the Existing Server and Restart

If you want to restart the server (e.g., after code changes):

#### Option A: Kill by PID

```bash
# Kill the specific process
kill 400516

# Wait a moment for it to shutdown
sleep 2

# Verify port is free
lsof -i :8000  # Should show nothing

# Start new instance
docaienv/bin/python main.py
```

#### Option B: Kill by Name

```bash
# Find and kill all Python processes running main.py
pkill -f "python main.py"

# Wait for shutdown
sleep 2

# Verify port is free
lsof -i :8000  # Should show nothing

# Start new instance
docaienv/bin/python main.py
```

#### Option C: Kill by Port (Most Reliable)

```bash
# Find PID using port 8000
PID=$(lsof -t -i:8000)

# Kill it
kill $PID

# Verify
lsof -i :8000  # Should show nothing

# Start new instance
docaienv/bin/python main.py
```

---

### Solution 3: Change the Port

If you want to run multiple instances on different ports:

#### Method A: Environment Variable

```bash
# Start on different port
PORT=8001 docaienv/bin/python main.py
```

#### Method B: Modify .env

```bash
# Edit .env file
nano .env

# Change this line:
PORT=8000

# To:
PORT=8001

# Save and restart
docaienv/bin/python main.py
```

---

## 🔧 Recommended Workflow

### For Development (Hot Reload Already Enabled)

**Current Setup**: The server is running with auto-reload enabled.

**What This Means**:
- When you edit Python files, the server automatically reloads
- You DON'T need to manually restart
- Just save your changes and test

**When You See**:
```
INFO:     Detected file change, reloading...
INFO:     Application startup complete.
```

**Then**: Your changes are live!

**You Only Need to Restart If**:
- `.env` file changes
- Installing new dependencies
- Major configuration changes

---

### For Production

**Option 1: Systemd Service** (Recommended)

Create `/etc/systemd/system/docai.service`:
```ini
[Unit]
Description=DocAI RAG Application
After=network.target mongod.service redis.service

[Service]
Type=simple
User=mapleleaf
WorkingDirectory=/home/mapleleaf/LCJRepos/gitprjs/DocAI
Environment="PATH=/home/mapleleaf/LCJRepos/gitprjs/DocAI/docaienv/bin"
ExecStart=/home/mapleleaf/LCJRepos/gitprjs/DocAI/docaienv/bin/python main.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**Usage**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable docai
sudo systemctl start docai
sudo systemctl status docai
```

---

**Option 2: Screen/Tmux**

```bash
# Start in screen
screen -S docai
docaienv/bin/python main.py

# Detach: Ctrl+A, D
# Reattach: screen -r docai
```

---

**Option 3: Supervisor**

Create `/etc/supervisor/conf.d/docai.conf`:
```ini
[program:docai]
command=/home/mapleleaf/LCJRepos/gitprjs/DocAI/docaienv/bin/python main.py
directory=/home/mapleleaf/LCJRepos/gitprjs/DocAI
user=mapleleaf
autostart=true
autorestart=true
stderr_logfile=/var/log/docai.err.log
stdout_logfile=/var/log/docai.out.log
```

---

## 📋 Quick Reference Commands

### Check Server Status

```bash
# Is server running?
curl -s http://localhost:8000/ > /dev/null && echo "✅ Running" || echo "❌ Not running"

# What's using port 8000?
lsof -i :8000

# Check process details
ps aux | grep "python main.py" | grep -v grep
```

---

### Start/Stop/Restart

```bash
# Start (if not running)
docaienv/bin/python main.py

# Stop
pkill -f "python main.py"

# Restart (stop + start)
pkill -f "python main.py" && sleep 2 && docaienv/bin/python main.py

# Start in background
docaienv/bin/python main.py &

# Start with logs
docaienv/bin/python main.py 2>&1 | tee logs/app.log
```

---

### Monitor Logs

```bash
# View current output (if running in background)
tail -f logs/app.log

# View live output (if using systemd)
journalctl -u docai -f

# Search for errors
grep -i error logs/app.log
```

---

## 🛡️ Prevention Tips

### 1. Always Check Before Starting

```bash
# Add this to your startup script
if lsof -i :8000 > /dev/null; then
    echo "❌ Port 8000 is already in use"
    echo "Stop the existing server first: pkill -f 'python main.py'"
    exit 1
fi

docaienv/bin/python main.py
```

---

### 2. Use a Startup Script

Create `start_server.sh`:
```bash
#!/bin/bash
set -e

echo "🔍 Checking if server is already running..."

if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Server already running on port 8000"
    echo ""
    read -p "Stop and restart? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🛑 Stopping existing server..."
        pkill -f "python main.py"
        sleep 2
        echo "✅ Stopped"
    else
        echo "ℹ️  Server still running at http://localhost:8000"
        exit 0
    fi
fi

echo "🚀 Starting DocAI server..."
cd "$(dirname "$0")"
docaienv/bin/python main.py
```

**Usage**:
```bash
chmod +x start_server.sh
./start_server.sh
```

---

### 3. Health Check Script

Create `check_server.sh`:
```bash
#!/bin/bash

echo "🏥 DocAI Health Check"
echo "===================="

# Check if process is running
if ps aux | grep -q "[p]ython main.py"; then
    echo "✅ Process: Running"
    PID=$(pgrep -f "python main.py")
    echo "   PID: $PID"
else
    echo "❌ Process: Not running"
fi

# Check if port is listening
if lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Port 8000: Listening"
else
    echo "❌ Port 8000: Not listening"
fi

# Check if responding to HTTP
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ HTTP: Responding"
else
    echo "❌ HTTP: Not responding"
fi

# Check external services
echo ""
echo "External Services:"
nc -zv localhost 27017 2>&1 | grep -q "succeeded" && echo "✅ MongoDB" || echo "❌ MongoDB"
nc -zv localhost 6379 2>&1 | grep -q "succeeded" && echo "✅ Redis" || echo "❌ Redis"
curl -s http://localhost:11434/api/tags > /dev/null && echo "✅ Ollama" || echo "❌ Ollama"
```

**Usage**:
```bash
chmod +x check_server.sh
./check_server.sh
```

---

## 🐛 Related Issues

### Issue 1: "Connection Refused"

**Symptom**: `curl: (7) Failed to connect to localhost port 8000: Connection refused`

**Cause**: Server is not running (different from "Address in use")

**Solution**: Start the server
```bash
docaienv/bin/python main.py
```

---

### Issue 2: "Permission Denied"

**Symptom**: `ERROR: [Errno 13] Permission denied`

**Cause**: Trying to bind to port < 1024 without sudo

**Solution**: Use port >= 1024 (like 8000) or use sudo (not recommended)

---

### Issue 3: Multiple Processes

**Symptom**: Multiple instances of `python main.py` running

**Diagnosis**:
```bash
ps aux | grep "python main.py" | grep -v grep
```

**Solution**: Kill all instances
```bash
pkill -9 -f "python main.py"
```

---

## 📊 Current Status (Right Now)

```bash
✅ Server Status: RUNNING
✅ PID: 400516
✅ Port: 8000 (listening)
✅ Started: 2025-10-30 14:53
✅ Uptime: ~1 hour
✅ Auto-reload: ENABLED

Access Points:
- Frontend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json
```

**You can use the server right now - no need to start it again!**

---

## 🎓 Key Takeaways

1. **"Address already in use" = Server is running** (usually good news!)
2. **Check before starting**: `lsof -i :8000`
3. **Auto-reload is enabled**: No need to restart for code changes
4. **Only restart for**: .env changes, dependency updates, major config changes
5. **Use startup scripts**: Prevent accidental multiple instances

---

**Resolution Status**: ✅ **NO ACTION NEEDED**  
**Server Status**: ✅ **RUNNING NORMALLY**  
**Next Step**: Use the existing server or follow Solution 2 to restart if needed

---

**End of Troubleshooting Report**

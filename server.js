const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3001;

// Store active processes
const activeProcesses = new Map();

// Store event scanner process
let eventScannerProcess = null;

// Middleware
app.use(cors());
app.use(express.json());

// Serve static files from build directory if it exists
const buildPath = path.join(__dirname, 'build');
if (require('fs').existsSync(buildPath)) {
  app.use(express.static(buildPath));
}

// API endpoint để chạy scrape scripts
app.post('/api/scrape', async (req, res) => {
  const { script } = req.body;
  const requestId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
  
  console.log(`[SERVER] New scrape request ${requestId} for script: ${script}`);
  
  if (!script) {
    return res.status(400).json({ error: 'Script name is required' });
  }

  const validScripts = ['uma-scrape.js', 'support-scrape.js', 'skill-scrape.js', 'scenario-scrape.js'];
  if (!validScripts.includes(script)) {
    return res.status(400).json({ error: 'Invalid script name' });
  }

  // Set headers for streaming response
  res.setHeader('Content-Type', 'text/plain');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering
  res.setHeader('Transfer-Encoding', 'chunked'); // Ensure chunked transfer

  const scriptPath = path.join(__dirname, 'scrape', script);
  
  // Check if script file exists
  if (!require('fs').existsSync(scriptPath)) {
    res.write(JSON.stringify({
      message: `Không tìm thấy file ${script}`,
      type: 'error'
    }) + '\n');
    return res.end();
  }

  // Spawn the Node.js process
  const child = spawn('node', [scriptPath], {
    cwd: path.join(__dirname, 'scrape'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  // Store the process for potential cancellation
  activeProcesses.set(requestId, child);

  // Log child process PID
  console.log(`[SERVER][${requestId}] Spawned child process PID: ${child.pid} for script: ${script}`);

  // Track if we've already sent completion message
  let completionSent = false;

  // Send initial log with request ID
  res.write(JSON.stringify({
    message: `Bắt đầu chạy ${script}...`,
    type: 'info',
    requestId: requestId
  }) + '\n');

  // Handle stdout (normal output)
  child.stdout.on('data', (data) => {
    const output = data.toString();
    const lines = output.split('\n').filter(line => line.trim());
    lines.forEach(line => {
      console.log(`[STDOUT][${requestId}][${script}]`, line);
      res.write(JSON.stringify({
        message: line,
        type: 'info'
      }) + '\n');
    });
  });

  // Handle stderr (error output)
  child.stderr.on('data', (data) => {
    const error = data.toString();
    const lines = error.split('\n').filter(line => line.trim());
    lines.forEach(line => {
      console.error(`[STDERR][${requestId}][${script}]`, line);
      res.write(JSON.stringify({
        message: line,
        type: 'error'
      }) + '\n');
    });
  });

  // Handle process exit (this fires when the process exits)
  child.on('exit', (code, signal) => {
    console.log(`[SERVER][${requestId}] Child process for ${script} exited with code: ${code}, signal: ${signal}`);
    
    // Remove from active processes
    activeProcesses.delete(requestId);
    
    if (!completionSent) {
      completionSent = true;
      
      if (code === 0) {
        res.write(JSON.stringify({
          message: `${script} hoàn thành thành công!`,
          type: 'success'
        }) + '\n');
      } else if (code !== null) {
        res.write(JSON.stringify({
          message: `${script} kết thúc với mã lỗi: ${code}`,
          type: 'error'
        }) + '\n');
      } else if (signal) {
        res.write(JSON.stringify({
          message: `${script} bị dừng bởi signal: ${signal}`,
          type: 'error'
        }) + '\n');
      } else {
        res.write(JSON.stringify({
          message: `${script} kết thúc không bình thường`,
          type: 'error'
        }) + '\n');
      }
      res.end();
    }
  });

  // Handle process close (this fires after exit, but we'll use exit for consistency)
  child.on('close', (code, signal) => {
    console.log(`[SERVER][${requestId}] Child process for ${script} closed with code: ${code}, signal: ${signal}`);
    
    // Remove from active processes
    activeProcesses.delete(requestId);
    
    // Only send completion message if exit event didn't fire
    if (!completionSent) {
      completionSent = true;
      
      if (code === 0) {
        res.write(JSON.stringify({
          message: `${script} hoàn thành thành công!`,
          type: 'success'
        }) + '\n');
      } else if (code !== null) {
        res.write(JSON.stringify({
          message: `${script} kết thúc với mã lỗi: ${code}`,
          type: 'error'
        }) + '\n');
      } else if (signal) {
        res.write(JSON.stringify({
          message: `${script} bị dừng bởi signal: ${signal}`,
          type: 'error'
        }) + '\n');
      } else {
        res.write(JSON.stringify({
          message: `${script} kết thúc không bình thường`,
          type: 'error'
        }) + '\n');
      }
      res.end();
    }
  });

  // Handle process errors
  child.on('error', (error) => {
    console.error(`[SERVER][${requestId}] Child process error:`, error);
    if (!completionSent) {
      completionSent = true;
      res.write(JSON.stringify({
        message: `Lỗi khi chạy ${script}: ${error.message}`,
        type: 'error'
      }) + '\n');
      res.end();
    }
  });

  // Handle client disconnect
  req.on('close', () => {
    console.log(`[SERVER][${requestId}] Client disconnected for ${script}, but keeping process alive`);
    // Don't kill the process immediately on client disconnect
    // Let the process complete naturally
    // Only kill if it's been running for too long
    setTimeout(() => {
      if (!child.killed) {
        console.log(`[SERVER][${requestId}] Killing long-running process for ${script} after client disconnect`);
        child.kill('SIGTERM');
        activeProcesses.delete(requestId);
      }
    }, 12000000); // Wait 200 minutes before killing for scraping scripts
  });

  // Handle client abort
  req.on('aborted', () => {
    console.log(`[SERVER][${requestId}] Client aborted request for ${script}`);
    // Similar to close, but log differently
  });
});

// API endpoint để dừng script đang chạy
app.post('/api/stop-scrape', async (req, res) => {
  const { requestId } = req.body;
  
  console.log(`[SERVER] Stop request for ${requestId}`);
  
  if (!requestId) {
    return res.status(400).json({ error: 'Request ID is required' });
  }

  const child = activeProcesses.get(requestId);
  if (!child) {
    return res.status(404).json({ error: 'Process not found or already completed' });
  }

  try {
    child.kill('SIGTERM');
    activeProcesses.delete(requestId);
    console.log(`[SERVER] Successfully stopped process ${requestId}`);
    res.json({ message: 'Script đã được dừng thành công' });
  } catch (error) {
    console.error(`[SERVER] Error stopping process ${requestId}:`, error);
    res.status(500).json({ error: 'Lỗi khi dừng script' });
  }
});

// API endpoint để lấy danh sách process đang chạy
app.get('/api/active-processes', (req, res) => {
  const processes = Array.from(activeProcesses.keys());
  res.json({ activeProcesses: processes });
});

// Test endpoint
app.get('/api/test', (req, res) => {
  res.json({ message: 'Server is running!' });
});

// Event Scanner API endpoints - Direct integration
app.post('/api/start-event-scanner', async (req, res) => {
  try {
    const data = req.body || {};
    console.log('[SERVER] Starting event scanner with data:', data);
    
    // Check if scanner is already running
    if (eventScannerProcess && eventScannerProcess.exitCode === null) {
      return res.status(400).json({ 
        success: false, 
        error: 'Event scanner is already running' 
      });
    }
    
    // Save context data
    const contextData = {
      character: data.character,
      scenario: data.scenario,
      cards: data.cards || [],
      timestamp: data.timestamp
    };
    
    const contextPath = path.join(__dirname, 'event_scanner', 'scanner_context.json');
    require('fs').writeFileSync(contextPath, JSON.stringify(contextData, null, 2), 'utf8');
    
    // Start Python event scanner
    const scannerPath = path.join(__dirname, 'event_scanner', 'event_scanner.py');
    
    // Try different Python commands for Windows compatibility
    const pythonCommands = ['python', 'py', 'python3'];
    let pythonCommand = null;
    
    for (const cmd of pythonCommands) {
      try {
        console.log(`[SERVER] Trying Python command: ${cmd}`);
        const proc = spawn(cmd, [scannerPath], {
          cwd: path.join(__dirname, 'event_scanner'),
          stdio: ['pipe', 'pipe', 'pipe'],
          env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
        });

        let errored = false;
        proc.stderr.once('data', (data) => {
          const msg = data.toString();
          if (msg.includes('Python was not found')) {
            errored = true;
            proc.kill();
          }
        });

        // Đợi 500ms để kiểm tra lỗi
        await new Promise(resolve => setTimeout(resolve, 500));
        if (!errored && proc.pid) {
          eventScannerProcess = proc;
          pythonCommand = cmd;
          console.log(`[SERVER] Successfully started with command: ${cmd}`);
          break;
        }
      } catch (error) {
        console.log(`[SERVER] Failed with command ${cmd}:`, error.message);
        continue;
      }
    }
    
    if (!eventScannerProcess || !eventScannerProcess.pid) {
      throw new Error('Could not start Python process. Please ensure Python is installed and accessible.');
    }
    
    console.log(`[SERVER] Event scanner started with PID: ${eventScannerProcess.pid} using command: ${pythonCommand}`);
    
    // Handle scanner output
    eventScannerProcess.stdout.on('data', (data) => {
      console.log('[EVENT SCANNER]', data.toString().trim());
    });
    
    eventScannerProcess.stderr.on('data', (data) => {
      console.error('[EVENT SCANNER ERROR]', data.toString().trim());
    });
    
    eventScannerProcess.on('exit', (code, signal) => {
      console.log(`[SERVER] Event scanner exited with code: ${code}, signal: ${signal}`);
      eventScannerProcess = null;
      
      // Clean up context file
      if (require('fs').existsSync(contextPath)) {
        require('fs').unlinkSync(contextPath);
      }
    });
    
    eventScannerProcess.on('error', (error) => {
      console.error('[SERVER] Event scanner process error:', error);
      eventScannerProcess = null;
    });
    
    res.json({ 
      success: true, 
      message: 'Event scanner started successfully',
      pid: eventScannerProcess.pid,
      pythonCommand: pythonCommand
    });
    
  } catch (error) {
    console.error('[SERVER] Error starting event scanner:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

app.post('/api/stop-event-scanner', async (req, res) => {
  try {
    if (!eventScannerProcess) {
      return res.status(404).json({ 
        success: false, 
        error: 'Event scanner is not running' 
      });
    }
    
    console.log('[SERVER] Stopping event scanner...');
    eventScannerProcess.kill('SIGTERM');
    
    // Wait a bit for graceful shutdown
    setTimeout(() => {
      if (eventScannerProcess && eventScannerProcess.exitCode === null) {
        console.log('[SERVER] Force killing event scanner...');
        eventScannerProcess.kill('SIGKILL');
      }
    }, 5000);
    
    eventScannerProcess = null;
    
    // Clean up context file
    const contextPath = path.join(__dirname, 'event_scanner', 'scanner_context.json');
    if (require('fs').existsSync(contextPath)) {
      require('fs').unlinkSync(contextPath);
    }
    
    res.json({ 
      success: true, 
      message: 'Event scanner stopped successfully' 
    });
    
  } catch (error) {
    console.error('[SERVER] Error stopping event scanner:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

app.get('/api/scanner-status', (req, res) => {
  const isRunning = eventScannerProcess && eventScannerProcess.exitCode === null;
  
  res.json({
    scanning: isRunning,
    process_running: isRunning,
    pid: isRunning ? eventScannerProcess.pid : null
  });
});

// Serve React app for all other routes (only if build exists)
app.get('*', (req, res) => {
  // Don't serve React app for API routes
  if (req.path.startsWith('/api/')) {
    return res.status(404).json({ error: 'API endpoint not found' });
  }
  
  if (require('fs').existsSync(buildPath)) {
    res.sendFile(path.join(buildPath, 'index.html'));
  } else {
    res.json({ message: 'Server is running but React app is not built. Run "npm run build" first.' });
  }
});

app.listen(PORT, () => {
  console.log(`Server đang chạy trên port ${PORT}`);
  console.log(`Truy cập: http://localhost:${PORT}`);
  console.log(`API test: http://localhost:${PORT}/api/test`);
}); 
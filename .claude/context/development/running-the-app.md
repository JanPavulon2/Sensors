# Running the Diuna Application

## Quick Start

### Backend (Main Application + API)
```bash
# Navigate to src directory
cd /home/jp2/Projects/diuna/src

# Run with sudo (required for WS281x LED library)
sudo /home/jp2/Projects/diuna/diunaenv/bin/python3 main_asyncio.py
```

**Why sudo?** The ws281x library requires root access to control GPIO pins on the Raspberry Pi.

### Frontend (React Dashboard)
```bash
# Navigate to project root
cd /home/jp2/Projects/diuna

# Go to frontend directory
cd frontend

# Install dependencies (if needed)
npm install

# Run development server
npm run dev
```

## Complete Setup
```bash
# Terminal 1: Backend
cd /home/jp2/Projects/diuna/src
sudo /home/jp2/Projects/diuna/diunaenv/bin/python3 main_asyncio.py

# Terminal 2: Frontend
cd /home/jp2/Projects/diuna/frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`
The API will be available at `http://localhost:8000`
The WebSocket endpoints will be at `ws://localhost:8000/ws/*`

## Troubleshooting
- **"No module named 'lifecycle'"**: Make sure you're in the `src` directory
- **"Permission denied"**: Use `sudo` for the backend
- **WebSocket connection failed**: Ensure the backend is running and listening on port 8000

# Diuna Frontend

A professional web-based LED animation design and control application built with React, TypeScript, and Vite.

## 🎯 Overview

Diuna Frontend provides real-time LED visualization, zone control, animation management, and system monitoring for the Diuna LED Control System backend.

**Tech Stack:**
- **React 18.2+** - Modern hooks-based UI framework
- **TypeScript 5.0+** - Type-safe development
- **Vite 5.0+** - Lightning-fast build tool
- **Tailwind CSS 3.4+** - Utility-first styling
- **Zustand 4.5+** - Lightweight state management
- **TanStack Query v5** - Server state & caching
- **Socket.IO Client** - Real-time WebSocket communication
- **React Konva** - 2D canvas rendering for LED visualization
- **Framer Motion** - Smooth animations

## 📋 Prerequisites

- **Node.js** 18+ ([download](https://nodejs.org))
- **npm** 9+ or **yarn**
- Modern browser (Chrome, Firefox, Safari, Edge)

## 🚀 Getting Started

### 1. Installation

```bash
# Install dependencies
npm install
```

### 2. Environment Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Update with your backend URLs:

```env
VITE_API_URL=http://localhost:8000/api
VITE_WEBSOCKET_URL=ws://localhost:8000
VITE_LOG_LEVEL=info
```

### 3. Development Server

Start the development server with HMR:

```bash
npm run dev
```

Available at **http://localhost:5173**

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   ├── pages/          # Route pages
│   ├── hooks/          # Custom React hooks
│   ├── stores/         # Zustand state stores
│   ├── services/       # API and WebSocket clients
│   ├── types/          # TypeScript definitions
│   ├── utils/          # Utility functions
│   ├── config/         # App configuration
│   ├── styles/         # Global styles
│   ├── App.tsx         # Root component
│   └── main.tsx        # Entry point
├── public/             # Static assets
├── tailwind.config.js  # Tailwind CSS config
├── vite.config.ts      # Vite config
└── README.md           # This file
```

## 🛠️ Development Commands

```bash
# Development server
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix

# Code formatting
npm run format

# Testing
npm run test
npm run test:ui
npm run test:coverage

# Production build
npm run build

# Preview build
npm run preview
```

## 🎨 Design System

### Colors (Dark Theme)

- **Background:** `#0A0A0A` → `#141414` → `#1E1E1E`
- **Text:** `#FFFFFF` → `#A1A1A1` → `#6B6B6B`
- **Accent:** `#00E5FF` (Cyan LED glow)
- **Status:** Green/Yellow/Red/Blue

### Spacing

8px grid: `p-2` (8px), `p-4` (16px), `p-6` (24px), `p-8` (32px)

## 🔌 API Integration

### REST API

```typescript
import { api } from '@/services/api';

// Example: Update zone color
await api.put('/zones/floor/color', {
  color: { mode: 'RGB', rgb: [255, 0, 0] }
});
```

### WebSocket (Real-time)

```typescript
import { websocketService } from '@/services/websocket';

// Subscribe to updates
websocketService.onZoneStateChanged((data) => {
  console.log('Zone updated:', data);
});

// Send commands
websocketService.setZoneColor('floor', { mode: 'RGB', rgb: [0, 255, 0] });
```

## 🎣 Custom Hooks

```typescript
const { data: zones, isLoading } = useZones();
const updateColorMutation = useUpdateZoneColor();
const { connected } = useWebSocket();
```

## 📦 State Management

Using Zustand for lightweight global state:

```typescript
import { useZoneStore } from '@/stores/zoneStore';
import { useSystemStore } from '@/stores/systemStore';

const zones = useZoneStore((state) => state.zones);
const connectionStatus = useSystemStore((state) => state.connectionStatus);
```

## ♿ Accessibility

- ✅ WCAG 2.1 AA compliance
- ✅ Full keyboard navigation
- ✅ Screen reader support
- ✅ 4.5:1 minimum color contrast
- ✅ Visible focus indicators

## 🚀 Deployment

### Build

```bash
npm run build
```

Creates optimized `dist/` folder.

### Serve with Backend

```python
# FastAPI
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
```

## 📚 Resources

- [React Docs](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [React Query](https://tanstack.com/query/latest)
- [Socket.IO Client](https://socket.io/docs/v4/client-api/)

## 📝 Contributing

1. Create feature branch: `git checkout -b feature/feature-name`
2. Make changes and test
3. Commit: `git commit -m "Add feature description"`
4. Push: `git push origin feature/feature-name`
5. Open Pull Request

---

Part of the **Diuna LED Control System**

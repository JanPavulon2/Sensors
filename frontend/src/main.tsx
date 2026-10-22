import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import '@/features/zones';
import '@/features/nodes';

import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

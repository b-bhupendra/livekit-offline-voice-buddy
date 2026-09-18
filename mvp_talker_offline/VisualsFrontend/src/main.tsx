import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/inter'
import './index.css'
import App from './App.tsx'
import { useBuddyStore } from './store'

// Expose store for debugging and testing
if (typeof window !== 'undefined') {
  (window as any).__BUDDY_STORE__ = useBuddyStore;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

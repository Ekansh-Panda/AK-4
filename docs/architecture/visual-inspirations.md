# Miori Core — Visual Inspirations

> Aesthetic references and UI/UX paradigms for the Miori frontends (Desktop and Remote Dashboard). Miori aims for a "Jarvis-grade," premium, glassmorphic, dynamic, and fluid interface.

## Core Aesthetic Directives
- **Glassmorphism**: Translucent panels, deep background blurs, frosted glass aesthetics.
- **Dynamic Micro-animations**: Fluid transitions on hover, state changes, and live data streaming (e.g., token generation).
- **Typography**: Modern sans-serif (e.g., Inter, SF Pro, or Geist) with high contrast and legible hierarchies.
- **Color Palette**: Deep dark mode (slate/indigo/obsidian bases) with vibrant, neon-like accents (cyan, purple, emerald) for active states.
- **Layout**: Floating modules, unconstrained panels, and minimal chrome to let the AI's content breathe.

## References

### 1. The "Command Center" Dashboard
*For the remote dashboard and task overview views.*
- **Reference**: Clean, dark-mode dashboards with glowing active metrics. 
- **Inspiration**: Futuristic flight-deck UI or modern developer tools (Vercel, Linear).
- **Key Elements**: Floating cards, subtle radial gradients indicating active status, and minimalist data visualization for system health (`/ws/status`).

### 2. Conversational Chat & Streaming
*For the primary chat interface.*
- **Reference**: High-end AI chat interfaces that break out of the standard "bubble" layout.
- **Key Elements**: 
  - Token streams should fade in fluidly rather than jumping.
  - "Thought" blocks (ReAct loops, tool executions) should be visually distinct (e.g., dim, monospaced, collapsible).
  - Artifact rendering (code, tables) should look like embedded native components.

### 3. The "Presence Orb" (Status Indicator)
*For the desktop menu bar or floating widget.*
- **Reference**: A breathing, dynamic status indicator reflecting Miori's current state (idle, listening, thinking, speaking, acting).
- **Key Elements**: Siri-like or Cortana-like abstract glowing orb, changing colors and pulse frequency based on the WebSocket heartbeat and active tool execution (e.g., pulsing red when `requires_approval` pauses the loop).

### 4. Computer-use & Remote Vision
*For the P2 remote frame streaming.*
- **Reference**: Tactical feeds, HUD overlays.
- **Key Elements**: High-contrast bounding boxes, stream quality indicators, and clear security/arming state toggles (Arm/Disarm).

---
*Note: These references guide the implementations in `apps/desktop` and `apps/remote-dashboard` during Phases 7 and 8.*

┌────────────────────┐
│  INPUT / CONTROL   │
│ (encoders, keys)   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Controllers       │
│                    │
│  StaticModeCtrl    │───┐
│  AnimationModeCtrl │   │
│  SelectedIndicator │   │
└─────────┬──────────┘   │
          │              │
          ▼              │
┌────────────────────┐   │
│  Frame Producers   │◄──┘
│                    │
│  AnimationEngine   │  (continuous)
│  Indicator Loop    │  (overlay)
│  Static Renderer   │  (sporadic)
└─────────┬──────────┘
          │ push_frame()
          ▼
┌──────────────────────────────────┐
│          FrameManager            │
│                                  │
│  Queues per priority             │
│  ANIMATION  (continuous source)  │
│  PULSE      (overlay)            │
│  MANUAL     (static)             │
│                                  │
│  ┌────────────────────────────┐  │
│  │ merge on each render tick  │  │
│  │                            │  │
│  │ ANIMATION (base layer)     │  │
│  │ + overlays (PULSE etc.)    │  │
│  └────────────────────────────┘  │
└─────────┬────────────────────────┘
          │
          ▼
┌────────────────────┐
│  LED Strip Output  │
└────────────────────┘

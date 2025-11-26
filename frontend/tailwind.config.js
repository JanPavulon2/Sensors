/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Background layers (dark theme)
        bg: {
          app: '#0A0A0A',
          panel: '#141414',
          elevated: '#1E1E1E',
          input: '#0F0F0F',
        },
        // Text colors
        text: {
          primary: '#FFFFFF',
          secondary: '#A1A1A1',
          tertiary: '#6B6B6B',
          disabled: '#404040',
        },
        // Accent (LED glow theme - cyan)
        accent: {
          primary: '#00E5FF',
          hover: '#00D4F0',
          active: '#00B8D4',
          glow: 'rgba(0, 229, 255, 0.3)',
        },
        // Status colors
        success: '#00E676',
        warning: '#FFD600',
        error: '#FF1744',
        info: '#2979FF',
        // Borders
        border: {
          subtle: '#1E1E1E',
          default: '#2A2A2A',
          strong: '#404040',
        },
        // Zone colors (customizable)
        zone: {
          floor: '#00E5FF',
          lamp: '#FF6B6B',
          desk: '#9D4EDD',
          hood: '#06FFA5',
        },
      },
      fontSize: {
        xs: '0.75rem',   // 12px
        sm: '0.875rem',  // 14px
        base: '1rem',    // 16px
        lg: '1.125rem',  // 18px
        xl: '1.25rem',   // 20px
        '2xl': '1.5rem', // 24px
        '3xl': '1.875rem', // 30px
        '4xl': '2.25rem',  // 36px
        '5xl': '3rem',     // 48px
      },
      spacing: {
        '0': '0',
        '1': '0.25rem',  // 4px
        '2': '0.5rem',   // 8px
        '3': '0.75rem',  // 12px
        '4': '1rem',     // 16px
        '6': '1.5rem',   // 24px
        '8': '2rem',     // 32px
        '12': '3rem',    // 48px
        '16': '4rem',    // 64px
        '24': '6rem',    // 96px
      },
      borderRadius: {
        'none': '0',
        'sm': '0.25rem',   // 4px
        'md': '0.5rem',    // 8px
        'lg': '0.75rem',   // 12px
        'xl': '1rem',      // 16px
        'full': '9999px',
      },
      boxShadow: {
        'sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'DEFAULT': '0 4px 6px rgba(0, 0, 0, 0.1)',
        'md': '0 6px 12px rgba(0, 0, 0, 0.15)',
        'lg': '0 10px 25px rgba(0, 0, 0, 0.2)',
        'glow': '0 0 20px rgba(0, 229, 255, 0.5)',
        'glow-sm': '0 0 10px rgba(0, 229, 255, 0.3)',
      },
      animation: {
        'led-pulse': 'led-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        'led-pulse': {
          '0%, 100%': {
            boxShadow: '0 0 10px rgba(0, 229, 255, 0.3), 0 0 20px rgba(0, 229, 255, 0.2)',
          },
          '50%': {
            boxShadow: '0 0 20px rgba(0, 229, 255, 0.5), 0 0 40px rgba(0, 229, 255, 0.3), 0 0 60px rgba(0, 229, 255, 0.2)',
          },
        },
      },
      fontFamily: {
        // You can customize these if desired
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};

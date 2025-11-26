/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
  	extend: {
  		colors: {
  			bg: {
  				app: '#0d1117',
  				panel: '#161b22',
  				elevated: '#21262d',
  				input: '#0d1117'
  			},
  			text: {
  				primary: '#e6edf3',
  				secondary: '#8b949e',
  				tertiary: '#6e7681',
  				disabled: '#444c56'
  			},
  			accent: {
  				primary: '#39ff14',
  				hover: '#2aff00',
  				active: '#1eff00',
  				glow: 'rgba(57, 255, 20, 0.3)',
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			success: '#3fb950',
  			warning: '#d29922',
  			error: '#da3633',
  			info: '#58a6ff',
  			border: 'hsl(var(--border))',
  			zone: {
  				floor: '#00E5FF',
  				lamp: '#FF6B6B',
  				desk: '#9D4EDD',
  				hood: '#06FFA5'
  			},
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		fontSize: {
  			xs: '0.75rem',
  			sm: '0.875rem',
  			base: '1rem',
  			lg: '1.125rem',
  			xl: '1.25rem',
  			'2xl': '1.5rem',
  			'3xl': '1.875rem',
  			'4xl': '2.25rem',
  			'5xl': '3rem'
  		},
  		spacing: {
  			'0': '0',
  			'1': '0.25rem',
  			'2': '0.5rem',
  			'3': '0.75rem',
  			'4': '1rem',
  			'6': '1.5rem',
  			'8': '2rem',
  			'12': '3rem',
  			'16': '4rem',
  			'24': '6rem'
  		},
  		borderRadius: {
  			none: '0',
  			sm: '1px',
  			md: '2px',
  			lg: '2px',
  			xl: '2px',
  			full: '9999px'
  		},
  		boxShadow: {
  			sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
  			DEFAULT: '0 2px 4px rgba(0, 0, 0, 0.4)',
  			md: '0 4px 8px rgba(0, 0, 0, 0.5)',
  			lg: '0 8px 16px rgba(0, 0, 0, 0.6)',
  			glow: '0 0 20px rgba(57, 255, 20, 0.4)',
  			'glow-sm': '0 0 10px rgba(57, 255, 20, 0.2)'
  		},
  		animation: {
  			'led-pulse': 'led-pulse 2s ease-in-out infinite'
  		},
  		keyframes: {
  			'led-pulse': {
  				'0%, 100%': {
  					boxShadow: '0 0 10px rgba(57, 255, 20, 0.3), 0 0 20px rgba(57, 255, 20, 0.2)'
  				},
  				'50%': {
  					boxShadow: '0 0 20px rgba(57, 255, 20, 0.5), 0 0 40px rgba(57, 255, 20, 0.3), 0 0 60px rgba(57, 255, 20, 0.2)'
  				}
  			}
  		},
  		fontFamily: {
  			sans: [
  				'Inter',
  				'system-ui',
  				'sans-serif'
  			],
  			mono: [
  				'JetBrains Mono',
  				'Fira Code',
  				'monospace'
  			]
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};

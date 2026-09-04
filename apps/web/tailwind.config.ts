import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#09090b',
        foreground: '#f4f4f5',
        card: {
          DEFAULT: '#121215',
          foreground: '#f4f4f5',
          border: '#27272a',
        },
        popover: {
          DEFAULT: '#18181b',
          foreground: '#f4f4f5',
        },
        primary: {
          DEFAULT: '#6366f1',
          foreground: '#ffffff',
          hover: '#4f46e5',
          subtle: 'rgba(99, 102, 241, 0.1)',
        },
        secondary: {
          DEFAULT: '#27272a',
          foreground: '#f4f4f5',
          hover: '#3f3f46',
        },
        muted: {
          DEFAULT: '#18181b',
          foreground: '#a1a1aa',
        },
        accent: {
          DEFAULT: '#06b6d4',
          foreground: '#ffffff',
        },
        destructive: {
          DEFAULT: '#ef4444',
          foreground: '#ffffff',
        },
        success: {
          DEFAULT: '#10b981',
          foreground: '#ffffff',
        },
        border: '#27272a',
        input: '#27272a',
        ring: '#6366f1',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-subtle': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};

export default config;

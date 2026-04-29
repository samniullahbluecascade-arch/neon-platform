import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'neon-pink':  '#ff2d78',
        'neon-cyan':  '#00d4ff',
        'neon-green': '#00ff9d',
        'neon-amber': '#ffb300',
        'neon-red':   '#ff3b3b',
        'bg-0': '#07070e',
        'bg-1': '#0e0e1b',
        'bg-2': '#161628',
      },
      fontFamily: {
        display: ['var(--font-bebas)', 'sans-serif'],
        mono:    ['var(--font-space-mono)', 'monospace'],
        sans:    ['var(--font-dm-sans)', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'flicker':    'flicker 3s linear infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.6' },
        },
        flicker: {
          '0%, 95%, 100%': { opacity: '1' },
          '96%':           { opacity: '0.4' },
          '97%':           { opacity: '1' },
          '98%':           { opacity: '0.2' },
          '99%':           { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};

export default config;

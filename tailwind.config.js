/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './frontend/src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#172119',
        signal: '#B8F34A',
        canvas: '#F5F6F1',
        muted: '#748077',
        line: '#E6E9E3',
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'], mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'] },
    },
  },
  plugins: [],
};

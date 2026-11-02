/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        ink: '#18201d',
        moss: '#315c4a',
        mint: '#dceee5',
        paper: '#f7f8f5',
        line: '#e5e9e3',
      },
      boxShadow: {
        soft: '0 16px 50px rgba(24, 32, 29, 0.08)',
        card: '0 8px 30px rgba(24, 32, 29, 0.06)',
      },
    },
  },
  plugins: [],
}

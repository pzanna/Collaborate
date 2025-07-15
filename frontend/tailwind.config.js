/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'slack-blue': '#1264a3',
        'slack-green': '#2eb67d',
        'slack-yellow': '#ecb22e',
        'slack-red': '#e01e5a',
      },
      animation: {
        'bounce-slow': 'bounce 1.4s infinite',
      },
    },
  },
  plugins: [],
}

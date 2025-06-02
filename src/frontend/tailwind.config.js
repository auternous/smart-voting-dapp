/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "typewriter-bg": "#fdf9e4",
        "typewriter-text": "#003300",
        "typewriter-border": "#a89f78",
      },
      fontFamily: {
        mono: ["'Courier Prime'", "Courier", "monospace"],
      },
    },
  },
  plugins: [],
};
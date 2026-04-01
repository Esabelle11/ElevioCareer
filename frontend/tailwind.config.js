/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        elevio: {
          blue: "#2F7CF6",
          purple: "#6B4EE6",
          pink: "#E94FA8",
          dark: "#0a0a0f",
          surface: "#12121a",
          border: "#262636",
          muted: "#8b8b9a",
        },
      },
      backgroundImage: {
        "gradient-brand": "linear-gradient(135deg, #6B4EE6 0%, #2F7CF6 50%, #E94FA8 100%)",
      },
    },
  },
  plugins: [],
};

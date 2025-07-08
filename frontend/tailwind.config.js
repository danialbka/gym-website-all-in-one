/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./*.html", "./src/**/*.{html,js}"],
  theme: {
    extend: {
      colors: {
        border: "#e5e5e5",
        input: "#f5f5f5",
        ring: "#000000",
        background: "#ffffff",
        foreground: "#000000",
        primary: {
          DEFAULT: "#000000",
          foreground: "#ffffff",
        },
        secondary: {
          DEFAULT: "#f5f5f5",
          foreground: "#000000",
        },
        destructive: {
          DEFAULT: "#000000",
          foreground: "#ffffff",
        },
        muted: {
          DEFAULT: "#f9f9f9",
          foreground: "#666666",
        },
        accent: {
          DEFAULT: "#f0f0f0",
          foreground: "#000000",
        },
        card: {
          DEFAULT: "#ffffff",
          foreground: "#000000",
        },
      },
    }
  },
  plugins: [],
}
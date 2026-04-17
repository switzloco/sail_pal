import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontSize: {
        base: ["16px", "1.5"],
        sm: ["14px", "1.4"],
      },
      colors: {
        ocean: {
          900: "#0c1b33",
          800: "#1a3050",
          700: "#1e4d8c",
          600: "#2563eb",
          500: "#3b82f6",
          100: "#dbeafe",
        },
        alert: {
          red: "#dc2626",
          amber: "#d97706",
          yellow: "#ca8a04",
          green: "#16a34a",
        },
      },
    },
  },
  plugins: [],
};

export default config;

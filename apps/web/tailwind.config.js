/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Nexus design tokens — dark-first, restrained accent
        surface: {
          DEFAULT: "#0f1117",
          raised: "#181c27",
          overlay: "#1e2333",
        },
        border: {
          DEFAULT: "#2a2f45",
          subtle: "#1e2333",
        },
        accent: {
          DEFAULT: "#6366f1",  // indigo-500
          hover: "#818cf8",    // indigo-400
          muted: "#312e81",    // indigo-900
        },
        text: {
          primary: "#f1f5f9",
          secondary: "#94a3b8",
          muted: "#475569",
        },
        status: {
          success: "#22c55e",
          error: "#ef4444",
          warning: "#f59e0b",
          running: "#3b82f6",
          idle: "#475569",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};

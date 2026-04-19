/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        background: "#f8fafc",
        card: "#ffffff",
        textPrimary: "#0f172a",
        textSecondary: "#64748b",
        accent: "#2563eb",
        accentLight: "#dbeafe",
        danger: "#dc2626",
        success: "#16a34a",
        warn: "#d97706",
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)',
        'card-hover': '0 4px 12px 0 rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06)',
        'nav': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      },
      borderRadius: {
        'card': '12px',
      },
    },
  },
  plugins: [],
}

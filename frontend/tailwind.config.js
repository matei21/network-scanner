/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // WCAG AA contrast on white background
        risk: {
          high: "#b91c1c",    // red-700
          medium: "#b45309",  // amber-700
          low: "#1d4ed8",     // blue-700
          info: "#374151",    // gray-700
          safe: "#15803d",    // green-700
        },
      },
      fontSize: {
        // Enforce minimum 16px (NFR-08)
        base: ["1rem", { lineHeight: "1.5rem" }],
      },
    },
  },
  plugins: [],
};

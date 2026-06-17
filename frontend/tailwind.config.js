/** @type {import('tailwindcss').Config} */
export default {
  // Tell Tailwind where to look for class names so unused ones are purged in production
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

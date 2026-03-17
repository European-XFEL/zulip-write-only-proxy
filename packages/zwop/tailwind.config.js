/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/zwop/frontend/templates/**.html",
    "./src/zwop/frontend/templates/*/**.html"
  ],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
  safelist: [
    'alert-error',
    'alert-info',
    'alert-warning',
  ]
};

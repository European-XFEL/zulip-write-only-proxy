/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./packages/zwop-service/src/zwop/frontend/templates/**.html",
    "./packages/zwop-service/src/zwop/frontend/templates/*/**.html"
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

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/zulip_write_only_proxy/frontend/templates/**.html",
    "./src/zulip_write_only_proxy/frontend/templates/*/**.html"
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

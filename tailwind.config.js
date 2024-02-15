/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/zulip_write_only_proxy/templates/**.html",
    "./src/zulip_write_only_proxy/templates/*/**.html"
  ],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
};

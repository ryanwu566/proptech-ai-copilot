const e2eConnectSource = process.env.NEXT_PUBLIC_API_BASE_URL === "http://e2e.test" ? " http://e2e.test" : "";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), payment=(), usb=(), serial=(), microphone=(self)" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'${e2eConnectSource}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'` },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-site" },
];

const nextConfig = {
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;

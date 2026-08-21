export function getApiConnectSource() {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!raw) {
    return "";
  }

  try {
    const url = new URL(raw);
    if (url.origin === "http://e2e.test") {
      return " http://e2e.test";
    }
    // Allow localhost/127.0.0.1 HTTP origins for local development
    const hostname = url.hostname.toLowerCase();
    if ((hostname === "localhost" || hostname === "127.0.0.1") && url.protocol === "http:") {
      return ` ${url.origin}`;
    }
    if (url.protocol !== "https:") {
      return "";
    }
    return ` ${url.origin}`;
  } catch {
    return "";
  }
}

const apiConnectSource = getApiConnectSource();

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), payment=(), usb=(), serial=(), microphone=(self)" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com https://server.arcgisonline.com https://wmts.nlsc.gov.tw; connect-src 'self'${apiConnectSource}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'` },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-site" },
];

const nextConfig = {
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;

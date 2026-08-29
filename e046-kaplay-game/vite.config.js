import { defineConfig } from "vite";

export default defineConfig({
    // The game uses top-level await (loading sprites), so the build target
    // must support it. esnext keeps the bundle modern.
    build: {
        target: "esnext",
    },
    server: {
        host: true,
        port: 5173,
        // Allow the user's Tailscale hostname (and the whole ts.net domain)
        // to reach the dev server over the LAN / tailnet.
        allowedHosts: [
            "vuos-hcar5000mi.tail6918b0.ts.net",
            ".tail6918b0.ts.net",
        ],
    },
});

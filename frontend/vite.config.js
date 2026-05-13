import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
export default defineConfig(function (_a) {
    var command = _a.command;
    return ({
        plugins: [react()],
        base: command === "build" ? "/ocw-canvas/" : "/",
        server: { port: 5173 },
    });
});

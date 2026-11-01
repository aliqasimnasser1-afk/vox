import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' lets the build work under any GitHub Pages sub-path
export default defineConfig({ base: './', plugins: [react()] });

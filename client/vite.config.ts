import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
    const rootEnv = loadEnv(mode, '..', 'VITE_');

    return {
        plugins: [sveltekit({
            preprocess: vitePreprocess(),
            files: { assets: 'public' },
            adapter: adapter({ pages: 'dist', assets: 'dist', fallback: 'index.html', strict: false }),
            version: { pollInterval: 60_000 },
        })],
        envDir: '..',
        define: {
            'import.meta.env.VITE_SUPABASE_URL': JSON.stringify(rootEnv.VITE_SUPABASE_URL),
            'import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY': JSON.stringify(rootEnv.VITE_SUPABASE_PUBLISHABLE_KEY),
            'import.meta.env.VITE_API_URL': JSON.stringify(rootEnv.VITE_API_URL),
            'import.meta.env.VITE_GA_ID': JSON.stringify(rootEnv.VITE_GA_ID),
        },
    };
});

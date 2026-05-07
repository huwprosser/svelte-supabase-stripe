<script lang="ts">
    import { updated } from '$app/state';

    let { children } = $props();

    $effect(() => {
        if (updated.current && confirm('A new version is available. Reload?')) {
            location.reload();
        }
    });
</script>

{@render children()}

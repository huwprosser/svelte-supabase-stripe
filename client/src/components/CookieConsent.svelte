<script lang="ts">
    type CookieChoice = "yes" | "no";

    let { onChoice }: { onChoice: (choice: CookieChoice) => void } = $props();

    function choose(choice: CookieChoice) {
        localStorage.setItem("cookieChoice", choice);
        onChoice(choice);
    }
</script>

<div class="cookie">
    <span>We use optional Google Analytics cookies.</span>
    <button onclick={() => choose("no")}>Reject</button>
    <button onclick={() => choose("yes")}>Accept</button>
</div>

<style>
    .cookie {
        position: fixed;
        left: 16px;
        right: 16px;
        bottom: 16px;
        background: white;
        border: 1px solid #ccc;
        padding: 12px;
        display: flex;
        gap: 8px;
        justify-content: center;
        align-items: center;
    }

    button {
        padding: 10px 12px;
        cursor: pointer;
    }
</style>

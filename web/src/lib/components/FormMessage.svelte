<script lang="ts">
  let { message, tone = 'error' }: { message: string; tone?: 'error' | 'success' | 'info' } = $props();
</script>

{#if message}
  <div
    class:bg-red-50={tone === 'error'}
    class:text-red-800={tone === 'error'}
    class:border-red-200={tone === 'error'}
    class:bg-emerald-50={tone === 'success'}
    class:text-emerald-800={tone === 'success'}
    class:border-emerald-200={tone === 'success'}
    class:bg-amber-50={tone === 'info'}
    class:text-amber-900={tone === 'info'}
    class:border-amber-200={tone === 'info'}
    class="rounded-2xl border px-4 py-3 text-sm leading-6"
    role={tone === 'error' ? 'alert' : 'status'}
  >
    {message}
  </div>
{/if}

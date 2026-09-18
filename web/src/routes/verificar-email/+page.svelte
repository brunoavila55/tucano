<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import FormMessage from '$lib/components/FormMessage.svelte';
  import { errorMessage, verifyEmail } from '$lib/api';

  let loading = true;
  let message = '';
  let error = '';

  onMount(async () => {
    const token = new URL(window.location.href).searchParams.get('token') ?? '';
    if (!token) {
      error = 'O link de confirmação está incompleto.';
      loading = false;
      return;
    }
    try {
      const response = await verifyEmail(token);
      message = response.message;
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head><title>Confirmar e-mail — Tucano</title></svelte:head>

<AuthShell eyebrow="Segurança da conta" title="Confirme seu e-mail">
  <div class="space-y-5">
    {#if loading}<p class="text-ink/60" role="status">Validando seu link…</p>{/if}
    <FormMessage message={message} tone="success" />
    <FormMessage message={error} />
    {#if !loading}
      <a class="primary-button flex w-full items-center justify-center" href={resolve('/entrar')}>Ir para o login</a>
    {/if}
  </div>
</AuthShell>

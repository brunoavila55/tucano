<script lang="ts">
  import { resolve } from '$app/paths';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import FormMessage from '$lib/components/FormMessage.svelte';
  import { errorMessage, requestPasswordReset } from '$lib/api';

  let email = '';
  let loading = false;
  let message = '';
  let error = '';
  let developmentToken = '';

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    loading = true;
    error = '';
    try {
      const response = await requestPasswordReset(email);
      message = response.message;
      developmentToken = response.development_action_token ?? '';
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Recuperar senha — Tucano</title></svelte:head>

<AuthShell eyebrow="Recuperação de acesso" title="Redefina sua senha">
  <div class="mb-5 space-y-5">
    <FormMessage message={error} />
    <FormMessage message={message} tone="success" />
    {#if developmentToken}
      <form action={resolve('/redefinir-senha')} method="GET">
        <input type="hidden" name="token" value={developmentToken} />
        <button class="primary-button flex w-full items-center justify-center" type="submit">Continuar no ambiente local</button>
      </form>
    {/if}
  </div>
  <form class="space-y-5" onsubmit={submit}>
    <label class="block">
      <span class="mb-2 block text-sm font-bold">E-mail da conta</span>
      <input class="form-input" bind:value={email} type="email" autocomplete="email" required />
    </label>
    <button class="primary-button w-full" disabled={loading}>{loading ? 'Enviando…' : 'Enviar instruções'}</button>
    <a class="block text-center text-sm font-bold text-forest hover:underline" href={resolve('/entrar')}>Voltar ao login</a>
  </form>
</AuthShell>

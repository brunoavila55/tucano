<script lang="ts">
  import { resolve } from '$app/paths';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import FormMessage from '$lib/components/FormMessage.svelte';
  import { errorMessage, resetPassword } from '$lib/api';

  let password = '';
  let passwordConfirmation = '';
  let loading = false;
  let message = '';
  let error = '';

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    error = '';
    if (password !== passwordConfirmation) {
      error = 'As senhas não coincidem.';
      return;
    }
    const token = new URL(window.location.href).searchParams.get('token') ?? '';
    if (!token) {
      error = 'O link de redefinição está incompleto.';
      return;
    }
    loading = true;
    try {
      const response = await resetPassword(token, password);
      message = response.message;
      password = '';
      passwordConfirmation = '';
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Nova senha — Tucano</title></svelte:head>

<AuthShell eyebrow="Recuperação de acesso" title="Escolha uma nova senha">
  <form class="space-y-5" onsubmit={submit}>
    <FormMessage message={error} />
    <FormMessage message={message} tone="success" />
    <label class="block">
      <span class="mb-2 block text-sm font-bold">Nova senha</span>
      <input class="form-input" bind:value={password} type="password" autocomplete="new-password" minlength="12" maxlength="128" required />
    </label>
    <label class="block">
      <span class="mb-2 block text-sm font-bold">Repita a nova senha</span>
      <input class="form-input" bind:value={passwordConfirmation} type="password" autocomplete="new-password" minlength="12" maxlength="128" required />
    </label>
    <button class="primary-button w-full" disabled={loading || !!message}>{loading ? 'Salvando…' : 'Salvar nova senha'}</button>
    {#if message}<a class="block text-center text-sm font-bold text-forest hover:underline" href={resolve('/entrar')}>Entrar com a nova senha</a>{/if}
  </form>
</AuthShell>

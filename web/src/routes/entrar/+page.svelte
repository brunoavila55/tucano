<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import FormMessage from '$lib/components/FormMessage.svelte';
  import { errorMessage, login } from '$lib/api';

  let email = '';
  let password = '';
  let loading = false;
  let error = '';

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    loading = true;
    error = '';
    try {
      await login(email, password);
      await goto(resolve('/conta'));
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Entrar — Tucano</title></svelte:head>

<AuthShell eyebrow="Bom ter você de volta" title="Entre na sua conta">
  <form class="space-y-5" onsubmit={submit}>
    <FormMessage message={error} />
    <label class="block">
      <span class="mb-2 block text-sm font-bold">E-mail</span>
      <input class="form-input" bind:value={email} type="email" autocomplete="email" required />
    </label>
    <label class="block">
      <span class="mb-2 block text-sm font-bold">Senha</span>
      <input class="form-input" bind:value={password} type="password" autocomplete="current-password" required />
    </label>
    <div class="flex justify-end">
      <a class="text-sm font-bold text-forest hover:underline" href={resolve('/recuperar-senha')}>Esqueci minha senha</a>
    </div>
    <button class="primary-button w-full" disabled={loading}>{loading ? 'Entrando…' : 'Entrar'}</button>
    <p class="text-center text-sm text-ink/55">Ainda não tem conta? <a class="font-bold text-forest hover:underline" href={resolve('/cadastro')}>Cadastre-se</a></p>
  </form>
</AuthShell>

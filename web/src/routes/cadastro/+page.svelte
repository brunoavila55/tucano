<script lang="ts">
  import { resolve } from '$app/paths';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import FormMessage from '$lib/components/FormMessage.svelte';
  import { errorMessage, register, type Role } from '$lib/api';

  let displayName = '';
  let email = '';
  let password = '';
  let profileType: Role = 'client';
  let companyName = '';
  let loading = false;
  let error = '';
  let success = '';
  let developmentToken = '';

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    loading = true;
    error = '';
    try {
      const response = await register({
        display_name: displayName,
        email,
        password,
        profile_type: profileType,
        company_name: companyName
      });
      success = response.message;
      developmentToken = response.development_action_token ?? '';
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Criar conta — Tucano</title></svelte:head>

<AuthShell eyebrow="Comece por aqui" title="Crie sua conta">
  {#if success}
    <div class="space-y-5">
      <FormMessage message={success} tone="success" />
      {#if developmentToken}
        <FormMessage message="Ambiente local: use o botão abaixo para confirmar sem um servidor de e-mail." tone="info" />
        <form action={resolve('/verificar-email')} method="GET">
          <input type="hidden" name="token" value={developmentToken} />
          <button class="flex min-h-12 w-full items-center justify-center rounded-2xl bg-forest px-5 font-extrabold text-white">Confirmar e-mail</button>
        </form>
      {/if}
      <a class="block text-center text-sm font-bold text-forest underline-offset-4 hover:underline" href={resolve('/entrar')}>Ir para o login</a>
    </div>
  {:else}
    <form class="space-y-5" onsubmit={submit}>
      <FormMessage message={error} />

      <label class="block">
        <span class="mb-2 block text-sm font-bold">Seu nome</span>
        <input class="form-input" bind:value={displayName} autocomplete="name" minlength="2" maxlength="100" required />
      </label>

      <label class="block">
        <span class="mb-2 block text-sm font-bold">E-mail</span>
        <input class="form-input" bind:value={email} type="email" autocomplete="email" maxlength="254" required />
      </label>

      <label class="block">
        <span class="mb-2 block text-sm font-bold">Senha</span>
        <input class="form-input" bind:value={password} type="password" autocomplete="new-password" minlength="12" maxlength="128" required aria-describedby="password-help" />
        <span id="password-help" class="mt-2 block text-xs text-ink/50">Use pelo menos 12 caracteres.</span>
      </label>

      <fieldset>
        <legend class="mb-3 text-sm font-bold">Como você quer começar?</legend>
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="profile-choice" class:profile-choice-selected={profileType === 'client'}>
            <input class="sr-only" type="radio" bind:group={profileType} value="client" />
            <strong>Preciso de serviços</strong>
            <span>Perfil contratante</span>
          </label>
          <label class="profile-choice" class:profile-choice-selected={profileType === 'professional'}>
            <input class="sr-only" type="radio" bind:group={profileType} value="professional" />
            <strong>Ofereço serviços</strong>
            <span>Perfil profissional</span>
          </label>
        </div>
      </fieldset>

      {#if profileType === 'client'}
        <label class="block">
          <span class="mb-2 block text-sm font-bold">Empresa <span class="font-normal text-ink/45">(opcional)</span></span>
          <input class="form-input" bind:value={companyName} autocomplete="organization" maxlength="150" />
        </label>
      {/if}

      <button class="primary-button w-full" disabled={loading}>{loading ? 'Criando conta…' : 'Criar conta'}</button>
      <p class="text-center text-sm text-ink/55">Já tem conta? <a class="font-bold text-forest hover:underline" href={resolve('/entrar')}>Entrar</a></p>
    </form>
  {/if}
</AuthShell>

<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import FormMessage from '$lib/components/FormMessage.svelte';
  import { addProfile, errorMessage, getMe, logout, type Role, type User } from '$lib/api';

  let user: User | null = null;
  let activeRole: Role = 'client';
  let loading = true;
  let adding = false;
  let error = '';
  let companyName = '';

  onMount(async () => {
    try {
      user = await getMe();
      activeRole = preferredRole(user.roles);
    } catch {
      await goto(resolve('/entrar'));
    } finally {
      loading = false;
    }
  });

  function preferredRole(roles: Role[]): Role {
    const saved = window.localStorage.getItem('tucano_active_role') as Role | null;
    if (saved && roles.includes(saved)) return saved;
    return roles[0] ?? 'client';
  }

  function selectRole(role: Role) {
    activeRole = role;
    window.localStorage.setItem('tucano_active_role', role);
  }

  async function createMissingProfile(role: Role) {
    adding = true;
    error = '';
    try {
      user = await addProfile(role, companyName);
      selectRole(role);
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      adding = false;
    }
  }

  async function signOut() {
    await logout();
    await goto(resolve('/entrar'));
  }
</script>

<svelte:head><title>Minha conta — Tucano</title></svelte:head>

<main class="min-h-screen px-5 py-6 sm:px-8">
  <nav class="mx-auto flex max-w-6xl items-center justify-between" aria-label="Navegação da conta">
    <a class="flex items-center gap-3 rounded-lg" href={resolve('/')}>
      <span class="grid size-10 place-items-center rounded-2xl bg-forest font-black text-white" aria-hidden="true">T</span>
      <span class="font-display text-2xl font-bold">tucano</span>
    </a>
    <button class="rounded-xl px-3 py-2 text-sm font-bold text-forest hover:bg-forest/5" onclick={signOut}>Sair</button>
  </nav>

  <section class="mx-auto max-w-6xl py-12">
    {#if loading}
      <p class="text-ink/60" role="status">Carregando sua conta…</p>
    {:else if user}
      <header class="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p class="text-xs font-black tracking-[0.16em] text-coral uppercase">Sua conta</p>
          <h1 class="mt-2 font-display text-4xl font-bold tracking-tight">Olá, {user.display_name}</h1>
          <p class="mt-2 text-sm text-ink/55">{user.email}</p>
        </div>
        {#if user.roles.length > 1}
          <div class="inline-flex rounded-2xl border border-forest/10 bg-white p-1" aria-label="Perfil ativo">
            <button class="role-tab" class:role-tab-active={activeRole === 'client'} onclick={() => selectRole('client')}>Contratante</button>
            <button class="role-tab" class:role-tab-active={activeRole === 'professional'} onclick={() => selectRole('professional')}>Profissional</button>
          </div>
        {/if}
      </header>

      <div class="mt-10 grid gap-6 lg:grid-cols-[1.4fr_0.6fr]">
        <article class="rounded-[2rem] border border-white bg-white/85 p-6 shadow-[0_18px_60px_rgb(24_35_30/0.09)] sm:p-8">
          <p class="text-xs font-black tracking-widest text-coral uppercase">Perfil ativo</p>
          <h2 class="mt-3 font-display text-3xl font-bold">{activeRole === 'client' ? 'Contratante' : 'Profissional'}</h2>
          <p class="mt-3 max-w-xl leading-7 text-ink/60">
            {activeRole === 'client'
              ? 'Publique chamados e encontre profissionais compatíveis. O fluxo de chamados entra na próxima etapa do produto.'
              : 'Configure seus serviços, região e disponibilidade. Esses dados entram na próxima etapa do produto.'}
          </p>
          <div class="mt-7 rounded-2xl bg-cream p-5 text-sm leading-6 text-ink/65">
            Seu perfil está criado e protegido por autorização no servidor. Nenhuma condição de serviço ou pagamento é intermediada pela plataforma.
          </div>
          {#if activeRole === 'professional'}
            <a class="primary-button mt-6 inline-flex items-center justify-center" href={resolve('/perfil-profissional')}>Configurar perfil profissional</a>
          {:else}
            <a class="primary-button mt-6 inline-flex items-center justify-center" href={resolve('/buscar-profissionais')}>Buscar profissionais</a>
          {/if}
        </article>

        <aside class="space-y-5">
          <FormMessage message={error} />
          {#if !user.roles.includes('professional')}
            <div class="rounded-3xl border border-forest/10 bg-white/70 p-5">
              <h2 class="font-display text-xl font-bold">Também oferece serviços?</h2>
              <p class="mt-2 text-sm leading-6 text-ink/55">Adicione o perfil profissional à mesma conta.</p>
              <button class="secondary-button mt-5 w-full" disabled={adding} onclick={() => createMissingProfile('professional')}>Adicionar perfil profissional</button>
            </div>
          {/if}
          {#if !user.roles.includes('client')}
            <div class="rounded-3xl border border-forest/10 bg-white/70 p-5">
              <h2 class="font-display text-xl font-bold">Também precisa contratar?</h2>
              <p class="mt-2 text-sm leading-6 text-ink/55">Adicione o perfil contratante sem criar outra conta.</p>
              <label class="mt-4 block text-sm font-bold">
                Empresa <span class="font-normal text-ink/45">(opcional)</span>
                <input class="form-input mt-2" bind:value={companyName} maxlength="150" />
              </label>
              <button class="secondary-button mt-5 w-full" disabled={adding} onclick={() => createMissingProfile('client')}>Adicionar perfil contratante</button>
            </div>
          {/if}
        </aside>
      </div>
    {/if}
  </section>
</main>

<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { readHealth, type HealthStatus } from '$lib/health';

  let health: HealthStatus = 'loading';

  onMount(async () => {
    health = await readHealth();
  });

  const statusLabel: Record<HealthStatus, string> = {
    loading: 'Conectando…',
    online: 'Sistema online',
    offline: 'API indisponível'
  };
</script>

<svelte:head>
  <meta property="og:title" content="Tucano — encontre o profissional certo" />
  <meta
    property="og:description"
    content="Necessidade publicada. Profissionais compatíveis. Contato direto."
  />
</svelte:head>

<main class="min-h-screen overflow-hidden">
  <nav class="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12" aria-label="Navegação principal">
    <a class="flex items-center gap-3 rounded-lg" href={resolve('/')} aria-label="Tucano, página inicial">
      <span class="grid size-10 place-items-center rounded-2xl bg-forest text-lg font-black text-white shadow-[0_6px_18px_rgb(22_86_63/0.2)]" aria-hidden="true">T</span>
      <span class="font-display text-2xl font-bold tracking-tight text-ink">tucano</span>
    </a>

    <div class="flex items-center gap-2 rounded-full border border-forest/10 bg-white/70 px-3 py-2 text-xs font-bold text-forest shadow-sm backdrop-blur" role="status" aria-live="polite">
      <span class:animate-pulse={health === 'loading'} class:bg-amber-400={health === 'loading'} class:bg-emerald-500={health === 'online'} class:bg-red-400={health === 'offline'} class="size-2 rounded-full"></span>
      {statusLabel[health]}
    </div>
  </nav>

  <section class="mx-auto grid max-w-7xl items-center gap-14 px-5 pb-20 pt-12 sm:px-8 sm:pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:px-12 lg:pb-28 lg:pt-24">
    <div class="relative z-10 max-w-2xl">
      <div class="mb-7 inline-flex items-center gap-2 rounded-full border border-coral/20 bg-coral/10 px-4 py-2 text-sm font-bold text-[#a83b27]">
        <span aria-hidden="true">●</span>
        Marketplace de serviços autônomos
      </div>

      <h1 class="font-display text-[clamp(3.25rem,9vw,6.8rem)] leading-[0.91] font-bold tracking-[-0.055em] text-ink">
        O serviço certo,
        <span class="relative mt-2 block w-fit text-forest">
          na hora certa.
          <svg class="absolute -bottom-3 left-0 -z-10 h-4 w-full text-coral/45" viewBox="0 0 530 24" preserveAspectRatio="none" aria-hidden="true">
            <path d="M4 18C119 3 306 3 526 14" fill="none" stroke="currentColor" stroke-width="10" stroke-linecap="round" />
          </svg>
        </span>
      </h1>

      <p class="mt-9 max-w-xl text-lg leading-8 text-ink/70 sm:text-xl">
        Publique o que você precisa e encontre profissionais compatíveis, disponíveis e próximos. Vocês conversam e combinam tudo diretamente.
      </p>

      <div class="mt-9 flex flex-col gap-3 sm:flex-row">
        <a class="flex min-h-14 items-center justify-center rounded-2xl bg-forest px-7 text-base font-extrabold text-white shadow-[0_12px_30px_rgb(22_86_63/0.22)] transition hover:-translate-y-0.5 hover:bg-[#104632]" href={resolve('/cadastro')}>
          Preciso de um profissional
        </a>
        <a class="flex min-h-14 items-center justify-center rounded-2xl border border-forest/20 bg-white/70 px-7 text-base font-extrabold text-forest transition hover:-translate-y-0.5 hover:bg-white" href={resolve('/cadastro')}>
          Quero oferecer serviços
        </a>
      </div>

      <p class="mt-4 text-sm text-ink/50">Uma conta, dois perfis quando você precisar.</p>
    </div>

    <div class="relative mx-auto w-full max-w-[34rem] lg:mx-0 lg:justify-self-end" aria-label="Prévia do fluxo de um chamado">
      <div class="absolute -left-12 top-16 size-32 rounded-full bg-coral/20 blur-3xl"></div>
      <div class="absolute -right-10 bottom-20 size-40 rounded-full bg-leaf/25 blur-3xl"></div>

      <article class="relative rotate-[1.5deg] rounded-[2rem] border border-white/80 bg-white/90 p-5 shadow-[0_30px_80px_rgb(24_35_30/0.15)] backdrop-blur sm:p-7">
        <div class="mb-6 flex items-start justify-between gap-4">
          <div>
            <p class="text-xs font-black tracking-[0.16em] text-coral uppercase">Janela de 2 horas</p>
            <h2 class="mt-2 font-display text-3xl font-bold tracking-tight">Garçom para evento</h2>
          </div>
          <span class="rounded-xl bg-emerald-50 px-3 py-2 text-xs font-extrabold text-emerald-700">Aberto</span>
        </div>

        <div class="grid gap-3 text-sm text-ink/70 sm:grid-cols-2">
          <div class="rounded-2xl bg-cream p-4">
            <span class="mb-1 block text-xs font-bold text-ink/40 uppercase">Quando</span>
            Sábado, 19h–23h
          </div>
          <div class="rounded-2xl bg-cream p-4">
            <span class="mb-1 block text-xs font-bold text-ink/40 uppercase">Região</span>
            Centro · 3,2 km
          </div>
        </div>

        <div class="mt-6 border-t border-sand pt-5">
          <div class="mb-4 flex items-center justify-between">
            <p class="font-extrabold">Profissionais compatíveis</p>
            <span class="text-sm font-bold text-forest">12 disponíveis</span>
          </div>
          <div class="space-y-3">
            {#each [
              { initials: 'AM', name: 'Ana Martins', meta: '4,9 · responde em 8 min', color: 'bg-[#f7c96d]' },
              { initials: 'RS', name: 'Rafael Souza', meta: '4,8 · 27 serviços', color: 'bg-[#93c9ad]' }
            ] as person (person.name)}
              <div class="flex items-center gap-3 rounded-2xl border border-sand/80 p-3">
                <div class={`grid size-11 shrink-0 place-items-center rounded-full ${person.color} text-sm font-black text-ink`}>{person.initials}</div>
                <div class="min-w-0 flex-1">
                  <p class="truncate font-extrabold">{person.name}</p>
                  <p class="truncate text-xs text-ink/55">{person.meta}</p>
                </div>
                <span class="rounded-lg bg-forest/8 px-2.5 py-1.5 text-xs font-extrabold text-forest">Compatível</span>
              </div>
            {/each}
          </div>
        </div>
      </article>

      <div class="absolute -bottom-8 -left-3 -rotate-3 rounded-2xl border border-white bg-ink px-5 py-4 text-white shadow-xl sm:-left-10">
        <p class="text-xs font-bold text-white/60">Contato direto</p>
        <p class="mt-1 font-display text-lg font-bold">Sem comissão por serviço</p>
      </div>
    </div>
  </section>

  <section class="border-y border-forest/10 bg-white/45" aria-label="Princípios da plataforma">
    <div class="mx-auto grid max-w-7xl gap-px px-5 py-10 sm:grid-cols-3 sm:px-8 lg:px-12">
      {#each [
        ['01', 'Relevância primeiro', 'Compatibilidade, disponibilidade e confiança antes de qualquer destaque.'],
        ['02', 'Autonomia real', 'O profissional decide quando, onde e com quem deseja trabalhar.'],
        ['03', 'Privacidade por padrão', 'Região aproximada até existir motivo e consentimento para compartilhar mais.']
      ] as item (item[0])}
        <article class="border-forest/10 py-5 sm:border-l sm:px-7 sm:first:border-l-0 sm:first:pl-0">
          <span class="text-xs font-black tracking-widest text-coral">{item[0]}</span>
          <h2 class="mt-3 font-display text-xl font-bold">{item[1]}</h2>
          <p class="mt-2 text-sm leading-6 text-ink/60">{item[2]}</p>
        </article>
      {/each}
    </div>
  </section>
</main>

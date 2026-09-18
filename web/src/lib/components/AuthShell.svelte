<script lang="ts">
  import { resolve } from '$app/paths';
  import type { Snippet } from 'svelte';

  let { title, eyebrow, children }: { title: string; eyebrow: string; children: Snippet } = $props();
</script>

<main class="min-h-screen px-5 py-6 sm:px-8 sm:py-10">
  <nav class="mx-auto flex max-w-5xl items-center justify-between" aria-label="Navegação de autenticação">
    <a class="flex items-center gap-3 rounded-lg" href={resolve('/')} aria-label="Tucano, página inicial">
      <span class="grid size-10 place-items-center rounded-2xl bg-forest text-lg font-black text-white" aria-hidden="true">T</span>
      <span class="font-display text-2xl font-bold tracking-tight">tucano</span>
    </a>
    <a class="rounded-xl px-3 py-2 text-sm font-bold text-forest hover:bg-forest/5" href={resolve('/entrar')}>Entrar</a>
  </nav>

  <section class="mx-auto grid max-w-5xl items-start gap-10 py-12 lg:grid-cols-[0.8fr_1.2fr] lg:py-20">
    <header class="pt-3">
      <p class="text-xs font-black tracking-[0.16em] text-coral uppercase">{eyebrow}</p>
      <h1 class="mt-3 font-display text-4xl leading-tight font-bold tracking-tight sm:text-5xl">{title}</h1>
      <p class="mt-5 max-w-md leading-7 text-ink/60">Uma conta pode ter os dois perfis. Você escolhe como quer usar o Tucano a cada momento.</p>
    </header>

    <div class="rounded-[2rem] border border-white/80 bg-white/85 p-5 shadow-[0_24px_70px_rgb(24_35_30/0.11)] backdrop-blur sm:p-8">
      {@render children()}
    </div>
  </section>
</main>

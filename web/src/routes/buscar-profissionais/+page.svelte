<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import FormMessage from '$lib/components/FormMessage.svelte';
  import { errorMessage, getMe, listCategories, searchProfessionals, type ProfessionalSearchPage, type ServiceCategory } from '$lib/api';

  let categories: ServiceCategory[] = [];
  let categoryId = '';
  let radiusKm = 25;
  let availableNow = false;
  let latitude: number | undefined;
  let longitude: number | undefined;
  let result: ProfessionalSearchPage | null = null;
  let loading = true;
  let searching = false;
  let locating = false;
  let error = '';

  onMount(async () => {
    try {
      const [loadedCategories, user] = await Promise.all([listCategories(), getMe()]);
      if (!user.roles.includes('client')) {
        await goto(resolve('/conta'));
        return;
      }
      categories = loadedCategories;
    } catch {
      await goto(resolve('/entrar'));
    } finally {
      loading = false;
    }
  });

  function locate() {
    error = '';
    if (!navigator.geolocation) {
      error = 'Seu navegador não oferece acesso à localização.';
      return;
    }
    locating = true;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        latitude = position.coords.latitude;
        longitude = position.coords.longitude;
        locating = false;
      },
      () => {
        error = 'Não foi possível obter sua localização. Confira a permissão do navegador.';
        locating = false;
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
  }

  async function search(event: SubmitEvent) {
    event.preventDefault();
    if (latitude === undefined || longitude === undefined) {
      error = 'Use sua localização aproximada antes de buscar.';
      return;
    }
    searching = true;
    error = '';
    try {
      result = await searchProfessionals({ category_id: categoryId, latitude, longitude, radius_km: radiusKm, available_now: availableNow });
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      searching = false;
    }
  }

  function price(cents: number | null) {
    if (cents == null) return 'Valor a combinar';
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100);
  }
</script>

<svelte:head><title>Buscar profissionais — Tucano</title></svelte:head>

<main class="min-h-screen px-5 py-6 sm:px-8">
  <nav class="mx-auto flex max-w-6xl items-center justify-between" aria-label="Navegação">
    <a class="font-display text-2xl font-bold" href={resolve('/conta')}>tucano</a>
    <a class="text-sm font-bold text-forest hover:underline" href={resolve('/conta')}>Voltar à conta</a>
  </nav>
  <section class="mx-auto max-w-6xl py-10">
    <p class="text-xs font-black tracking-[0.16em] text-coral uppercase">Perto de você</p>
    <h1 class="mt-2 font-display text-4xl font-bold">Encontre profissionais</h1>
    <p class="mt-3 max-w-2xl leading-7 text-ink/60">A busca usa sua posição somente para calcular distância. Os resultados mostram regiões aproximadas, nunca coordenadas.</p>

    {#if loading}
      <p class="mt-10" role="status">Carregando busca…</p>
    {:else}
      <form class="form-card mt-8 grid gap-4 md:grid-cols-[1.4fr_0.7fr_auto] md:items-end" onsubmit={search}>
        <label><span class="form-label">Categoria</span><select class="form-input" bind:value={categoryId} required><option value="" disabled>Selecione</option>{#each categories as category (category.id)}<option value={category.id}>{category.name}</option>{/each}</select></label>
        <label><span class="form-label">Distância máxima</span><select class="form-input" bind:value={radiusKm}><option value={5}>5 km</option><option value={10}>10 km</option><option value={25}>25 km</option><option value={50}>50 km</option><option value={100}>100 km</option><option value={200}>200 km</option></select></label>
        <button class="secondary-button" type="button" disabled={locating} onclick={locate}>{locating ? 'Localizando…' : latitude !== undefined ? 'Localização pronta' : 'Usar localização'}</button>
        <label class="flex min-h-12 items-center gap-3 md:col-span-2"><input class="size-5 accent-forest" type="checkbox" bind:checked={availableNow} /><span class="font-bold">Mostrar somente disponíveis agora</span></label>
        <button class="primary-button" disabled={searching}>{searching ? 'Buscando…' : 'Buscar'}</button>
      </form>
      <div class="mt-5"><FormMessage message={error} /></div>

      {#if result}
        <div class="mt-10 flex items-end justify-between gap-4"><h2 class="font-display text-3xl font-bold">Resultados</h2><span class="text-sm text-ink/50">{result.total} encontrado{result.total === 1 ? '' : 's'}</span></div>
        <div class="mt-5 grid gap-5 md:grid-cols-2">
          {#each result.items as professional (professional.id)}
            <article class="overflow-hidden rounded-3xl border border-white bg-white/85 shadow-[0_18px_60px_rgb(24_35_30/0.08)]">
              {#if professional.cover_url}<img class="aspect-[16/8] w-full object-cover" src={professional.cover_url} alt="Portfólio de {professional.display_name}" />{/if}
              <div class="p-6">
                <div class="flex items-start justify-between gap-4"><div><p class="text-xs font-black tracking-widest text-coral uppercase">{professional.category.name}</p><h3 class="mt-1 font-display text-2xl font-bold">{professional.display_name}</h3></div>{#if professional.available_now}<span class="rounded-full bg-forest/10 px-3 py-1 text-xs font-bold text-forest">Disponível agora</span>{/if}</div>
                <p class="mt-3 line-clamp-3 leading-6 text-ink/60">{professional.bio || 'Perfil profissional em construção.'}</p>
                <div class="mt-4 flex flex-wrap gap-2">{#each professional.skills as skill (skill)}<span class="rounded-full bg-cream px-3 py-1 text-xs font-bold">{skill}</span>{/each}</div>
                <div class="mt-5 flex items-center justify-between border-t border-forest/10 pt-4 text-sm"><span>{professional.service_region} · aproximadamente {professional.distance_km.toLocaleString('pt-BR')} km</span><strong>{price(professional.reference_price_cents)}</strong></div>
              </div>
            </article>
          {:else}
            <div class="rounded-3xl border border-forest/10 bg-white/70 p-8 md:col-span-2"><h3 class="font-display text-2xl font-bold">Nenhum perfil nesta distância</h3><p class="mt-2 text-ink/55">Tente aumentar o raio ou remover o filtro “disponível agora”.</p></div>
          {/each}
        </div>
      {/if}
    {/if}
  </section>
</main>

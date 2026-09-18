<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import FormMessage from '$lib/components/FormMessage.svelte';
  import {
    deletePortfolioItem,
    errorMessage,
    getProfessionalProfile,
    listCategories,
    updateProfessionalProfile,
    uploadPortfolioItem,
    type Availability,
    type PortfolioItem,
    type ProfessionalProfile,
    type ServiceCategory
  } from '$lib/api';

  const weekdays = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];
  let categories: ServiceCategory[] = [];
  let profile: ProfessionalProfile | null = null;
  let categoryId = '';
  let bio = '';
  let skills = '';
  let serviceRegion = '';
  let serviceRadiusKm = 25;
  let referencePrice = '';
  let availableNow = false;
  let availabilities: Availability[] = [];
  let latitude: number | undefined;
  let longitude: number | undefined;
  let loading = true;
  let saving = false;
  let locating = false;
  let uploading = false;
  let error = '';
  let success = '';

  onMount(async () => {
    try {
      [categories, profile] = await Promise.all([listCategories(), getProfessionalProfile()]);
      categoryId = profile.primary_category?.id ?? '';
      bio = profile.bio;
      skills = profile.skills.join(', ');
      serviceRegion = profile.service_region;
      serviceRadiusKm = profile.service_radius_km;
      referencePrice = profile.reference_price_cents == null ? '' : (profile.reference_price_cents / 100).toFixed(2).replace('.', ',');
      availableNow = profile.available_now;
      availabilities = profile.availabilities.map((period) => ({ ...period }));
    } catch {
      await goto(resolve('/entrar'));
    } finally {
      loading = false;
    }
  });

  function useCurrentLocation() {
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

  function addAvailability() {
    availabilities = [...availabilities, { weekday: 1, start_time: '09:00', end_time: '18:00' }];
  }

  function removeAvailability(index: number) {
    availabilities = availabilities.filter((_, current) => current !== index);
  }

  async function save(event: SubmitEvent) {
    event.preventDefault();
    saving = true;
    error = '';
    success = '';
    const normalizedPrice = referencePrice.trim().replace(',', '.');
    const cents = normalizedPrice === '' ? null : Math.round(Number(normalizedPrice) * 100);
    if (cents !== null && (!Number.isFinite(cents) || cents < 0)) {
      error = 'Informe um preço de referência válido ou deixe o campo vazio.';
      saving = false;
      return;
    }
    try {
      profile = await updateProfessionalProfile({
        bio,
        primary_category_id: categoryId,
        skills: skills.split(',').map((item) => item.trim()).filter(Boolean),
        service_region: serviceRegion,
        ...(latitude !== undefined && longitude !== undefined ? { latitude, longitude } : {}),
        service_radius_km: serviceRadiusKm,
        reference_price_cents: cents,
        available_now: availableNow,
        availability_timezone: 'America/Sao_Paulo',
        availabilities: availabilities.map(({ weekday, start_time, end_time }) => ({ weekday: Number(weekday), start_time, end_time }))
      });
      success = 'Perfil profissional atualizado.';
      latitude = undefined;
      longitude = undefined;
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      saving = false;
    }
  }

  async function upload(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !profile) return;
    uploading = true;
    error = '';
    try {
      const item = await uploadPortfolioItem(file);
      profile = { ...profile, portfolio: [...profile.portfolio, item] };
    } catch (caught) {
      error = errorMessage(caught);
    } finally {
      input.value = '';
      uploading = false;
    }
  }

  async function removePortfolio(item: PortfolioItem) {
    if (!profile) return;
    error = '';
    try {
      await deletePortfolioItem(item.id);
      profile = { ...profile, portfolio: profile.portfolio.filter((current) => current.id !== item.id) };
    } catch (caught) {
      error = errorMessage(caught);
    }
  }
</script>

<svelte:head><title>Perfil profissional — Tucano</title></svelte:head>

<main class="min-h-screen px-5 py-6 sm:px-8">
  <nav class="mx-auto flex max-w-5xl items-center justify-between" aria-label="Navegação">
    <a class="font-display text-2xl font-bold" href={resolve('/conta')}>tucano</a>
    <a class="text-sm font-bold text-forest hover:underline" href={resolve('/conta')}>Voltar à conta</a>
  </nav>

  <section class="mx-auto max-w-5xl py-10">
    <p class="text-xs font-black tracking-[0.16em] text-coral uppercase">Seu trabalho</p>
    <h1 class="mt-2 font-display text-4xl font-bold">Perfil profissional</h1>
    <p class="mt-3 max-w-2xl leading-7 text-ink/60">Mostre o essencial para uma decisão rápida. Sua coordenada não aparece no perfil: exibimos somente a região e a distância aproximada.</p>

    {#if loading}
      <p class="mt-10" role="status">Carregando perfil…</p>
    {:else if profile}
      <form class="mt-10 space-y-8" onsubmit={save}>
        <FormMessage message={error} />
        <FormMessage message={success} tone="success" />

        <section class="form-card grid gap-5 sm:grid-cols-2">
          <label class="block sm:col-span-2">
            <span class="form-label">Categoria principal</span>
            <select class="form-input" bind:value={categoryId} required>
              <option value="" disabled>Selecione uma categoria</option>
              {#each categories as category (category.id)}
                <option value={category.id}>{category.name}</option>
              {/each}
            </select>
          </label>
          <label class="block sm:col-span-2">
            <span class="form-label">Apresentação</span>
            <textarea class="form-input min-h-32" bind:value={bio} maxlength="600" placeholder="Conte brevemente sua experiência e como trabalha."></textarea>
          </label>
          <label class="block sm:col-span-2">
            <span class="form-label">Habilidades</span>
            <input class="form-input" bind:value={skills} placeholder="Ex.: café especial, latte art, atendimento" />
            <span class="form-help">Separe por vírgulas. Até 20 habilidades.</span>
          </label>
          <label class="block">
            <span class="form-label">Região exibida</span>
            <input class="form-input" bind:value={serviceRegion} maxlength="120" placeholder="Ex.: Centro, Curitiba — PR" required />
          </label>
          <label class="block">
            <span class="form-label">Raio de atendimento</span>
            <select class="form-input" bind:value={serviceRadiusKm}>
              <option value={5}>5 km</option><option value={10}>10 km</option><option value={25}>25 km</option>
              <option value={50}>50 km</option><option value={100}>100 km</option><option value={200}>200 km</option>
            </select>
          </label>
          <div class="rounded-2xl border border-forest/10 bg-cream p-4 sm:col-span-2">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <strong class="block">Localização privada</strong>
                <span class="text-sm text-ink/55">{latitude !== undefined ? 'Nova localização pronta para salvar.' : profile.location_configured ? 'Localização já configurada.' : 'Necessária para aparecer na busca por distância.'}</span>
              </div>
              <button class="secondary-button" type="button" disabled={locating} onclick={useCurrentLocation}>{locating ? 'Localizando…' : 'Usar minha localização'}</button>
            </div>
          </div>
          <label class="block">
            <span class="form-label">Preço de referência <span class="font-normal text-ink/45">(opcional)</span></span>
            <input class="form-input" bind:value={referencePrice} inputmode="decimal" placeholder="Ex.: 180,00" />
          </label>
          <label class="flex min-h-12 items-center gap-3 rounded-2xl border border-forest/10 px-4">
            <input class="size-5 accent-forest" type="checkbox" bind:checked={availableNow} />
            <span class="font-bold">Disponível agora</span>
          </label>
        </section>

        <section class="form-card">
          <div class="flex items-center justify-between gap-4">
            <div><h2 class="font-display text-2xl font-bold">Disponibilidade semanal</h2><p class="mt-1 text-sm text-ink/55">Você mantém o controle e pode alterar quando quiser.</p></div>
            <button class="secondary-button" type="button" onclick={addAvailability}>Adicionar horário</button>
          </div>
          <div class="mt-5 space-y-3">
            {#each availabilities as period, index (period.id ?? index)}
              <div class="grid gap-3 rounded-2xl bg-cream p-4 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
                <label><span class="form-label">Dia</span><select class="form-input" bind:value={period.weekday}>{#each weekdays as day, value (day)}<option value={value}>{day}</option>{/each}</select></label>
                <label><span class="form-label">Início</span><input class="form-input" type="time" bind:value={period.start_time} required /></label>
                <label><span class="form-label">Fim</span><input class="form-input" type="time" bind:value={period.end_time} required /></label>
                <button class="secondary-button" type="button" onclick={() => removeAvailability(index)} aria-label="Remover horário">Remover</button>
              </div>
            {:else}
              <p class="rounded-2xl bg-cream p-4 text-sm text-ink/55">Nenhum horário recorrente informado.</p>
            {/each}
          </div>
        </section>

        <section class="form-card">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div><h2 class="font-display text-2xl font-bold">Portfólio</h2><p class="mt-1 text-sm text-ink/55">JPEG ou PNG, até 5 MB por imagem.</p></div>
            <label class="secondary-button cursor-pointer text-center">
              {uploading ? 'Enviando…' : 'Adicionar imagem'}
              <input class="sr-only" type="file" accept="image/jpeg,image/png" disabled={uploading} onchange={upload} />
            </label>
          </div>
          <div class="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {#each profile.portfolio as item (item.id)}
              <figure class="overflow-hidden rounded-2xl border border-forest/10 bg-white">
                <img class="aspect-square w-full object-cover" src={item.url} alt="Item do portfólio" />
                <button class="w-full px-3 py-2 text-sm font-bold text-coral" type="button" onclick={() => removePortfolio(item)}>Remover</button>
              </figure>
            {/each}
          </div>
        </section>

        <button class="primary-button w-full sm:w-auto" disabled={saving}>{saving ? 'Salvando…' : 'Salvar perfil'}</button>
      </form>
    {/if}
  </section>
</main>

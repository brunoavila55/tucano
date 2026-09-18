<script lang="ts">
  import '../app.css';

  let { children } = $props();
</script>

<svelte:head>
  <title>Tucano — profissionais disponíveis quando você precisa</title>
  <meta
    name="description"
    content="Encontre profissionais autônomos compatíveis, disponíveis e próximos de você."
  />
</svelte:head>

{@render children()}


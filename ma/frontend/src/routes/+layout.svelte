<script lang="ts">
  import './layout.css';
  import { page } from '$app/stores';
  import { Home, Cpu, LayoutDashboard, Database, Menu, ChevronLeft } from '@lucide/svelte';

  let { children } = $props();
  let isCollapsed = $state(false);

  // Sidebar items
  const menuItems = [
    { name: 'Main (Home)', path: '/', icon: Home },
    { name: 'Machine Status', path: '/machine-status', icon: Cpu }
  ];
</script>

<svelte:head>
  <title>MMS System Dashboard</title>
</svelte:head>

<div class="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-zinc-950">
  <!-- Sidebar -->
  <aside class="border-r border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col z-20 transition-all duration-300 {isCollapsed ? 'w-20' : 'w-64'}">
    <!-- Header -->
    <div class="h-16 flex items-center border-b border-slate-100 dark:border-zinc-800 gap-3 transition-all duration-300 {isCollapsed ? 'px-4 justify-center' : 'px-6'}">
      <LayoutDashboard class="h-6 w-6 text-emerald-600 dark:text-emerald-400 shrink-0" />
      {#if !isCollapsed}
        <span class="font-bold text-lg text-slate-800 dark:text-slate-100 tracking-wide whitespace-nowrap overflow-hidden">MMS DASHBOARD</span>
      {/if}
    </div>

    <!-- Navigation Menu -->
    <nav class="flex-1 py-6 px-4 space-y-1">
      {#each menuItems as item}
        {@const isActive = $page.url.pathname === item.path || ($page.url.pathname.startsWith(item.path) && item.path !== '/')}
        <a
          href={item.path}
          class="flex items-center rounded-xl font-medium text-sm transition-all duration-200 group gap-3
            {isCollapsed ? 'px-3 py-3 justify-center' : 'px-4 py-3'}
            {isActive 
              ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 shadow-sm border border-emerald-100/50 dark:border-emerald-900/30' 
              : 'text-slate-600 dark:text-zinc-400 hover:bg-slate-50 dark:hover:bg-zinc-800 hover:text-slate-900 dark:hover:text-zinc-200'}"
          title={isCollapsed ? item.name : ''}
        >
          <item.icon class="h-5 w-5 shrink-0 transition-transform duration-200 group-hover:scale-110" />
          {#if !isCollapsed}
            <span class="whitespace-nowrap overflow-hidden">{item.name}</span>
          {/if}
        </a>
      {/each}
    </nav>

    <!-- Footer -->
    <!-- <div class="p-4 border-t border-slate-100 dark:border-zinc-800 text-xs text-slate-400 dark:text-zinc-500 flex items-center gap-2 transition-all duration-300 {isCollapsed ? 'justify-center' : ''}">
      <Database class="h-4 w-4 text-slate-400 dark:text-zinc-500 shrink-0" />
      {#if !isCollapsed}
        <span class="whitespace-nowrap overflow-hidden">Status: API Connected</span>
      {/if}
    </div> -->
  </aside>

  <!-- Main Content Area -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <!-- Top Bar -->
    <header class="h-16 border-b border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-8 flex items-center justify-between z-10 shadow-sm">
      <div class="flex items-center gap-4">
        <!-- Collapse Toggle Button -->
        <button 
          onclick={() => isCollapsed = !isCollapsed} 
          class="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-500 dark:text-zinc-400 transition-colors cursor-pointer"
          aria-label="Toggle Sidebar"
        >
          {#if isCollapsed}
            <Menu class="h-5 w-5" />
          {:else}
            <ChevronLeft class="h-5 w-5" />
          {/if}
        </button>

        <div class="flex items-center gap-2">
          <span class="text-sm text-slate-400 dark:text-zinc-500">Workspace</span>
          <span class="text-sm text-slate-300 dark:text-zinc-700">/</span>
          <span class="text-sm font-medium text-slate-700 dark:text-zinc-300">
            {$page.url.pathname === '/' ? 'Home' : 'Machine Status'}
          </span>
        </div>
      </div>
      
      <!-- Date Display -->
      <div class="text-sm font-medium text-slate-500 dark:text-zinc-400">
        {new Date().toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
      </div>
    </header>

    <!-- Page Body -->
    <main class="flex-1 overflow-y-auto p-8">
      {@render children()}
    </main>
  </div>
</div>

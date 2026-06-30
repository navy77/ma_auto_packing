<script lang="ts">
  import { Cpu, ArrowRight, Play, CheckCircle } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
</script>

<div class="max-w-4xl mx-auto space-y-8">
  <!-- Hero Section -->
  <div class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 to-zinc-950 p-8 md:p-12 text-white shadow-xl">
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(16,185,129,0.1),transparent)]"></div>
    <div class="relative z-10 space-y-4 max-w-lg">
      <div class="inline-flex items-center gap-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider">
        <CheckCircle class="h-3.5 w-3.5" />
        System Operational
      </div>
      <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight">Machine Monitoring System</h1>
      <p class="text-slate-300 leading-relaxed text-sm md:text-base">
        Real-time telemetry, productivity tracking, and visual analysis of machine assembly and palletizing performance.
      </p>
      <div class="pt-2">
        <Button href="/machine-status" class="bg-emerald-600 hover:bg-emerald-500 text-white font-medium gap-2">
          View Machine Status
          <ArrowRight class="h-4 w-4" />
        </Button>
      </div>
    </div>
  </div>

  <!-- Highlights -->
  <div class="grid md:grid-cols-2 gap-6">
    <div class="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl p-6 shadow-sm space-y-4">
      <div class="h-10 w-10 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
        <Cpu class="h-6 w-6" />
      </div>
      <h2 class="text-lg font-bold text-slate-800 dark:text-slate-100">box_assy</h2>
      <p class="text-sm text-slate-500 dark:text-zinc-400 leading-relaxed">
        Tracks real-time status ratios, operating state timelines, and daily efficiency metrics for the box assembly unit.
      </p>
      <a href="/machine-status?mc=box_assy" class="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-600 dark:text-emerald-400 hover:underline">
        Monitor box_assy
        <ArrowRight class="h-3.5 w-3.5" />
      </a>
    </div>

    <div class="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl p-6 shadow-sm space-y-4">
      <div class="h-10 w-10 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
        <Cpu class="h-6 w-6" />
      </div>
      <h2 class="text-lg font-bold text-slate-800 dark:text-slate-100">palletizing</h2>
      <p class="text-sm text-slate-500 dark:text-zinc-400 leading-relaxed">
        Monitors packing efficiency, shift comparisons, alarms, and operating ratios for the palletizing unit.
      </p>
      <a href="/machine-status?mc=palletizing" class="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-600 dark:text-emerald-400 hover:underline">
        Monitor palletizing
        <ArrowRight class="h-3.5 w-3.5" />
      </a>
    </div>
  </div>
</div>

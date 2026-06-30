<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { RefreshCw, Play, Pause, AlertTriangle, Cpu } from '@lucide/svelte';
  import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
  import ChartComponent from '$lib/components/ChartComponent.svelte';

  // Config mapping of legend colors requested by the user
  const colors: Record<string, string> = {
    MC_RUN: '#2ecc71',
    MC_WAIT: '#f1c40f',
    MC_ALARM: '#f39c12',
    MC_STOP: '#e74c3c',
    'NO DATA': '#77716f'
  };

  // State options
  const machines = ['box_assy', 'palletizing'];
  const statuses = ['MC_RUN', 'MC_WAIT', 'MC_ALARM', 'MC_STOP'];

  // Reactive state
  let selectedMachine = $state('box_assy');
  let selectedStatus = $state('MC_RUN');
  let isAutoRefresh = $state(true);

  let pieData = $state<any[]>([]);
  let timelineData = $state<any[]>([]);
  let monthlyData = $state<any[]>([]);
  let shiftMData = $state<any[]>([]);
  let shiftNData = $state<any[]>([]);

  let isLoading = $state(false);
  let errorMessage = $state<string | null>(null);

  // Sync with URL query parameter if present
  $effect(() => {
    const mcParam = $page.url.searchParams.get('mc');
    if (mcParam && machines.includes(mcParam)) {
      selectedMachine = mcParam;
    }
  });

  // Data fetching logic
  async function fetchAllData() {
    isLoading = true;
    errorMessage = null;
    try {
      const mc = selectedMachine;
      const status = selectedStatus;
      
      // 1. Fetch Pie Chart Data
      const resPie = await fetch(`http://localhost:8001/status/ratio-daily/${mc}`);
      const pieJson = resPie.ok ? await resPie.json() : [];

      // 2. Fetch Timeline Chart Data
      const resTimeline = await fetch(`http://localhost:8001/status/timeline/${mc}`);
      const timelineJson = resTimeline.ok ? await resTimeline.json() : [];

      // 3. Fetch Monthly Stacked Bar Data
      const resMonthly = await fetch(`http://localhost:8001/status/ratio-monthly/${mc}`);
      const monthlyJson = resMonthly.ok ? await resMonthly.json() : { daily_data: [] };

      // 4. Fetch Monthly Shift Comparison Data for Selected Status
      const resM = await fetch(`http://localhost:8001/status/ratio-monthly/${mc}/M/${status}`);
      const mJson = resM.ok ? await resM.json() : { daily_data: [] };

      const resN = await fetch(`http://localhost:8001/status/ratio-monthly/${mc}/N/${status}`);
      const nJson = resN.ok ? await resN.json() : { daily_data: [] };

      // Update state reactively
      pieData = pieJson;
      timelineData = timelineJson;
      monthlyData = monthlyJson.daily_data || [];
      shiftMData = mJson.daily_data || [];
      shiftNData = nJson.daily_data || [];
    } catch (err: any) {
      console.error(err);
      errorMessage = "Failed to connect to the backend server. Please make sure the API is running at http://localhost:8001.";
    } finally {
      isLoading = false;
    }
  }

  // Refetch data when machine or status changes
  $effect(() => {
    // This will run immediately on mount and whenever selectedMachine or selectedStatus changes
    fetchAllData();
  });

  // Auto-refresh interval
  $effect(() => {
    if (!isAutoRefresh) return;
    const interval = setInterval(() => {
      fetchAllData();
    }, 10000);

    return () => clearInterval(interval);
  });

  // ECharts Configurations
  // 1. Pie Chart Options
  let pieOption = $derived({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}%'
    },
    legend: {
      bottom: '0%',
      left: 'center',
      data: ['MC_RUN', 'MC_WAIT', 'MC_ALARM', 'MC_STOP'],
      textStyle: { color: '#888' }
    },
    series: [
      {
        name: 'Status Ratio',
        type: 'pie',
        radius: ['45%', '75%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}: {c}%',
          fontSize: 12
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 13,
            fontWeight: 'bold'
          }
        },
        data: pieData.map(item => ({
          name: item.status,
          value: item.ratio,
          itemStyle: { color: colors[item.status] || '#95a5a6' }
        }))
      }
    ]
  } as any);

  // 2. Timeline Chart Range and Render Options
  const getTimelineRange = () => {
    const now = new Date();
    const start = new Date(now);
    if (now.getHours() < 7) {
      start.setDate(start.getDate() - 1);
    }
    start.setHours(7, 0, 0, 0);
    const end = new Date(start);
    end.setDate(end.getDate() + 1);
    return { min: start.getTime(), max: end.getTime() };
  };

  const renderItem = (params: any, api: any) => {
    const categoryIndex = api.value(0);
    const start = api.coord([api.value(1), categoryIndex]);
    const end = api.coord([api.value(2), categoryIndex]);
    const height = api.size([0, 1])[1] * 0.6;
    return {
      type: 'rect',
      shape: {
        x: start[0],
        y: start[1] - height / 2,
        width: Math.max(end[0] - start[0], 0.5),
        height: height
      },
      style: api.style()
    };
  };

  let timelineOption = $derived({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const status = params.value[3];
        const startStr = new Date(params.value[1]).toLocaleTimeString();
        const endStr = new Date(params.value[2]).toLocaleTimeString();
        const durationMin = Math.round((params.value[2] - params.value[1]) / 60000);
        return `<b>${status}</b><br/>Start: ${startStr}<br/>End: ${endStr}<br/>Duration: ${durationMin} min`;
      }
    },
    xAxis: {
      type: 'value',
      min: getTimelineRange().min,
      max: getTimelineRange().max,
      interval: 3 * 3600 * 1000,
      axisLabel: {
        formatter: (value: number) => {
          const date = new Date(value);
          const hours = String(date.getHours()).padStart(2, '0');
          const minutes = String(date.getMinutes()).padStart(2, '0');
          return `${hours}:${minutes}`;
        }
      }
    },
    yAxis: {
      type: 'category',
      data: [selectedMachine],
      show: false
    },
    grid: {
      left: '2%',
      right: '2%',
      top: '10%',
      bottom: '15%'
    },
    legend: {
      bottom: '0%',
      left: 'center',
      data: ['MC_RUN', 'MC_WAIT', 'MC_ALARM', 'MC_STOP'],
      textStyle: { color: '#888' }
    },
    series: [
      {
        type: 'custom',
        renderItem: renderItem,
        encode: { x: [1, 2], y: 0 },
        data: timelineData.map(row => {
          const startDt = new Date(row.ts);
          const endDt = new Date(startDt.getTime() + row.duration * 1000);
          return {
            name: row.status,
            value: [0, startDt.getTime(), endDt.getTime(), row.status],
            itemStyle: {
              color: colors[row.status] || '#77716f'
            }
          };
        })
      },
      ...['MC_RUN', 'MC_WAIT', 'MC_ALARM', 'MC_STOP'].map(status => ({
        name: status,
        type: 'bar',
        data: [],
        itemStyle: { color: colors[status] }
      }))
    ]
  } as any);

  // 3. Stacked 100% Bar Chart Options
  let stackOption = $derived({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      bottom: '0%',
      left: 'center',
      data: ['MC_RUN', 'MC_WAIT', 'MC_ALARM', 'MC_STOP'],
      textStyle: { color: '#888' }
    },
    grid: {
      left: '3%',
      right: '3%',
      bottom: '12%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: monthlyData.map(d => d.date)
    },
    yAxis: {
      type: 'value',
      name: 'Ratio (%)',
      min: 0,
      max: 100
    },
    series: ['MC_RUN', 'MC_WAIT', 'MC_ALARM', 'MC_STOP', 'NO DATA'].map(status => ({
      name: status,
      type: 'bar',
      stack: 'total',
      emphasis: { focus: 'series' },
      data: monthlyData.map(d => {
        const detail = d.details?.find((det: any) => det.status === status);
        return detail ? detail.ratio : 0;
      }),
      itemStyle: { color: colors[status] || '#77716f' }
    }))
  } as any);

  // 4. Smooth Line Chart Options (comparing M and N shift)
  let lineOption = $derived({
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      bottom: '0%',
      left: 'center',
      data: ['Shift M', 'Shift N', 'MC_RUN', 'MC_WAIT', 'MC_ALARM', 'MC_STOP'],
      textStyle: { color: '#888' }
    },
    grid: {
      left: '3%',
      right: '3%',
      bottom: '12%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: shiftMData.map(d => d.date)
    },
    yAxis: {
      type: 'value',
      name: 'Ratio (%)',
      min: 0,
      max: 100
    },
    series: [
      {
        name: 'Shift M',
        type: 'line',
        smooth: true,
        data: shiftMData.map(d => d.details && d.details.length > 0 ? d.details[0].ratio : 0),
        itemStyle: { color: '#3b82f6' },
        lineStyle: { width: 3 }
      },
      {
        name: 'Shift N',
        type: 'line',
        smooth: true,
        data: shiftNData.map(d => d.details && d.details.length > 0 ? d.details[0].ratio : 0),
        itemStyle: { color: '#f59e0b' },
        lineStyle: { width: 3 }
      },
      ...['MC_RUN', 'MC_WAIT', 'MC_ALARM', 'MC_STOP'].map(status => ({
        name: status,
        type: 'line',
        data: [],
        itemStyle: { color: colors[status] }
      }))
    ]
  } as any);
</script>

<div class="space-y-6">
  <!-- Controls Section -->
  <div class="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
    <div class="flex flex-wrap items-center gap-4">
      <!-- Machine Selection Dropdown -->
      <div class="space-y-1">
        <label for="machine-select" class="block text-xs font-semibold text-slate-400 dark:text-zinc-500 uppercase tracking-wider">Select Machine</label>
        <div class="relative">
          <select 
            id="machine-select" 
            bind:value={selectedMachine} 
            class="h-9 w-48 rounded-lg border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-sm font-semibold text-slate-700 dark:text-zinc-200 px-3 pr-8 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 appearance-none"
          >
            {#each machines as mc}
              <option value={mc}>{mc}</option>
            {/each}
          </select>
          <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
            <Cpu class="h-4 w-4" />
          </div>
        </div>
      </div>
      
      <!-- Auto-refresh Controller -->
      <div class="flex items-center gap-2 mt-4 md:mt-0">
        <button 
          onclick={() => isAutoRefresh = !isAutoRefresh}
          class="flex items-center gap-2 h-9 px-3 text-sm font-semibold border rounded-lg border-slate-200 dark:border-zinc-800 transition-colors
            {isAutoRefresh 
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/30' 
              : 'bg-white text-slate-600 dark:bg-zinc-900 dark:text-zinc-300'}"
        >
          {#if isAutoRefresh}
            <Play class="h-4 w-4 fill-current animate-pulse" />
            <span>Auto Refresh On (10s)</span>
          {:else}
            <Pause class="h-4 w-4" />
            <span>Auto Refresh Off</span>
          {/if}
        </button>

        <!-- Manual Refresh Button -->
        <button 
          onclick={fetchAllData}
          disabled={isLoading}
          class="flex items-center gap-2 h-9 px-3 text-sm font-semibold border border-slate-200 dark:border-zinc-800 rounded-lg bg-white dark:bg-zinc-900 text-slate-600 dark:text-zinc-300 hover:bg-slate-50 dark:hover:bg-zinc-800 disabled:opacity-50 transition-colors"
        >
          <RefreshCw class="h-4 w-4 {isLoading ? 'animate-spin' : ''}" />
          <span>Refresh</span>
        </button>
      </div>
    </div>
    
    <!-- Legend Quick Reference -->
    <div class="flex flex-wrap items-center gap-4 text-xs font-semibold text-slate-500 dark:text-zinc-400">
      <span class="text-slate-400 dark:text-zinc-500 uppercase text-[10px] tracking-wider">Legend:</span>
      {#each Object.entries(colors) as [status, color]}
        <div class="flex items-center gap-1.5">
          <span class="h-3 w-3 rounded-full" style="background-color: {color}"></span>
          <span>{status}</span>
        </div>
      {/each}
    </div>
  </div>

  <!-- Error Notification -->
  {#if errorMessage}
    <div class="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30 rounded-xl p-4 text-amber-800 dark:text-amber-300 flex items-start gap-3">
      <AlertTriangle class="h-5 w-5 shrink-0 mt-0.5" />
      <div>
        <h4 class="font-bold text-sm">Connection Issue</h4>
        <p class="text-xs leading-relaxed mt-1">{errorMessage}</p>
      </div>
    </div>
  {/if}

  <!-- Dashboard 2x2 Grid of ECharts -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    
    <!-- Graph 3.1: Pie Chart (Top Left) -->
    <Card class="border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
      <CardHeader class="pb-2">
        <CardTitle class="text-base font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wide">Daily Status Ratio</CardTitle>
        <CardDescription class="text-xs">Operation status breakdown for today</CardDescription>
      </CardHeader>
      <CardContent class="h-80">
        {#if pieData.length > 0}
          <ChartComponent options={pieOption} height="100%" />
        {:else}
          <div class="h-full flex items-center justify-center text-slate-400 text-sm">No data available</div>
        {/if}
      </CardContent>
    </Card>

    <!-- Graph 3.2: Timeline Chart (Top Right) -->
    <Card class="border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
      <CardHeader class="pb-2">
        <CardTitle class="text-base font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wide">Machine Timeline</CardTitle>
        <CardDescription class="text-xs">Chronological operating states for today's shift</CardDescription>
      </CardHeader>
      <CardContent class="h-80">
        {#if timelineData.length > 0}
          <ChartComponent options={timelineOption} height="100%" />
        {:else}
          <div class="h-full flex items-center justify-center text-slate-400 text-sm">No data available</div>
        {/if}
      </CardContent>
    </Card>

    <!-- Graph 3.3: 100% Stacked Bar Chart (Bottom Left) -->
    <Card class="border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
      <CardHeader class="pb-2">
        <CardTitle class="text-base font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wide">Monthly Operation Ratio</CardTitle>
        <CardDescription class="text-xs">Day-by-day status ratio stacks for this month</CardDescription>
      </CardHeader>
      <CardContent class="h-80">
        {#if monthlyData.length > 0}
          <ChartComponent options={stackOption} height="100%" />
        {:else}
          <div class="h-full flex items-center justify-center text-slate-400 text-sm">No data available</div>
        {/if}
      </CardContent>
    </Card>

    <!-- Graph 3.4: Smooth Line Chart (Bottom Right) -->
    <Card class="border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm flex flex-col justify-between">
      <CardHeader class="pb-2 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <CardTitle class="text-base font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wide">Shift Comparison (M vs N)</CardTitle>
          <CardDescription class="text-xs">Compare monthly ratios for the selected status</CardDescription>
        </div>
        <!-- Status select dropdown specifically for the line comparison chart -->
        <div class="relative">
          <select 
            id="status-select" 
            bind:value={selectedStatus} 
            class="h-8 rounded-lg border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs font-bold text-slate-700 dark:text-zinc-200 px-3 pr-8 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 appearance-none min-w-[120px]"
          >
            {#each statuses as st}
              <option value={st}>{st}</option>
            {/each}
          </select>
          <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
            <span class="h-2 w-2 rounded-full" style="background-color: {colors[selectedStatus]}"></span>
          </div>
        </div>
      </CardHeader>
      <CardContent class="h-80">
        {#if shiftMData.length > 0 || shiftNData.length > 0}
          <ChartComponent options={lineOption} height="100%" />
        {:else}
          <div class="h-full flex items-center justify-center text-slate-400 text-sm">No data available</div>
        {/if}
      </CardContent>
    </Card>

  </div>
</div>

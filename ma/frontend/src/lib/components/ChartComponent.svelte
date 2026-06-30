<script lang="ts">
  import { onMount } from 'svelte';
  import * as echarts from 'echarts';

  let { options, height = '350px', width = '100%' } = $props<{
    options: echarts.EChartsOption;
    height?: string;
    width?: string;
  }>();

  let chartDom: HTMLDivElement = $state() as any;
  let chartInstance: echarts.ECharts | null = null;

  onMount(() => {
    // Initialize chart
    chartInstance = echarts.init(chartDom);
    
    if (options) {
      chartInstance.setOption(options);
    }

    // Dynamic resize observer
    const resizeObserver = new ResizeObserver(() => {
      chartInstance?.resize();
    });
    resizeObserver.observe(chartDom);

    return () => {
      resizeObserver.disconnect();
      chartInstance?.dispose();
    };
  });

  // React to options changes
  $effect(() => {
    if (chartInstance && options) {
      chartInstance.setOption(options, true);
    }
  });
</script>

<div bind:this={chartDom} style:width style:height class="w-full h-full"></div>

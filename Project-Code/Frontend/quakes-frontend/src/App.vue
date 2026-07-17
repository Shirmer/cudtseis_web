<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
html {
  scroll-behavior: smooth;
  background: #f5f6f3;
}

body {
  margin: 0;
  padding: 0;
  min-width: 320px;
  background: #f5f6f3;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

button,
input,
textarea,
select {
  font: inherit;
}

::selection {
  color: #fff;
  background: #9f2c24;
}
</style>

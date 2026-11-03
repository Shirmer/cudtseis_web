<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
html {
  scroll-behavior: smooth;
  background: #f6f4ef;
}

body {
  margin: 0;
  padding: 0;
  min-width: 320px;
  background: #f6f4ef;
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
  background: #d97a1c;
}
</style>

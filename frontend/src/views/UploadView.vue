<template>
  <div>
    <!-- <Header /> --> <!-- старое использование -->
    <AppHeader /> <!-- новое использование -->
    <!-- ...existing code... -->
  </div>
</template>

<script>
// import Header from '@/components/Header.vue'  // старый импорт
import AppHeader from '@/components/AppHeader.vue'  // новый импорт
// ...existing code...

export default {
  // ...existing code...
  components: {
    AppHeader,
    // ...existing code...
  }
}
</script>
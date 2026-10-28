<template>
  <div class="app">
    <Header />
    <main>
      <router-view />
    </main>
    <footer class="footer">
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
        class="icp-link"
      >湘ICP备2026047657号</a>
    </footer>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import Header from '@/components/Header.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  authStore.initFromStorage()
})
</script>

<style>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

main {
  flex: 1;
}

.footer {
  border-top: 1px solid #e0e0e0;
  padding: 16px 0;
  text-align: center;
}

.icp-link {
  font-size: 13px;
  color: #999999;
  text-decoration: none;
  transition: color 0.2s;
}

.icp-link:hover {
  color: #1a1a1a;
}
</style>

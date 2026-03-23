<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="shell">
    <header class="masthead reveal">
      <div class="brand-cluster">
        <p class="micro">Operations Console</p>
        <h1>Scraper Control Atlas</h1>
        <p class="subtitle">Tum veri toplama akislarini tek merkezden takip et, calistir ve dogrula.</p>
      </div>
      <nav class="rail">
        <RouterLink to="/" class="nav-chip">Giris</RouterLink>
        <RouterLink to="/data" class="nav-chip">Veri</RouterLink>
        <RouterLink to="/grants" class="nav-chip">Hibe</RouterLink>
        <RouterLink to="/itu" class="nav-chip">ITU</RouterLink>
      </nav>
    </header>

    <main class="stage">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
}

.masthead {
  margin: 20px auto 0;
  width: min(1200px, calc(100% - 24px));
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid #ccbfae;
  border-radius: 20px;
  padding: 20px;
  background: linear-gradient(180deg, rgba(255, 253, 247, 0.9), rgba(244, 234, 220, 0.94));
  box-shadow: 0 20px 42px rgba(29, 39, 56, 0.11);
}

.micro {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #136f63;
}

h1 {
  margin-top: 3px;
  font-size: clamp(28px, 5vw, 46px);
  color: #111d2d;
}

.subtitle {
  margin-top: 8px;
  max-width: 560px;
  color: #2f4057;
}

.rail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.nav-chip {
  text-decoration: none;
  color: #23344b;
  background: #f8f0e2;
  border: 1px solid #c9baa7;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 14px;
  font-weight: 700;
  transition: all 0.18s ease;
}

.nav-chip.router-link-active {
  color: #fff;
  background: #111d2d;
  border-color: #111d2d;
}

.stage {
  width: min(1200px, calc(100% - 24px));
  margin: 0 auto;
  padding: 18px 0 26px;
}

@media (max-width: 720px) {
  .masthead {
    margin-top: 10px;
    padding: 16px;
  }

  .subtitle {
    font-size: 14px;
  }
}
</style>

<template>
  <div class="home-page">
    <!-- Hero Section -->
    <div class="hero-section">
      <h1 class="hero-title">
        <span class="gradient-text">{{ $t('home.welcome') }}</span>
      </h1>
      <p class="hero-subtitle">{{ $t('home.subtitle') }}</p>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div 
        v-for="(stat, index) in statCards" 
        :key="stat.key"
        class="stat-card"
        :style="{ animationDelay: `${index * 0.1}s` }"
      >
        <div class="stat-icon-wrapper">
          <component :is="stat.icon" class="stat-icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value" :data-target="stat.value">{{ animatedStats[stat.key] || 0 }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
        <div class="stat-glow"></div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <router-link 
        v-for="(action, index) in actions" 
        :key="action.path"
        :to="action.path" 
        class="action-card"
        :style="{ animationDelay: `${(statCards.length + index) * 0.1}s` }"
      >
        <div class="action-icon-wrapper">
          <component :is="action.icon" class="action-icon" />
          <div class="action-glow"></div>
        </div>
        <div class="action-title">{{ action.title }}</div>
        <div class="action-description">{{ action.description }}</div>
        <div class="ripple-effect"></div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../services/api'
import { Upload, Search, MessageSquare, CheckSquare, FileText, Clock, TrendingUp } from 'lucide-vue-next'

const { t } = useI18n()

const stats = ref({
  totalDocuments: 0,
  pendingTasks: 0,
  recentUploads: 0
})

const animatedStats = ref({
  totalDocuments: 0,
  pendingTasks: 0,
  recentUploads: 0
})

const statCards = computed(() => {
  const { t } = useI18n()
  return [
    {
      key: 'totalDocuments',
      label: t('home.totalDocuments'),
      icon: FileText,
      value: stats.value.totalDocuments
    },
    {
      key: 'pendingTasks',
      label: t('home.pendingTasks'),
      icon: Clock,
      value: stats.value.pendingTasks
    },
    {
      key: 'recentUploads',
      label: t('home.recentUploads'),
      icon: TrendingUp,
      value: stats.value.recentUploads
    }
  ]
})

const actions = computed(() => {
  const { t } = useI18n()
  return [
    {
      path: '/documents',
      title: t('nav.documents'),
      description: t('home.viewAllDocuments'),
      icon: FileText
    },
    {
      path: '/upload',
      title: t('home.uploadDocuments'),
      description: t('home.addNewDocuments'),
      icon: Upload
    },
    {
      path: '/search',
      title: t('home.search'),
      description: t('home.findDocumentsQuickly'),
      icon: Search
    },
    {
      path: '/chatbot',
      title: t('home.chatbot'),
      description: t('home.askAI'),
      icon: MessageSquare
    },
    {
      path: '/tasks',
      title: t('home.tasks'),
      description: t('home.manageWorkflow'),
      icon: CheckSquare
    }
  ]
})

const animateValue = (key, start, end, duration) => {
  const startTime = performance.now()
  const animate = (currentTime) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easeOutQuart = 1 - Math.pow(1 - progress, 4)
    animatedStats.value[key] = Math.floor(start + (end - start) * easeOutQuart)
    
    if (progress < 1) {
      requestAnimationFrame(animate)
    } else {
      animatedStats.value[key] = end
    }
  }
  requestAnimationFrame(animate)
}

watch(() => stats.value, (newStats) => {
  Object.keys(newStats).forEach(key => {
    animateValue(key, animatedStats.value[key] || 0, newStats[key], 1000)
  })
}, { deep: true })

onMounted(async () => {
  // Load stats
  try {
    const res = await api.get('/reports/usage')
    if (res.is_success && res.data) {
      stats.value = {
        totalDocuments: res.data.total_documents || 0,
        pendingTasks: res.data.pending_tasks || 0,
        recentUploads: res.data.recent_uploads || 0
      }
    }
  } catch (e) {
    console.error('Failed to load stats', e)
  }
})
</script>

<style scoped>
.home-page {
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeIn var(--transition-base) var(--ease-out);
}

/* Hero Section */
.hero-section {
  text-align: center;
  padding: var(--space-3xl) var(--space-xl);
  margin-bottom: var(--space-3xl);
  animation: fadeInDown var(--transition-slow) var(--ease-out);
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 800;
  margin: 0 0 var(--space-md) 0;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.hero-subtitle {
  font-size: 1.25rem;
  color: var(--text-medium);
  font-weight: 500;
  margin: 0;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-xl);
  margin-bottom: var(--space-3xl);
}

.stat-card {
  position: relative;
  background: var(--bg-white);
  padding: var(--space-xl);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  text-align: center;
  overflow: hidden;
  transition: all var(--transition-base);
  animation: fadeInUp var(--transition-base) var(--ease-out) both;
  border: 1px solid transparent;
  background-clip: padding-box;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: var(--radius-xl);
  padding: 2px;
  background: var(--gradient-cyan-purple);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity var(--transition-base);
}

.stat-card:hover::before {
  opacity: 1;
}

.stat-card:hover {
  transform: translateY(-8px);
  box-shadow: var(--shadow-2xl), var(--shadow-glow-cyan);
}

.stat-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(0, 217, 255, 0.2) 0%, transparent 70%);
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity var(--transition-base);
  pointer-events: none;
}

.stat-card:hover .stat-glow {
  opacity: 1;
}

.stat-icon-wrapper {
  width: 64px;
  height: 64px;
  margin: 0 auto var(--space-lg);
  border-radius: var(--radius-full);
  background: var(--gradient-cyan-purple);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-glow-cyan);
  transition: all var(--transition-base);
}

.stat-card:hover .stat-icon-wrapper {
  transform: scale(1.1) rotate(5deg);
  box-shadow: var(--shadow-glow-ai);
}

.stat-icon {
  width: 32px;
  height: 32px;
  color: white;
  stroke-width: 2.5;
}

.stat-content {
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: 3rem;
  font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: var(--space-sm);
  line-height: 1;
  letter-spacing: -0.02em;
}

.stat-label {
  color: var(--text-medium);
  font-size: 0.95rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Quick Actions */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-xl);
}

.action-card {
  position: relative;
  background: var(--bg-white);
  padding: var(--space-2xl);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  text-align: center;
  text-decoration: none;
  color: inherit;
  transition: all var(--transition-base);
  overflow: hidden;
  animation: fadeInUp var(--transition-base) var(--ease-out) both;
  border: 2px solid transparent;
}

.action-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--gradient-ai-soft);
  opacity: 0;
  transition: opacity var(--transition-base);
  z-index: 0;
}

.action-card:hover::before {
  opacity: 1;
}

.action-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: var(--shadow-2xl), var(--shadow-glow);
  border-color: var(--ai-cyan);
}

.action-icon-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto var(--space-lg);
  z-index: 1;
}

.action-icon {
  width: 48px;
  height: 48px;
  color: var(--primary);
  stroke-width: 2;
  transition: all var(--transition-base);
  position: relative;
  z-index: 2;
}

.action-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  background: var(--gradient-cyan-purple);
  border-radius: var(--radius-full);
  transform: translate(-50%, -50%) scale(0.8);
  opacity: 0;
  transition: all var(--transition-base);
  filter: blur(10px);
}

.action-card:hover .action-glow {
  opacity: 0.6;
  transform: translate(-50%, -50%) scale(1.2);
}

.action-card:hover .action-icon {
  transform: scale(1.1) rotate(5deg);
  color: var(--ai-cyan);
  filter: drop-shadow(0 0 8px rgba(0, 217, 255, 0.6));
}

.action-title {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text-dark);
  margin-bottom: var(--space-xs);
  position: relative;
  z-index: 1;
  transition: color var(--transition-base);
}

.action-card:hover .action-title {
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.action-description {
  font-size: 0.9rem;
  color: var(--text-light);
  position: relative;
  z-index: 1;
}

.ripple-effect {
  position: absolute;
  border-radius: 50%;
  background: rgba(0, 217, 255, 0.3);
  transform: scale(0);
  animation: ripple 0.6s var(--ease-out);
  pointer-events: none;
  opacity: 0;
}

.action-card:active .ripple-effect {
  animation: ripple 0.6s var(--ease-out);
  opacity: 1;
}

@keyframes ripple {
  to {
    transform: scale(4);
    opacity: 0;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }
  
  .hero-subtitle {
    font-size: 1rem;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>


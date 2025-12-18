<template>
  <div class="scan-page">
    <div class="coming-soon-container">
      <div class="coming-soon-content">
        <div class="icon-wrapper">
          <Scan class="coming-soon-icon" />
        </div>
        <h1 class="coming-soon-title">Scan Inbox</h1>
        <p class="coming-soon-subtitle">Coming Soon</p>
        <p class="coming-soon-description">
          The automatic scan feature is under development. You will be able to:
        </p>
        <ul class="feature-list">
          <li>
            <CheckCircle class="feature-icon" />
            <span>Receive and manage documents automatically scanned from scanners</span>
          </li>
          <li>
            <CheckCircle class="feature-icon" />
            <span>Preview and process scanned documents</span>
          </li>
          <li>
            <CheckCircle class="feature-icon" />
            <span>Assign documents to users or folders</span>
          </li>
          <li>
            <CheckCircle class="feature-icon" />
            <span>Track scan status and history</span>
          </li>
        </ul>
        <div class="coming-soon-footer">
          <p class="footer-text">This feature will be available soon in the next version.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Scan, CheckCircle } from 'lucide-vue-next'
</script>

<style scoped>
.scan-page {
  min-height: calc(100vh - 200px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.coming-soon-container {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.coming-soon-content {
  background: white;
  border-radius: 16px;
  padding: 4rem 3rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.icon-wrapper {
  margin-bottom: 2rem;
  display: flex;
  justify-content: center;
}

.coming-soon-icon {
  width: 120px;
  height: 120px;
  color: var(--primary, #4f46e5);
  opacity: 0.8;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.8;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.05);
  }
}

.coming-soon-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--primary, #4f46e5);
  margin: 0 0 0.5rem 0;
}

.coming-soon-subtitle {
  font-size: 1.5rem;
  font-weight: 600;
  color: #666;
  margin: 0 0 2rem 0;
  position: relative;
  display: inline-block;
}

.coming-soon-subtitle::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, var(--primary, #4f46e5), var(--ai-cyan, #00d9ff));
  border-radius: 2px;
}

.coming-soon-description {
  font-size: 1.1rem;
  color: #555;
  margin: 2rem 0 1.5rem 0;
  line-height: 1.6;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 2rem 0;
  text-align: left;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.feature-list li {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  margin-bottom: 0.75rem;
  background: var(--bg-light, #f8f9fa);
  border-radius: 8px;
  transition: all 0.3s ease;
}

.feature-list li:hover {
  background: #e9ecef;
  transform: translateX(5px);
}

.feature-icon {
  width: 24px;
  height: 24px;
  color: var(--primary, #4f46e5);
  flex-shrink: 0;
  margin-top: 2px;
}

.feature-list li span {
  color: #555;
  font-size: 1rem;
  line-height: 1.5;
}

.coming-soon-footer {
  margin-top: 3rem;
  padding-top: 2rem;
  border-top: 1px solid #e9ecef;
}

.footer-text {
  color: #888;
  font-size: 0.95rem;
  font-style: italic;
  margin: 0;
}

@media (max-width: 768px) {
  .coming-soon-content {
    padding: 2rem 1.5rem;
  }

  .coming-soon-title {
    font-size: 2rem;
  }

  .coming-soon-subtitle {
    font-size: 1.25rem;
  }

  .coming-soon-icon {
    width: 80px;
    height: 80px;
  }

  .feature-list {
    margin-left: 0;
    margin-right: 0;
  }

  .feature-list li {
    padding: 0.75rem;
  }
}
</style>

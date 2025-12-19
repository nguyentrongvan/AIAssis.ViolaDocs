<template>
  <div></div>
</template>

<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../store/auth'
import Driver from 'driver.js'

const router = useRouter()
const { t, locale } = useI18n()
const authStore = useAuthStore()

let driverObj = null
let globalResizeHandler = null
let globalResizeTimeout = null
let globalViewportCheckInterval = null
let lastViewportWidth = window.innerWidth
let lastViewportHeight = window.innerHeight
let isRestartingTour = false
let tourJustStarted = false
let tourStartTime = 0
let lastNextClickTime = 0

const buildTourSteps = () => {
  const steps = []
  
  // Helper function to add button texts to popover
  const addButtonTexts = (popoverConfig, isFirst = false, isLast = false) => {
    const prevBtnTextValue = isFirst ? null : t('onboarding.previous')
    const nextBtnTextValue = isLast ? t('onboarding.finish') : t('onboarding.next')
    const closeBtnTextValue = t('common.close')
    const result = {
      ...popoverConfig,
      showButtons: true,
      nextBtnText: nextBtnTextValue,
      closeBtnText: closeBtnTextValue
    }
    // Only add prevBtnText if not first step
    // Driver.js will show button with default "Previous" if not set, so we use CSS to hide it
    if (!isFirst) {
      result.prevBtnText = prevBtnTextValue
    }
    // For first step, don't set prevBtnText at all - CSS will handle hiding the button
    return result
  }
  
  // Step 1: Welcome (centered on page)
  steps.push({
    element: 'body',
    popover: addButtonTexts({
      title: t('onboarding.steps.welcome.title'),
      description: t('onboarding.steps.welcome.description'),
      position: 'mid-center'
    }, true, false)
  })
  
  // Step 2: Sidebar Navigation
  const sidebar = document.querySelector('.sidebar')
  if (sidebar) {
      steps.push({
        element: '.sidebar',
        popover: addButtonTexts({
          title: t('onboarding.steps.sidebar.title'),
          description: t('onboarding.steps.sidebar.description'),
          position: 'right'
        })
      })
  }
  
  // Step 3: LLM Settings Setup (IMPORTANT - only for admin/staff/maintainer)
  if (authStore.isAdmin || authStore.isStaff || authStore.isMaintainer || authStore.hasPermission('settings')) {
    // Wait a bit for DOM to be ready, then find Settings link
    // Try multiple methods to find the Settings link
    let settingsLink = null
    
    // Method 1: Find by href attribute (Vue Router might use hash or full path)
    settingsLink = document.querySelector('nav a[href="/admin/settings"]') || 
                   document.querySelector('nav a[href*="/admin/settings"]') ||
                   document.querySelector('.sidebar nav a[href*="settings"]')
    
    // Method 2: Find by text content "Settings" in nav items
    if (!settingsLink) {
      const allNavLinks = Array.from(document.querySelectorAll('.sidebar nav a.nav-item'))
      settingsLink = allNavLinks.find(link => {
        const text = link.textContent?.trim().toLowerCase() || ''
        const href = link.getAttribute('href') || ''
        // Check if text contains "settings" or href contains "/admin/settings"
        return text.includes('settings') || href.includes('/admin/settings')
      })
    }
    
    // Method 3: Find by looking for Settings icon and its parent link
    if (!settingsLink) {
      const settingsIcons = Array.from(document.querySelectorAll('.sidebar nav .nav-icon'))
      const settingsIcon = settingsIcons.find(icon => {
        // Check if this icon is in a link that goes to settings
        const link = icon.closest('a')
        if (link) {
          const href = link.getAttribute('href') || ''
          const text = link.textContent?.trim().toLowerCase() || ''
          return href.includes('/admin/settings') || text.includes('settings')
        }
        return false
      })
      if (settingsIcon) {
        settingsLink = settingsIcon.closest('a')
      }
    }
    
    if (settingsLink) {
      steps.push({
        element: settingsLink,
        popover: addButtonTexts({
          title: t('onboarding.steps.llmSetup.title'),
          description: t('onboarding.steps.llmSetup.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 4: Library Menu
  const libraryLink = document.querySelector('nav a[href="/"]')
  if (libraryLink) {
    steps.push({
      element: 'nav a[href="/"]',
      popover: addButtonTexts({
        title: t('onboarding.steps.library.title'),
        description: t('onboarding.steps.library.description'),
        position: 'right'
      })
    })
  }
  
  // Step 5: Documents Menu
  const documentsLink = document.querySelector('nav a[href="/documents"]')
  if (documentsLink) {
    steps.push({
      element: 'nav a[href="/documents"]',
      popover: addButtonTexts({
        title: t('onboarding.steps.documents.title'),
        description: t('onboarding.steps.documents.description'),
        position: 'right'
      })
    })
  }
  
  // Step 6: Upload Menu (if has permission)
  if (authStore.hasPermission('upload')) {
    const uploadLink = document.querySelector('nav a[href="/upload"]')
    if (uploadLink) {
      steps.push({
        element: 'nav a[href="/upload"]',
        popover: addButtonTexts({
          title: t('onboarding.steps.upload.title'),
          description: t('onboarding.steps.upload.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 7: Scan Menu (if has permission)
  if (authStore.hasPermission('scan')) {
    const scanLink = document.querySelector('nav a[href="/scan"]')
    if (scanLink) {
      steps.push({
        element: 'nav a[href="/scan"]',
        popover: addButtonTexts({
          title: t('onboarding.steps.scan.title'),
          description: t('onboarding.steps.scan.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 8: Folders Menu (if has permission)
  if (authStore.hasPermission('folder')) {
    const foldersLink = document.querySelector('nav a[href="/folders"]')
    if (foldersLink) {
      steps.push({
        element: 'nav a[href="/folders"]',
        popover: addButtonTexts({
          title: t('onboarding.steps.folders.title'),
          description: t('onboarding.steps.folders.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 9: Search Menu (if has permission)
  if (authStore.hasPermission('search')) {
    const searchLink = document.querySelector('nav a[href="/search"]')
    if (searchLink) {
      steps.push({
        element: 'nav a[href="/search"]',
        popover: addButtonTexts({
          title: t('onboarding.steps.search.title'),
          description: t('onboarding.steps.search.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 10: Recycle Bin Menu (if has permission)
  if (authStore.hasPermission('delete')) {
    const recycleBinLink = document.querySelector('nav a[href="/recycle-bin"]')
    if (recycleBinLink) {
      steps.push({
        element: 'nav a[href="/recycle-bin"]',
        popover: addButtonTexts({
          title: t('onboarding.steps.recycleBin.title'),
          description: t('onboarding.steps.recycleBin.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 11: Tasks Menu
  const tasksLink = document.querySelector('nav a[href="/tasks"]')
  if (tasksLink) {
    steps.push({
      element: 'nav a[href="/tasks"]',
      popover: addButtonTexts({
        title: t('onboarding.steps.tasks.title'),
        description: t('onboarding.steps.tasks.description'),
        position: 'right'
      })
    })
  }
  
  // Step 12: Chatbot Menu (if has permission)
  if (authStore.hasPermission('chat')) {
    const chatbotLink = document.querySelector('nav a[href="/chatbot"]')
    if (chatbotLink) {
      steps.push({
        element: 'nav a[href="/chatbot"]',
        popover: addButtonTexts({
          title: t('onboarding.steps.chatbot.title'),
          description: t('onboarding.steps.chatbot.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 13: Admin Section (if admin/staff)
  if (authStore.isAdmin || authStore.isStaff || authStore.hasPermission('user') || authStore.hasPermission('settings') || authStore.hasPermission('reports')) {
    const adminDivider = document.querySelector('.nav-divider')
    if (adminDivider && adminDivider.textContent?.includes(t('nav.admin'))) {
      steps.push({
        element: '.nav-divider',
        popover: addButtonTexts({
          title: t('onboarding.steps.admin.title'),
          description: t('onboarding.steps.admin.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 14: Maintainer Section (if maintainer)
  if (authStore.isMaintainer) {
    const maintainerDivider = document.querySelectorAll('.nav-divider')
    const maintainerDiv = Array.from(maintainerDivider).find(div => 
      div.textContent?.includes(t('nav.maintainer'))
    )
    if (maintainerDiv) {
      steps.push({
        element: '.nav-divider:last-of-type',
        popover: addButtonTexts({
          title: t('onboarding.steps.maintainer.title'),
          description: t('onboarding.steps.maintainer.description'),
          position: 'right'
        })
      })
    }
  }
  
  // Step 14: Finish
  const totalSteps = steps.length
  steps.push({
    element: 'body',
    popover: addButtonTexts({
      title: t('onboarding.steps.finish.title'),
      description: t('onboarding.steps.finish.description'),
      position: 'mid-center'
    }, false, true)
  })
  
  return steps
}

// Function to adjust popover position to prevent cutoff
// Simplified version - only adjusts when necessary
const adjustPopoverPosition = (isMidCenter = false) => {
  const popover = document.getElementById('driver-popover-item')
  if (!popover) return
  
  // Wait for popover to have dimensions and animation to complete
  requestAnimationFrame(() => {
    const popoverRect = popover.getBoundingClientRect()
    const popoverWidth = popoverRect.width
    const popoverHeight = popoverRect.height
    
    // Ensure popover is visible BEFORE checking dimensions
    // This is critical - popover must be visible to have valid dimensions
    if (window.getComputedStyle(popover).display === 'none' || popover.style.display === 'none') {
      popover.style.setProperty('display', 'block', 'important')
      popover.style.setProperty('visibility', 'visible', 'important')
      popover.style.setProperty('opacity', '1', 'important')
    } else {
      popover.style.display = ''
      popover.style.visibility = 'visible'
      popover.style.opacity = '1'
    }
    popover.classList.add('animation-complete')
    
    // Re-check dimensions after ensuring visibility
    const popoverRectAfter = popover.getBoundingClientRect()
    const popoverWidthAfter = popoverRectAfter.width
    const popoverHeightAfter = popoverRectAfter.height
    
    // Ensure popover has valid dimensions before adjusting
    if (popoverWidthAfter === 0 || popoverHeightAfter === 0) {
      // Retry after a short delay if popover doesn't have dimensions yet
      setTimeout(() => adjustPopoverPosition(isMidCenter), 50)
      return
    }
    
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    const margin = 20
    
    // Get computed styles to check current position
    const computedStyle = window.getComputedStyle(popover)
    const currentLeft = parseFloat(computedStyle.left) || 0
    const currentTop = parseFloat(computedStyle.top) || 0
    
    // For mid-center position, only adjust if significantly off-center or outside viewport
    if (isMidCenter) {
      const centerX = viewportWidth / 2
      const centerY = viewportHeight / 2
      
      // Calculate desired position (centered)
      let desiredLeft = centerX - (popoverWidth / 2)
      let desiredTop = centerY - (popoverHeight / 2)
      
      // Ensure popover stays within viewport bounds
      desiredLeft = Math.max(margin, Math.min(desiredLeft, viewportWidth - popoverWidth - margin))
      desiredTop = Math.max(margin, Math.min(desiredTop, viewportHeight - popoverHeight - margin))
      
      // Only reposition if significantly off-center (> 10px) or outside viewport
      const leftDiff = Math.abs(currentLeft - desiredLeft)
      const topDiff = Math.abs(currentTop - desiredTop)
      const isOutsideViewport = popoverRect.left < margin || 
                                popoverRect.right > viewportWidth - margin || 
                                popoverRect.top < margin || 
                                popoverRect.bottom > viewportHeight - margin
      
      if (leftDiff > 10 || topDiff > 10 || isOutsideViewport) {
        popover.style.position = 'fixed'
        popover.style.left = `${desiredLeft}px`
        popover.style.top = `${desiredTop}px`
        popover.style.right = 'auto'
        popover.style.bottom = 'auto'
        popover.style.margin = '0'
        popover.style.marginLeft = '0'
        popover.style.marginTop = '0'
        // Don't reset transform immediately - let animation complete first
        setTimeout(() => {
          if (popover) {
            popover.style.transform = 'none'
          }
        }, 350) // After animation completes (300ms + buffer)
      }
      return
    }
    
    // For other positions, only adjust if popover is actually cut off
    const needsAdjustment = popoverRect.right > viewportWidth - margin ||
                           popoverRect.left < margin ||
                           popoverRect.bottom > viewportHeight - margin ||
                           popoverRect.top < margin
    
    if (needsAdjustment) {
      let newLeft = currentLeft
      let newTop = currentTop
      
      // Adjust horizontal position
      if (popoverRect.right > viewportWidth - margin) {
        newLeft = viewportWidth - popoverWidth - margin
      } else if (popoverRect.left < margin) {
        newLeft = margin
      }
      
      // Adjust vertical position
      if (popoverRect.bottom > viewportHeight - margin) {
        newTop = viewportHeight - popoverHeight - margin
      } else if (popoverRect.top < margin) {
        newTop = margin
      }
      
      // Apply adjustments
      if (newLeft !== currentLeft) {
        popover.style.right = ''
        popover.style.left = `${newLeft}px`
      }
      if (newTop !== currentTop) {
        popover.style.bottom = ''
        popover.style.top = `${newTop}px`
      }
    }
  })
}

const startTour = async () => {
  // Wait a bit for DOM to be ready
  await new Promise(resolve => setTimeout(resolve, 800))
  
  const steps = buildTourSteps()
  
  if (steps.length <= 1) {
    // Only welcome step, mark as completed
    markTourCompleted()
    // Reset flag since tour won't start
    isRestartingTour = false
    return
  }
  
  driverObj = new Driver({
    animate: true,
    opacity: 0.75,
    padding: 0, // No padding - we'll handle alignment via CSS margin
    scrollIntoViewOptions: {
      behavior: 'smooth',
      block: 'center',
      inline: 'center'
    },
    allowClose: true,
    keyboardControl: true,
    overlayClickNext: false,
    stageBackground: '#ffffff',
    onReset: () => {
      // User clicked close/skip or tour ended
      const currentIndex = driverObj?.getActiveIndex?.() ?? -1
      const totalSteps = driverObj?.getSteps?.()?.length ?? 0
      const wasCompleted = currentIndex >= totalSteps - 1
      const timeSinceStart = Date.now() - tourStartTime
      // Check if this is an immediate reset: happened within 2 seconds of start and tour hasn't progressed past first step
      // Don't rely on tourJustStarted flag as it may have been reset
      const isImmediateReset = timeSinceStart < 2000 && currentIndex === -1 && !wasCompleted
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:451',message:'onReset called',data:{isRestartingTour,currentIndex,totalSteps,wasCompleted,hasCompleted:authStore.has_completed_onboarding,userHasCompleted:authStore.user?.has_completed_onboarding,isImmediateReset},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      cleanupResizeHandlers()
      
      // Cleanup document-level close button interceptor
      if (window._tourCloseInterceptor) {
        document.removeEventListener('click', window._tourCloseInterceptor, { capture: true })
        document.removeEventListener('mousedown', window._tourCloseInterceptor, { capture: true })
        window._tourCloseInterceptor = null
      }
      
      // Cleanup overlay click handler
      if (window._tourOverlayHandler) {
        const overlay = document.getElementById('driver-page-overlay')
        if (overlay) {
          overlay.removeEventListener('click', window._tourOverlayHandler, { capture: true })
        }
        window._tourOverlayHandler = null
      }
      
      // If tour was just started and reset immediately (likely Driver.js error), prevent restart loop
      if (isImmediateReset) {
        driverObj = null
        tourJustStarted = false
        isRestartingTour = false
        // Mark as completed to prevent automatic restart
        // BUT: Only if not already marked (e.g., by close button handler)
        // Use a small delay to check if store was updated by close button handler
        setTimeout(() => {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:480',message:'Checking has_completed_onboarding after delay',data:{hasCompleted:authStore.has_completed_onboarding,userHasCompleted:authStore.user?.has_completed_onboarding},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
          // #endregion
          if (!authStore.has_completed_onboarding) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:483',message:'Calling markTourCompleted from setTimeout',data:{hasCompleted:authStore.has_completed_onboarding},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
            // #endregion
            markTourCompleted()
          } else {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:487',message:'Already marked completed, skipping markTourCompleted',data:{hasCompleted:authStore.has_completed_onboarding},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
            // #endregion
          }
        }, 50)
        return
      }
      
      // Only mark as completed if tour actually finished (not if it was reset during restart)
      // Check if we're not in the middle of restarting and tour actually completed
      if (!isRestartingTour) {
        // Check if tour was actually completed (reached the end) vs just closed early
        // Only mark completed if tour reached the end, otherwise user just closed it early
        // BUT: If has_completed_onboarding is already true (from close button handler), don't call markTourCompleted again
        if (wasCompleted) {
          markTourCompleted()
        } else if (authStore.has_completed_onboarding) {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:485',message:'Tour closed early but already marked completed',data:{hasCompleted:authStore.has_completed_onboarding,userHasCompleted:authStore.user?.has_completed_onboarding},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
          // #endregion
        } else {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:490',message:'Tour closed early, NOT marking completed',data:{wasCompleted,currentIndex,totalSteps},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
          // #endregion
        }
      }
      
      driverObj = null
      // Reset flags
      isRestartingTour = false
      tourJustStarted = false
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:495',message:'onReset finished',data:{hasCompleted:authStore.has_completed_onboarding,userHasCompleted:authStore.user?.has_completed_onboarding},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
    },
    onNext: (element) => {
      const currentIndex = driverObj?.getActiveIndex?.() ?? -1
      const hasNext = driverObj?.hasNextStep?.() ?? false
      const totalSteps = driverObj?.getSteps?.()?.length ?? 0
      // Mark next click time for transition detection
      lastNextClickTime = Date.now()
      // If no next step, mark as completed and close tour (tour finished)
      if (driverObj && !hasNext) {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:525',message:'Tour finished, marking completed and closing',data:{currentIndex,totalSteps,hasNext},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        markTourCompleted().then(() => {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:531',message:'markTourCompleted resolved, closing tour',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
          // #endregion
          forceCloseTour()
        }).catch((error) => {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:535',message:'markTourCompleted failed, still closing tour',data:{error:String(error)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
          // #endregion
          // Still try to close even if marking failed
          forceCloseTour()
        })
      }
    },
    onHighlighted: (element) => {
      const currentIndex = driverObj?.getActiveIndex?.() ?? -1
      const totalSteps = driverObj?.getSteps?.()?.length ?? 0
      const nextStepExists = driverObj?.hasNextStep?.() ?? false
      const currentStep = driverObj?.getSteps?.()?.[currentIndex]
      const isMidCenter = currentStep?.popover?.position === 'mid-center'
      const popover = document.getElementById('driver-popover-item')
      const popoverDisplay = popover ? window.getComputedStyle(popover).display : 'none'
      const overlayAtStart = document.getElementById('driver-page-overlay')
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:559',message:'onHighlighted called',data:{currentIndex,totalSteps,overlayExists:!!overlayAtStart,popoverExists:!!popover},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
      // #endregion
      
      // Add overlay click listener to close tour when clicking outside
      // Use a global handler to avoid duplicate listeners
      setTimeout(() => {
        const overlay = document.getElementById('driver-page-overlay')
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:571',message:'Checking for overlay in onHighlighted',data:{overlayExists:!!overlay,currentIndex,hasHandler:!!window._tourOverlayHandler},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
        // #endregion
        if (overlay) {
          // Create global handler if not exists
          if (!window._tourOverlayHandler) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:574',message:'Creating new overlay handler',data:{currentIndex},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
            // #endregion
            window._tourOverlayHandler = (e) => {
              const target = e.target
              const overlayElement = document.getElementById('driver-page-overlay')
              if (!overlayElement) {
                // #region agent log
                fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:578',message:'Overlay handler: overlay element not found',data:{targetTag:target?.tagName,targetId:target?.id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
                // #endregion
                return
              }
              
              // Check if clicking on overlay itself (not on children like popover or highlighted element)
              const isOverlay = target === overlayElement || target.id === 'driver-page-overlay'
              const isPopover = target.closest('#driver-popover-item')
              const isHighlighted = target.closest('#driver-highlighted-element-stage')
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:585',message:'Overlay click detected',data:{isOverlay,targetTag:target?.tagName,targetId:target?.id,isPopover:!!isPopover,isHighlighted:!!isHighlighted,overlayId:overlayElement.id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
              // #endregion
              // Only close if clicking directly on overlay (not on popover or highlighted element)
              if (isOverlay && !isPopover && !isHighlighted) {
                // #region agent log
                fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:590',message:'Overlay clicked, closing tour',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
                // #endregion
                e.preventDefault()
                e.stopPropagation()
                e.stopImmediatePropagation()
                // Mark as completed first, then force close
                markTourCompleted().then(() => {
                  forceCloseTour()
                }).catch((error) => {
                  // Still try to close even if marking failed
                  forceCloseTour()
                })
                return false
              } else {
                // #region agent log
                fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:603',message:'Overlay click ignored - not valid overlay click',data:{isOverlay,isPopover:!!isPopover,isHighlighted:!!isHighlighted,targetTag:target?.tagName,targetId:target?.id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
                // #endregion
              }
            }
          }
          
          // Remove old listener if exists, then add new one (to handle overlay recreation)
          overlay.removeEventListener('click', window._tourOverlayHandler, { capture: true })
          overlay.addEventListener('click', window._tourOverlayHandler, { capture: true, passive: false })
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:609',message:'Overlay listener attached',data:{currentIndex,overlayId:overlay.id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
          // #endregion
        } else {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:612',message:'Overlay not found in setTimeout',data:{currentIndex},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
          // #endregion
        }
      }, 100)
      
      // Setup close button listener for this step (Driver.js recreates buttons on each step)
      // Reset listener flag when step changes to allow re-attachment
      setTimeout(() => {
        const closeBtn = document.querySelector('.driver-close-btn')
        if (closeBtn) {
          // Reset flag to allow re-attachment (Driver.js may recreate button)
          delete closeBtn.dataset.listenerAttached
        }
        setupCloseButtonListener()
      }, 100)
      setTimeout(() => {
        const closeBtn = document.querySelector('.driver-close-btn')
        if (closeBtn) {
          delete closeBtn.dataset.listenerAttached
        }
        setupCloseButtonListener()
        const overlay = document.getElementById('driver-page-overlay')
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:655',message:'Checking overlay at 300ms',data:{overlayExists:!!overlay,currentIndex,hasHandler:!!window._tourOverlayHandler},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
        // #endregion
        if (overlay && window._tourOverlayHandler) {
          overlay.removeEventListener('click', window._tourOverlayHandler, { capture: true })
          overlay.addEventListener('click', window._tourOverlayHandler, { capture: true, passive: false })
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:662',message:'Overlay listener re-attached at 300ms',data:{currentIndex},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
          // #endregion
        }
      }, 300)
      setTimeout(() => {
        const closeBtn = document.querySelector('.driver-close-btn')
        if (closeBtn) {
          delete closeBtn.dataset.listenerAttached
        }
        setupCloseButtonListener()
        const overlay = document.getElementById('driver-page-overlay')
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:670',message:'Checking overlay at 500ms',data:{overlayExists:!!overlay,currentIndex,hasHandler:!!window._tourOverlayHandler},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
        // #endregion
        if (overlay && window._tourOverlayHandler) {
          overlay.removeEventListener('click', window._tourOverlayHandler, { capture: true })
          overlay.addEventListener('click', window._tourOverlayHandler, { capture: true, passive: false })
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:677',message:'Overlay listener re-attached at 500ms',data:{currentIndex},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'J'})}).catch(()=>{});
          // #endregion
        }
      }, 500)
      
      // Fix highlight box alignment
      setTimeout(() => {
        const highlightedElement = element?.node
        const highlightStage = document.getElementById('driver-highlighted-element-stage')
        
        if (highlightedElement && highlightStage) {
          const elementRect = highlightedElement.getBoundingClientRect()
          const stageRect = highlightStage.getBoundingClientRect()
          
          // Calculate correct position and size
          // Stage should match element exactly, with border inside
          const correctLeft = elementRect.left
          const correctTop = elementRect.top
          const correctWidth = elementRect.width
          const correctHeight = elementRect.height
          
          // Check if stage position/size is incorrect
          const leftDiff = Math.abs(stageRect.left - correctLeft)
          const topDiff = Math.abs(stageRect.top - correctTop)
          const widthDiff = Math.abs(stageRect.width - correctWidth)
          const heightDiff = Math.abs(stageRect.height - correctHeight)
          
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:505',message:'Highlight box alignment check',data:{currentIndex,elementTag:highlightedElement.tagName,elementClass:highlightedElement.className,elementRect:{left:elementRect.left,top:elementRect.top,width:elementRect.width,height:elementRect.height},stageRect:{left:stageRect.left,top:stageRect.top,width:stageRect.width,height:stageRect.height},leftDiff,topDiff,widthDiff,heightDiff,needsFix:leftDiff>1||topDiff>1||widthDiff>1||heightDiff>1},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'I'})}).catch(()=>{});
          // #endregion
          
          // Fix alignment if needed (tolerance of 1px for subpixel rendering)
          if (leftDiff > 1 || topDiff > 1 || widthDiff > 1 || heightDiff > 1) {
            // Force correct position and size
            highlightStage.style.left = `${correctLeft}px`
            highlightStage.style.top = `${correctTop}px`
            highlightStage.style.width = `${correctWidth}px`
            highlightStage.style.height = `${correctHeight}px`
            
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:530',message:'Fixed highlight box alignment',data:{correctLeft,correctTop,correctWidth,correctHeight,oldLeft:stageRect.left,oldTop:stageRect.top,oldWidth:stageRect.width,oldHeight:stageRect.height},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'I'})}).catch(()=>{});
            // #endregion
          }
        }
      }, 100)
      
      // Immediately add force-visible class to ensure popover stays visible
      // This class has !important in CSS and will persist even if Driver.js removes inline styles
      if (popover) {
        popover.classList.add('force-visible')
      }
      
      // Wait for Driver.js to create popover and animation to complete before adjusting
      // Animation duration is 300ms, so wait 350ms to ensure it's complete
      setTimeout(() => {
        const popover = document.getElementById('driver-popover-item')
        if (popover) {
          // Ensure class is still present (Driver.js might remove it)
          popover.classList.add('force-visible')
          
          const computedStyle = window.getComputedStyle(popover)
          const rect = popover.getBoundingClientRect()
          // Ensure popover is visible - use CSS class with !important to override any Driver.js styles
          if (computedStyle.display === 'none' || popover.style.display === 'none') {
            popover.classList.add('force-visible')
            popover.style.setProperty('display', 'block', 'important')
            popover.style.setProperty('visibility', 'visible', 'important')
            popover.style.setProperty('opacity', '1', 'important')
          } else {
            popover.style.display = ''
            popover.style.visibility = 'visible'
            popover.style.opacity = '1'
          }
          
          // Check again after setting styles and ensure class persists
          setTimeout(() => {
            const popover = document.getElementById('driver-popover-item')
            if (!popover) return
            
            // Re-add class in case Driver.js removed it
            popover.classList.add('force-visible')
            
            const computedStyle2 = window.getComputedStyle(popover)
            const rect2 = popover.getBoundingClientRect()
            // If still hidden, force visible again with class
            if (computedStyle2.display === 'none' || popover.style.display === 'none') {
              popover.classList.add('force-visible')
              popover.style.setProperty('display', 'block', 'important')
              popover.style.setProperty('visibility', 'visible', 'important')
              popover.style.setProperty('opacity', '1', 'important')
            }
          }, 50)
          
          // Adjust position once after animation completes and popover has dimensions
          adjustPopoverPosition(isMidCenter)
        }
      }, 350) // Wait for animation to complete (300ms) + small buffer
      // Hide Previous button if it has no text or shows default "Previous" (for first step)
      setTimeout(() => {
        const prevBtn = document.querySelector('.driver-prev-btn')
        if (prevBtn) {
          const btnText = prevBtn.textContent?.trim() || ''
          const innerHTML = prevBtn.innerHTML?.trim() || ''
          // Hide if empty, undefined, or shows default English "Previous" text
          if (!btnText || btnText === '' || btnText === 'undefined' || btnText === 'Previous' || btnText === '← Previous' || innerHTML.includes('Previous')) {
            prevBtn.style.display = 'none'
          } else {
            // Ensure button is visible and update text if needed
            prevBtn.style.display = ''
            // Check if button text needs to be updated with translation
            const expectedText = t('onboarding.previous')
            if (btnText !== expectedText && !innerHTML.includes(expectedText)) {
              // Update button text with translation
              prevBtn.textContent = expectedText
            }
          }
        }
      }, 100)
      
      // Ensure element is scrolled into view, especially for sidebar items
      if (element && element.node) {
        const node = element.node
        // Check if element is in sidebar
        const sidebar = document.querySelector('.sidebar')
        if (sidebar && sidebar.contains(node)) {
          // Scroll sidebar container to show the element
          // Use requestAnimationFrame for better performance and to ensure DOM is ready
          requestAnimationFrame(() => {
            // Get element position relative to sidebar
            const sidebarRect = sidebar.getBoundingClientRect()
            const elementRect = node.getBoundingClientRect()
            const sidebarHeight = sidebar.clientHeight
            const elementHeight = node.offsetHeight || elementRect.height
            
            // Calculate if element is visible in sidebar viewport
            const elementTopRelativeToSidebar = elementRect.top - sidebarRect.top + sidebar.scrollTop
            const elementBottomRelativeToSidebar = elementTopRelativeToSidebar + elementHeight
            
            // Calculate desired scroll position (center the element with padding)
            const padding = 40 // Padding from top/bottom
            const desiredScrollTop = elementTopRelativeToSidebar - (sidebarHeight / 2) + (elementHeight / 2)
            
            // Smooth scroll sidebar
            sidebar.scrollTo({
              top: Math.max(0, Math.min(desiredScrollTop, sidebar.scrollHeight - sidebarHeight)),
              behavior: 'smooth'
            })
            
            // Double check after scroll completes - ensure element is visible
            setTimeout(() => {
              const rect = node.getBoundingClientRect()
              const sidebarRect2 = sidebar.getBoundingClientRect()
              const isVisible = rect.top >= sidebarRect2.top + padding && rect.bottom <= sidebarRect2.bottom - padding
              
              if (!isVisible) {
                // If element is above visible area
                if (rect.top < sidebarRect2.top + padding) {
                  const currentScroll = sidebar.scrollTop
                  const elementTopRelative = rect.top - sidebarRect2.top + currentScroll
                  const targetScroll = elementTopRelative - padding
                  sidebar.scrollTo({
                    top: Math.max(0, targetScroll),
                    behavior: 'smooth'
                  })
                }
                // If element is below visible area
                else if (rect.bottom > sidebarRect2.bottom - padding) {
                  const currentScroll = sidebar.scrollTop
                  const elementBottomRelative = rect.bottom - sidebarRect2.bottom + currentScroll
                  const targetScroll = elementBottomRelative - sidebarHeight + padding
                  sidebar.scrollTo({
                    top: Math.max(0, Math.min(targetScroll, sidebar.scrollHeight - sidebarHeight)),
                    behavior: 'smooth'
                  })
                }
              }
              
              // After sidebar scroll, adjust popover position after animation completes
              setTimeout(() => {
                const currentStepIdx = driverObj?.getActiveIndex?.() ?? -1
                const step = driverObj?.getSteps?.()?.[currentStepIdx]
                const isMidCenter = step?.popover?.position === 'mid-center'
                adjustPopoverPosition(isMidCenter)
              }, 350) // Wait for animation to complete
            }, 500)
          })
        } else {
          // For main content, ensure it's visible in viewport
          requestAnimationFrame(() => {
            node.scrollIntoView({
              behavior: 'smooth',
              block: 'center',
              inline: 'center'
            })
            setTimeout(() => {
              const currentStepIdx = driverObj?.getActiveIndex?.() ?? -1
              const step = driverObj?.getSteps?.()?.[currentStepIdx]
              const isMidCenter = step?.popover?.position === 'mid-center'
              adjustPopoverPosition(isMidCenter)
            }, 350) // Wait for animation to complete
          })
        }
      }
    }
  })
  
  driverObj.defineSteps(steps)
  
  // Mark tour as just started to prevent immediate reset loop
  tourJustStarted = true
  tourStartTime = Date.now()
  
  driverObj.start()
  
  // Monitor popover for display changes using MutationObserver
  // Only force visible during initial step, not during step transitions
  setTimeout(() => {
    const popover = document.getElementById('driver-popover-item')
    if (popover) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
            const currentIndex = driverObj?.getActiveIndex?.() ?? -1
            const computedStyle = window.getComputedStyle(popover)
            const rect = popover.getBoundingClientRect()
            const timeSinceNextClick = Date.now() - lastNextClickTime
            // Consider transitioning if next was clicked within last 2 seconds
            const isTransitioning = timeSinceNextClick < 2000
            
            // Only force visible if NOT transitioning and popover is hidden
            // During transitions, Driver.js may temporarily hide popover to reposition
            if (!isTransitioning && (computedStyle.display === 'none' || popover.style.display === 'none')) {
              // Add class first (persists even if Driver.js removes inline styles)
              popover.classList.add('force-visible')
              popover.style.display = 'block'
              popover.style.visibility = 'visible'
              popover.style.opacity = '1'
            } else if (isTransitioning && (computedStyle.display === 'none' || popover.style.display === 'none')) {
              // After transition completes (2 seconds), check if popover is still hidden and force visible
              setTimeout(() => {
                const popoverAfterTransition = document.getElementById('driver-popover-item')
                if (popoverAfterTransition) {
                  const computedStyleAfter = window.getComputedStyle(popoverAfterTransition)
                  if (computedStyleAfter.display === 'none' || popoverAfterTransition.style.display === 'none') {
                    // Use CSS class with !important to force visible
                    // Add class first - it persists even if Driver.js removes inline styles
                    popoverAfterTransition.classList.add('force-visible')
                    popoverAfterTransition.style.setProperty('display', 'block', 'important')
                    popoverAfterTransition.style.setProperty('visibility', 'visible', 'important')
                    popoverAfterTransition.style.setProperty('opacity', '1', 'important')
                    // Verify it's visible after setting
                    setTimeout(() => {
                      const popoverCheck = document.getElementById('driver-popover-item')
                      if (!popoverCheck) return
                      
                      // Re-add class in case Driver.js removed it
                      popoverCheck.classList.add('force-visible')
                      
                      const computedStyleAfterSet = window.getComputedStyle(popoverCheck)
                      const rectAfterSet = popoverCheck.getBoundingClientRect()
                      // If still hidden, ensure class is applied and use !important
                      if (computedStyleAfterSet.display === 'none' || popoverCheck.style.display === 'none') {
                        popoverCheck.classList.add('force-visible')
                        popoverCheck.style.setProperty('display', 'block', 'important')
                        popoverCheck.style.setProperty('visibility', 'visible', 'important')
                        popoverCheck.style.setProperty('opacity', '1', 'important')
                      }
                    }, 100)
                  }
                }
              }, 2100) // Slightly longer than transition detection window
            }
          }
        })
      })
      observer.observe(popover, {
        attributes: true,
        attributeFilter: ['style'],
        attributeOldValue: true
      })
      // Store observer to disconnect later
      if (!window._tourPopoverObserver) {
        window._tourPopoverObserver = observer
      }
      
    }
  }, 100)
  
  // Check again after animation should complete
  // Setup event listener for close button - use MutationObserver to catch when button is created
  const setupCloseButtonListener = () => {
    const closeBtn = document.querySelector('.driver-close-btn')
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:869',message:'setupCloseButtonListener called',data:{closeBtnExists:!!closeBtn,hasListenerAttached:closeBtn?.dataset?.listenerAttached,hasDriverObj:!!driverObj,currentIndex:driverObj?.getActiveIndex?.() ?? -1},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
    // #endregion
    if (closeBtn) {
      // Check if listeners already attached to avoid duplicates
      if (closeBtn.dataset.listenerAttached === 'true') {
        // Listeners already attached, skip
        return
      }
      
      closeBtn.dataset.listenerAttached = 'true'
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:891',message:'Attaching listeners to close button',data:{closeBtnText:closeBtn.textContent,closeBtnZIndex:window.getComputedStyle(closeBtn).zIndex,pointerEvents:window.getComputedStyle(closeBtn).pointerEvents},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
      // #endregion
      // Ensure button is clickable - force all necessary styles
      closeBtn.style.setProperty('pointer-events', 'auto', 'important')
      closeBtn.style.setProperty('z-index', '1000000003', 'important')
      closeBtn.style.setProperty('position', 'relative', 'important')
      closeBtn.style.setProperty('cursor', 'pointer', 'important')
      
      // Ensure popover and all its children are clickable
      const popover = document.getElementById('driver-popover-item')
      if (popover) {
        popover.style.setProperty('pointer-events', 'auto', 'important')
        // Make all buttons in popover clickable
        const allButtons = popover.querySelectorAll('button')
        allButtons.forEach(btn => {
          btn.style.setProperty('pointer-events', 'auto', 'important')
          btn.style.setProperty('z-index', '1000000003', 'important')
        })
      }
      
      // Add click listener directly to button with highest priority
      const clickHandler = (e) => {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:859',message:'Close button clicked via clickHandler',data:{hasDriverObj:!!driverObj,eventType:e.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
        // #endregion
        e.preventDefault()
        e.stopImmediatePropagation()
        // Mark as completed first, then force close
        markTourCompleted().then(() => {
          forceCloseTour()
        }).catch((error) => {
          // Still try to close even if marking failed
          forceCloseTour()
        })
        return false
      }
      
      // Add listeners with highest priority (capture phase first)
      closeBtn.addEventListener('click', clickHandler, { capture: true, passive: false })
      closeBtn.addEventListener('mousedown', (e) => {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:878',message:'Close button mousedown triggered',data:{closeBtnText:closeBtn.textContent,closeBtnZIndex:window.getComputedStyle(closeBtn).zIndex,pointerEvents:window.getComputedStyle(closeBtn).pointerEvents},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
        // #endregion
        e.preventDefault()
        e.stopImmediatePropagation()
        // Mark as completed first, then force close
        markTourCompleted().then(() => {
          forceCloseTour()
        }).catch((error) => {
          // Still try to close even if marking failed
          forceCloseTour()
        })
        return false
      }, { capture: true, passive: false })
      
      // Also add to parent footer in case button is recreated
      const footer = closeBtn.closest('.driver-popover-footer')
      if (footer && !footer.dataset.listenerAttached) {
        footer.dataset.listenerAttached = 'true'
        footer.addEventListener('click', (e) => {
          if (e.target.classList.contains('driver-close-btn') || e.target.closest('.driver-close-btn')) {
            e.preventDefault()
            e.stopImmediatePropagation()
            // Mark as completed first, then force close
            markTourCompleted().then(() => {
              forceCloseTour()
            }).catch((error) => {
              // Still try to close even if marking failed
              forceCloseTour()
            })
            return false
          }
        }, { capture: true, passive: false })
      }
      
      // Also intercept at document level as last resort
      if (!window._tourCloseInterceptor) {
        window._tourCloseInterceptor = (e) => {
          const target = e.target
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:860',message:'Document click intercepted',data:{targetTag:target?.tagName,targetClass:target?.className,isCloseBtn:target?.classList?.contains('driver-close-btn'),hasClosestCloseBtn:!!target?.closest('.driver-close-btn'),eventType:e.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
          // #endregion
          if (target && (target.classList.contains('driver-close-btn') || target.closest('.driver-close-btn'))) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:863',message:'Close button detected in document interceptor',data:{hasDriverObj:!!driverObj,driverObjType:typeof driverObj},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
            // #endregion
            e.preventDefault()
            e.stopImmediatePropagation()
            
            // Try multiple methods to close tour
            // Method 1: Use driverObj if available
            if (driverObj && typeof driverObj.reset === 'function') {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:870',message:'Closing via driverObj.reset',data:{hasDriverObj:true},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
              // #endregion
              // CRITICAL: Save driverObj reference BEFORE markTourCompleted (which may trigger onReset and null it)
              const driverInstance = driverObj
              // Mark as completed first, then force close
            markTourCompleted().then(() => {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:937',message:'markTourCompleted resolved, calling forceCloseTour',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
              // #endregion
              forceCloseTour()
            }).catch((error) => {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:941',message:'markTourCompleted failed, still calling forceCloseTour',data:{error:String(error)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
              // #endregion
              // Still try to close even if marking failed
              forceCloseTour()
            })
            } else {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:875',message:'Force closing by removing DOM',data:{hasDriverObj:false,overlayExists:!!document.getElementById('driver-page-overlay'),popoverExists:!!document.getElementById('driver-popover-item'),stageExists:!!document.getElementById('driver-highlighted-element-stage')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
              // #endregion
              // Method 2: Force close by removing Driver.js DOM elements
              const overlay = document.getElementById('driver-page-overlay')
              const popover = document.getElementById('driver-popover-item')
              const highlightedStage = document.getElementById('driver-highlighted-element-stage')
              
              if (overlay) overlay.remove()
              if (popover) popover.remove()
              if (highlightedStage) highlightedStage.remove()
              
              // Remove all driver-related classes
              document.body.classList.remove('driver-active', 'driver-block-scroll')
              
              // Reset driverObj
              driverObj = null
              
              // Mark tour as completed to prevent auto-restart
              markTourCompleted()
              
              // Cleanup resize handlers
              cleanupResizeHandlers()
            }
            return false
          }
        }
        document.addEventListener('click', window._tourCloseInterceptor, { capture: true, passive: false })
        document.addEventListener('mousedown', window._tourCloseInterceptor, { capture: true, passive: false })
      }
    }
  }
  
  // Try immediately
  setupCloseButtonListener()
  
  // Also try after delays to catch button when it's created
  setTimeout(setupCloseButtonListener, 100)
  setTimeout(setupCloseButtonListener, 500)
  setTimeout(setupCloseButtonListener, 1000)
  setTimeout(setupCloseButtonListener, 2000)
  
  // Use MutationObserver to watch for button creation
  let popoverObserver = null
  setTimeout(() => {
    const popover = document.getElementById('driver-popover-item')
    if (popover) {
      popoverObserver = new MutationObserver(() => {
        setupCloseButtonListener()
      })
      popoverObserver.observe(popover, {
        childList: true,
        subtree: true
      })
    }
  }, 100)
  
  setTimeout(() => {
    const popover = document.getElementById('driver-popover-item')
    if (popover) {
      const computedStyle = window.getComputedStyle(popover)
      const rect = popover.getBoundingClientRect()
      // Force visible if hidden
      if (computedStyle.display === 'none' || popover.style.display === 'none') {
        popover.style.display = 'block'
        popover.style.visibility = 'visible'
        popover.style.opacity = '1'
      }
    }
  }, 500)
  
  // Reset restart flag after tour successfully starts
  // Don't reset tourJustStarted here - let onReset handle it or reset after successful start
  setTimeout(() => {
    isRestartingTour = false
    // tourJustStarted will be reset in onReset if immediate reset, or after successful start (2 seconds)
    setTimeout(() => {
      // Only reset if tour is still running (not reset)
      if (driverObj && tourJustStarted) {
        tourJustStarted = false
      }
    }, 2000) // 2 second grace period - if tour still running, it's successful
  }, 100)
  
  // Setup global resize handler (only once per tour)
  cleanupResizeHandlers()
  setupResizeHandlers()
}

// Setup resize handlers to maintain popover position
const setupResizeHandlers = () => {
  // Reset viewport tracking
  lastViewportWidth = window.innerWidth
  lastViewportHeight = window.innerHeight
  
  globalResizeHandler = () => {
    clearTimeout(globalResizeTimeout)
    globalResizeTimeout = setTimeout(() => {
      const popover = document.getElementById('driver-popover-item')
      if (popover && driverObj) {
        const currentViewportWidth = window.innerWidth
        const currentViewportHeight = window.innerHeight
        const viewportChanged = currentViewportWidth !== lastViewportWidth || currentViewportHeight !== lastViewportHeight
        
        if (viewportChanged) {
          lastViewportWidth = currentViewportWidth
          lastViewportHeight = currentViewportHeight
          
          const currentStepIdx = driverObj.getActiveIndex?.() ?? -1
          const step = driverObj.getSteps?.()?.[currentStepIdx]
          const isMidCenter = step?.popover?.position === 'mid-center'
          
          // Ensure popover is visible
          popover.style.display = ''
          popover.style.visibility = 'visible'
          popover.style.opacity = '1'
          
          // Adjust position after a short delay to ensure DOM is ready
          setTimeout(() => {
            adjustPopoverPosition(isMidCenter)
          }, 100)
        }
      }
    }, 150)
  }
  
  window.addEventListener('resize', globalResizeHandler)
  window.addEventListener('orientationchange', globalResizeHandler)
  
  // Monitor for DevTools open/close by checking viewport periodically
  globalViewportCheckInterval = setInterval(() => {
    const currentWidth = window.innerWidth
    const currentHeight = window.innerHeight
    if (currentWidth !== lastViewportWidth || currentHeight !== lastViewportHeight) {
      if (globalResizeHandler) {
        globalResizeHandler()
      }
    }
  }, 500)
}

// Cleanup resize handlers
const cleanupResizeHandlers = () => {
  if (globalResizeHandler) {
    window.removeEventListener('resize', globalResizeHandler)
    window.removeEventListener('orientationchange', globalResizeHandler)
    globalResizeHandler = null
  }
  if (globalResizeTimeout) {
    clearTimeout(globalResizeTimeout)
    globalResizeTimeout = null
  }
  if (globalViewportCheckInterval) {
    clearInterval(globalViewportCheckInterval)
    globalViewportCheckInterval = null
  }
}

const markTourCompleted = async () => {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:1057',message:'markTourCompleted called',data:{isRestartingTour,currentHasCompleted:authStore.has_completed_onboarding,userHasCompleted:authStore.user?.has_completed_onboarding},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
  // #endregion
  try {
    await authStore.completeOnboarding()
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:1062',message:'markTourCompleted finished',data:{hasCompleted:authStore.has_completed_onboarding,userHasCompleted:authStore.user?.has_completed_onboarding},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
  } catch (error) {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:1065',message:'markTourCompleted error',data:{error:String(error)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
    console.error('Failed to mark onboarding as completed', error)
  }
}

// Force close tour by removing DOM elements and cleaning up
const forceCloseTour = () => {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:1111',message:'forceCloseTour called',data:{hasDriverObj:!!driverObj,overlayExists:!!document.getElementById('driver-page-overlay'),popoverExists:!!document.getElementById('driver-popover-item'),stageExists:!!document.getElementById('driver-highlighted-element-stage')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
  // #endregion

  // Method 1: Try driverObj.reset first if available
  if (driverObj && typeof driverObj.reset === 'function') {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:1115',message:'Using driverObj.reset',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
    // #endregion
    driverObj.reset(true)
    driverObj = null
  } else {
    // Method 2: Force close by removing Driver.js DOM elements
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:1120',message:'Force removing DOM elements',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
    // #endregion
    const overlay = document.getElementById('driver-page-overlay')
    const popover = document.getElementById('driver-popover-item')
    const highlightedStage = document.getElementById('driver-highlighted-element-stage')

    if (overlay) overlay.remove()
    if (popover) popover.remove()
    if (highlightedStage) highlightedStage.remove()

    // Remove all driver-related classes
    document.body.classList.remove('driver-active', 'driver-block-scroll')

    // Reset driverObj
    driverObj = null
  }

  // Cleanup resize handlers
  cleanupResizeHandlers()

  // Reset flags
  isRestartingTour = false
  tourJustStarted = false

  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/6006ef1e-a69d-4b1d-b684-212f0849099c',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'OnboardingTour.vue:1140',message:'forceCloseTour completed',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H'})}).catch(()=>{});
  // #endregion
}

// Export function to restart tour manually
const restartTour = async () => {
  // Set flag to prevent watchers and other logic from interfering
  isRestartingTour = true
  tourJustStarted = false // Reset this flag when manually restarting
  
  // Reset driver if exists
  if (driverObj) {
    driverObj.reset(true)
    driverObj = null
  }
  cleanupResizeHandlers()
  
  // Set both store property and user property to false to allow tour to start
  authStore.has_completed_onboarding = false
  if (authStore.user) {
    authStore.user.has_completed_onboarding = false
  }
  
  // Wait a bit then start tour (increased delay to ensure DOM is ready)
  setTimeout(() => {
    startTour()
    // Reset flag after tour starts (will be set to false in startTour after successful start)
  }, 500)
}

// Expose restartTour function globally or via provide
defineExpose({
  restartTour
})

const checkAndStartTour = () => {
  // Don't start tour if we're manually restarting it
  if (isRestartingTour) {
    return
  }

  // Don't start tour if it just started and was reset (prevent restart loop)
  if (tourJustStarted) {
    return
  }

  // Only start tour if user is authenticated and hasn't completed onboarding
  // Check both store property and user property
  if (authStore.isAuthenticated && authStore.user && !authStore.has_completed_onboarding) {
    // Double check the user object has the property
    if (!authStore.user.has_completed_onboarding) {
      startTour()
    }
  }
}

// Watch for user changes
watch(() => authStore.user, (newUser) => {
  // Don't interfere if we're manually restarting the tour
  if (isRestartingTour) {
    return
  }

  if (newUser && !authStore.has_completed_onboarding) {
    checkAndStartTour()
  }
}, { immediate: false })

// Watch for locale changes to restart tour with new translations
watch(locale, () => {
  if (driverObj) {
    driverObj.reset(true)
    driverObj = null
    setTimeout(() => {
      checkAndStartTour()
    }, 100)
  }
})

onMounted(() => {
  // Wait for user data to be loaded
  if (authStore.user && authStore.isAuthenticated) {
    checkAndStartTour()
  } else {
    // Wait a bit more if user data is still loading
    setTimeout(() => {
      checkAndStartTour()
    }, 1500)
  }
})

onUnmounted(() => {
  if (driverObj) {
    driverObj.reset(true)
    driverObj = null
  }
  cleanupResizeHandlers()
})
</script>

<style scoped>
/* Driver.js custom styles are in driver-custom.css */
</style>


/**
 * RISKCAST Premium Animation System
 * Powered by Framer Motion
 *
 * Design Philosophy: Bloomberg Terminal meets Linear smoothness
 * - Data-dense, purposeful animations
 * - Spring physics for natural feel
 * - 60fps performance target
 * - Reduced motion support
 */

import { type Variants, type Transition, type Spring } from 'framer-motion';

// ============================================
// SPRING CONFIGURATIONS
// ============================================

export const springs = {
  // Snappy - for buttons, toggles
  snappy: { type: 'spring', stiffness: 400, damping: 30 } as Spring,

  // Smooth - for cards, modals
  smooth: { type: 'spring', stiffness: 300, damping: 30 } as Spring,

  // Gentle - for page transitions
  gentle: { type: 'spring', stiffness: 200, damping: 25 } as Spring,

  // Bouncy - for success states
  bouncy: { type: 'spring', stiffness: 500, damping: 15 } as Spring,

  // Stiff - for micro-interactions
  stiff: { type: 'spring', stiffness: 600, damping: 40 } as Spring,
} as const;

// ============================================
// TIMING CONFIGURATIONS
// ============================================

export const durations = {
  instant: 0.1,
  fast: 0.15,
  normal: 0.2,
  slow: 0.3,
  slower: 0.5,
  slowest: 0.8,
} as const;

export const easings = {
  // Premium easing curves
  easeOut: [0.16, 1, 0.3, 1],
  easeIn: [0.4, 0, 1, 1],
  easeInOut: [0.4, 0, 0.2, 1],

  // Sharp for data updates
  sharp: [0.4, 0, 0.6, 1],

  // Smooth for UI elements
  smooth: [0.25, 0.1, 0.25, 1],
} as const;

// ============================================
// FADE VARIANTS
// ============================================

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: durations.normal, ease: easings.easeOut },
  },
  exit: {
    opacity: 0,
    transition: { duration: durations.fast, ease: easings.easeIn },
  },
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: durations.normal, ease: easings.easeOut },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: durations.fast, ease: easings.easeIn },
  },
};

export const fadeInDown: Variants = {
  hidden: { opacity: 0, y: -10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: durations.normal, ease: easings.easeOut },
  },
  exit: {
    opacity: 0,
    y: 10,
    transition: { duration: durations.fast, ease: easings.easeIn },
  },
};

export const fadeInScale: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: springs.smooth,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: { duration: durations.fast },
  },
};

// ============================================
// SLIDE VARIANTS
// ============================================

export const slideInLeft: Variants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: springs.smooth,
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: { duration: durations.fast },
  },
};

export const slideInRight: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: springs.smooth,
  },
  exit: {
    opacity: 0,
    x: 20,
    transition: { duration: durations.fast },
  },
};

// ============================================
// SCALE VARIANTS
// ============================================

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: springs.bouncy,
  },
  exit: {
    opacity: 0,
    scale: 0.8,
    transition: { duration: durations.fast },
  },
};

export const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.5 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: springs.bouncy,
  },
  exit: {
    opacity: 0,
    scale: 0.5,
    transition: { duration: durations.fast },
  },
};

// ============================================
// STAGGER VARIANTS
// ============================================

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      staggerChildren: 0.03,
      staggerDirection: -1,
    },
  },
};

export const staggerContainerSlow: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.15,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      staggerChildren: 0.05,
      staggerDirection: -1,
    },
  },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: springs.smooth,
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: durations.fast },
  },
};

export const staggerItemScale: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: springs.smooth,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: { duration: durations.fast },
  },
};

// ============================================
// PAGE TRANSITION VARIANTS
// ============================================

export const pageTransition: Variants = {
  hidden: {
    opacity: 0,
    y: 8,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: durations.slow,
      ease: easings.easeOut,
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: {
      duration: durations.normal,
      ease: easings.easeIn,
    },
  },
};

export const pageSlide: Variants = {
  hidden: {
    opacity: 0,
    x: 20,
  },
  visible: {
    opacity: 1,
    x: 0,
    transition: springs.gentle,
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: { duration: durations.normal },
  },
};

// ============================================
// CARD VARIANTS
// ============================================

export const cardHover = {
  rest: {
    scale: 1,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    transition: springs.snappy,
  },
  hover: {
    scale: 1.01,
    boxShadow: '0 10px 30px rgba(0,0,0,0.12)',
    transition: springs.snappy,
  },
  tap: {
    scale: 0.99,
    transition: springs.stiff,
  },
};

export const cardEntrance: Variants = {
  hidden: {
    opacity: 0,
    y: 20,
    scale: 0.98,
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: springs.smooth,
  },
};

// ============================================
// BUTTON VARIANTS
// ============================================

export const buttonTap = {
  scale: 0.97,
  transition: springs.stiff,
};

export const buttonHover = {
  scale: 1.02,
  transition: springs.snappy,
};

export const buttonVariants: Variants = {
  rest: { scale: 1 },
  hover: { scale: 1.02, transition: springs.snappy },
  tap: { scale: 0.97, transition: springs.stiff },
};

// ============================================
// SIDEBAR / NAVIGATION VARIANTS
// ============================================

export const sidebarVariants: Variants = {
  expanded: {
    width: 256,
    transition: springs.smooth,
  },
  collapsed: {
    width: 64,
    transition: springs.smooth,
  },
};

export const navItemVariants: Variants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: springs.smooth,
  },
};

export const activeIndicator: Variants = {
  hidden: { opacity: 0, scaleY: 0 },
  visible: {
    opacity: 1,
    scaleY: 1,
    transition: springs.bouncy,
  },
};

// ============================================
// MODAL / OVERLAY VARIANTS
// ============================================

export const overlayVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: durations.normal },
  },
  exit: {
    opacity: 0,
    transition: { duration: durations.fast },
  },
};

export const modalVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: 10,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: springs.smooth,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 10,
    transition: { duration: durations.fast },
  },
};

export const dropdownVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: -5,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: springs.snappy,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: -5,
    transition: { duration: durations.fast },
  },
};

// ============================================
// DATA VISUALIZATION VARIANTS
// ============================================

export const chartLine: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: durations.slowest, ease: easings.easeOut },
      opacity: { duration: durations.fast },
    },
  },
};

export const chartBar: Variants = {
  hidden: { scaleY: 0, opacity: 0 },
  visible: {
    scaleY: 1,
    opacity: 1,
    transition: springs.bouncy,
  },
};

export const gaugeProgress: Variants = {
  hidden: { pathLength: 0 },
  visible: (value: number) => ({
    pathLength: value,
    transition: { duration: durations.slower, ease: easings.easeOut },
  }),
};

export const dataPoint: Variants = {
  hidden: { scale: 0, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: springs.bouncy,
  },
};

// ============================================
// NOTIFICATION / TOAST VARIANTS
// ============================================

export const toastVariants: Variants = {
  hidden: {
    opacity: 0,
    x: 100,
    scale: 0.95,
  },
  visible: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: springs.smooth,
  },
  exit: {
    opacity: 0,
    x: 100,
    scale: 0.95,
    transition: { duration: durations.normal },
  },
};

export const notificationBadge: Variants = {
  hidden: { scale: 0 },
  visible: {
    scale: 1,
    transition: springs.bouncy,
  },
  pulse: {
    scale: [1, 1.2, 1],
    transition: {
      duration: 0.3,
      repeat: 2,
    },
  },
};

// ============================================
// SKELETON / LOADING VARIANTS
// ============================================

export const shimmer: Variants = {
  hidden: { x: '-100%' },
  visible: {
    x: '100%',
    transition: {
      repeat: Infinity,
      duration: 1.5,
      ease: 'linear',
    },
  },
};

export const pulse: Variants = {
  hidden: { opacity: 0.4 },
  visible: {
    opacity: [0.4, 0.7, 0.4],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

// ============================================
// URGENCY ANIMATIONS
// ============================================

export const urgencyPulse: Variants = {
  rest: { opacity: 1 },
  pulse: {
    opacity: [1, 0.7, 1],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

export const criticalGlow: Variants = {
  rest: {
    boxShadow: '0 0 0 0 rgba(220, 38, 38, 0)',
  },
  glow: {
    boxShadow: ['0 0 0 0 rgba(220, 38, 38, 0.4)', '0 0 0 8px rgba(220, 38, 38, 0)'],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

// ============================================
// ACCORDION VARIANTS
// ============================================

export const accordionContent: Variants = {
  hidden: {
    height: 0,
    opacity: 0,
  },
  visible: {
    height: 'auto',
    opacity: 1,
    transition: {
      height: springs.smooth,
      opacity: { duration: durations.normal, delay: 0.1 },
    },
  },
  exit: {
    height: 0,
    opacity: 0,
    transition: {
      opacity: { duration: durations.fast },
      height: { duration: durations.normal, delay: 0.05 },
    },
  },
};

export const accordionIcon: Variants = {
  closed: { rotate: 0 },
  open: {
    rotate: 180,
    transition: springs.snappy,
  },
};

// ============================================
// NUMBER ANIMATION HELPERS
// ============================================

export const numberTransition: Transition = {
  duration: durations.slower,
  ease: easings.easeOut,
};

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Creates a stagger container with custom timing
 */
export function createStaggerContainer(
  staggerChildren: number = 0.05,
  delayChildren: number = 0.1,
): Variants {
  return {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren, delayChildren },
    },
    exit: {
      opacity: 0,
      transition: { staggerChildren: staggerChildren / 2, staggerDirection: -1 },
    },
  };
}

/**
 * Creates a slide variant with custom direction and distance
 */
export function createSlideVariant(
  direction: 'up' | 'down' | 'left' | 'right',
  distance: number = 20,
): Variants {
  const sign = direction === 'down' || direction === 'right' ? 1 : -1;

  if (direction === 'up' || direction === 'down') {
    return {
      hidden: { opacity: 0, y: sign * distance },
      visible: {
        opacity: 1,
        y: 0,
        transition: springs.smooth,
      },
      exit: {
        opacity: 0,
        y: sign * distance * -0.5,
        transition: { duration: durations.fast },
      },
    };
  }

  return {
    hidden: { opacity: 0, x: sign * distance },
    visible: {
      opacity: 1,
      x: 0,
      transition: springs.smooth,
    },
    exit: {
      opacity: 0,
      x: sign * distance * -0.5,
      transition: { duration: durations.fast },
    },
  };
}

/**
 * Reduced motion safe animation
 * Returns static values when reduced motion is preferred
 */
export function getReducedMotionVariants(variants: Variants): Variants {
  if (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  ) {
    return {
      hidden: { opacity: 0 },
      visible: { opacity: 1 },
      exit: { opacity: 0 },
    };
  }
  return variants;
}

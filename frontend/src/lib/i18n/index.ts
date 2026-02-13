/**
 * RISKCAST i18n - Internationalization Support
 *
 * Supports:
 * - English (en) - Default
 * - Vietnamese (vi) - Primary target market
 *
 * Key translation categories:
 * - 7 Questions framework labels
 * - Action types
 * - Urgency/Severity levels
 * - Common UI elements
 */

export type Locale = 'en' | 'vi';

export interface Translations {
  // Navigation
  nav: {
    dashboard: string;
    decisions: string;
    signals: string;
    customers: string;
    settings: string;
    humanReview: string;
  };

  // 7 Questions Framework
  questions: {
    q1: { title: string; subtitle: string };
    q2: { title: string; subtitle: string };
    q3: { title: string; subtitle: string };
    q4: { title: string; subtitle: string };
    q5: { title: string; subtitle: string };
    q6: { title: string; subtitle: string };
    q7: { title: string; subtitle: string };
  };

  // Urgency Levels
  urgency: {
    immediate: string;
    urgent: string;
    soon: string;
    watch: string;
  };

  // Severity Levels
  severity: {
    critical: string;
    high: string;
    medium: string;
    low: string;
  };

  // Confidence Levels
  confidence: {
    high: string;
    medium: string;
    low: string;
  };

  // Action Types
  actions: {
    reroute: string;
    delay: string;
    insure: string;
    hedge: string;
    monitor: string;
    doNothing: string;
  };

  // Common UI
  common: {
    search: string;
    filter: string;
    sort: string;
    export: string;
    save: string;
    cancel: string;
    confirm: string;
    loading: string;
    error: string;
    errorDescription: string;
    errorTitle: string;
    retry: string;
    viewAll: string;
    showMore: string;
    showLess: string;
    offline: string;
    unknownError: string;
    connectionFailed: string;
  };

  // Time & Dates
  time: {
    now: string;
    today: string;
    yesterday: string;
    daysAgo: string;
    hoursAgo: string;
    minutesAgo: string;
    deadline: string;
    remaining: string;
    expired: string;
  };

  // Financial
  financial: {
    exposure: string;
    cost: string;
    benefit: string;
    savings: string;
    loss: string;
    confidenceInterval: string;
  };

  // Decision-specific
  decision: {
    acknowledge: string;
    override: string;
    escalate: string;
    pending: string;
    acknowledged: string;
    overridden: string;
    escalated: string;
    expired: string;
  };
}

// English translations (default)
export const en: Translations = {
  nav: {
    dashboard: 'Dashboard',
    decisions: 'Decisions',
    signals: 'Signals',
    customers: 'Customers',
    settings: 'Settings',
    humanReview: 'Human Review',
  },

  questions: {
    q1: { title: 'What is Happening?', subtitle: 'Event summary and impact' },
    q2: { title: 'When?', subtitle: 'Timeline and urgency' },
    q3: { title: 'How Bad Is It?', subtitle: 'Financial exposure and severity' },
    q4: { title: 'Why?', subtitle: 'Root cause analysis' },
    q5: { title: 'What To Do Now?', subtitle: 'Recommended action' },
    q6: { title: 'How Confident?', subtitle: 'Confidence level and factors' },
    q7: { title: 'What If Nothing?', subtitle: 'Cost of inaction' },
  },

  urgency: {
    immediate: 'Immediate',
    urgent: 'Urgent',
    soon: 'Soon',
    watch: 'Watch',
  },

  severity: {
    critical: 'Critical',
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  },

  confidence: {
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  },

  actions: {
    reroute: 'Reroute',
    delay: 'Delay',
    insure: 'Insure',
    hedge: 'Hedge',
    monitor: 'Monitor',
    doNothing: 'Do Nothing',
  },

  common: {
    search: 'Search',
    filter: 'Filter',
    sort: 'Sort',
    export: 'Export',
    save: 'Save',
    cancel: 'Cancel',
    confirm: 'Confirm',
    loading: 'Loading...',
    error: 'Error',
    errorDescription: 'Something went wrong. Please try again.',
    errorTitle: 'Something went wrong',
    retry: 'Retry',
    viewAll: 'View all',
    showMore: 'Show more',
    showLess: 'Show less',
    offline: 'Server connection lost. Reconnecting...',
    unknownError: 'An unexpected error occurred.',
    connectionFailed: 'Could not connect to server. Please try again.',
  },

  time: {
    now: 'Now',
    today: 'Today',
    yesterday: 'Yesterday',
    daysAgo: 'days ago',
    hoursAgo: 'hours ago',
    minutesAgo: 'minutes ago',
    deadline: 'Deadline',
    remaining: 'remaining',
    expired: 'Expired',
  },

  financial: {
    exposure: 'Exposure',
    cost: 'Cost',
    benefit: 'Benefit',
    savings: 'Savings',
    loss: 'Loss',
    confidenceInterval: 'Confidence Interval',
  },

  decision: {
    acknowledge: 'Acknowledge',
    override: 'Override',
    escalate: 'Escalate',
    pending: 'Pending',
    acknowledged: 'Acknowledged',
    overridden: 'Overridden',
    escalated: 'Escalated',
    expired: 'Expired',
  },
};

// Vietnamese translations
export const vi: Translations = {
  nav: {
    dashboard: 'Bảng điều khiển',
    decisions: 'Quyết định',
    signals: 'Tín hiệu',
    customers: 'Khách hàng',
    settings: 'Cài đặt',
    humanReview: 'Xem xét thủ công',
  },

  questions: {
    q1: { title: 'Chuyện gì đang xảy ra?', subtitle: 'Tóm tắt sự kiện và tác động' },
    q2: { title: 'Khi nào?', subtitle: 'Timeline và mức độ khẩn cấp' },
    q3: { title: 'Nghiêm trọng thế nào?', subtitle: 'Mức độ thiệt hại tài chính' },
    q4: { title: 'Tại sao?', subtitle: 'Phân tích nguyên nhân gốc rễ' },
    q5: { title: 'Cần làm gì ngay?', subtitle: 'Hành động được khuyến nghị' },
    q6: { title: 'Độ tin cậy?', subtitle: 'Mức độ và yếu tố tin cậy' },
    q7: { title: 'Nếu không làm gì?', subtitle: 'Chi phí của sự không hành động' },
  },

  urgency: {
    immediate: 'Ngay lập tức',
    urgent: 'Khẩn cấp',
    soon: 'Sớm',
    watch: 'Theo dõi',
  },

  severity: {
    critical: 'Nghiêm trọng',
    high: 'Cao',
    medium: 'Trung bình',
    low: 'Thấp',
  },

  confidence: {
    high: 'Cao',
    medium: 'Trung bình',
    low: 'Thấp',
  },

  actions: {
    reroute: 'Chuyển tuyến',
    delay: 'Trì hoãn',
    insure: 'Bảo hiểm',
    hedge: 'Phòng hộ',
    monitor: 'Theo dõi',
    doNothing: 'Không hành động',
  },

  common: {
    search: 'Tìm kiếm',
    filter: 'Lọc',
    sort: 'Sắp xếp',
    export: 'Xuất',
    save: 'Lưu',
    cancel: 'Hủy',
    confirm: 'Xác nhận',
    loading: 'Đang tải...',
    error: 'Lỗi',
    errorDescription: 'Đã xảy ra lỗi. Vui lòng thử lại.',
    errorTitle: 'Đã xảy ra lỗi',
    retry: 'Thử lại',
    viewAll: 'Xem tất cả',
    showMore: 'Xem thêm',
    showLess: 'Thu gọn',
    offline: 'Mất kết nối server. Đang thử kết nối lại...',
    unknownError: 'Đã xảy ra lỗi không mong muốn.',
    connectionFailed: 'Không thể kết nối server. Vui lòng thử lại.',
  },

  time: {
    now: 'Bây giờ',
    today: 'Hôm nay',
    yesterday: 'Hôm qua',
    daysAgo: 'ngày trước',
    hoursAgo: 'giờ trước',
    minutesAgo: 'phút trước',
    deadline: 'Hạn chót',
    remaining: 'còn lại',
    expired: 'Đã hết hạn',
  },

  financial: {
    exposure: 'Mức độ rủi ro',
    cost: 'Chi phí',
    benefit: 'Lợi ích',
    savings: 'Tiết kiệm',
    loss: 'Tổn thất',
    confidenceInterval: 'Khoảng tin cậy',
  },

  decision: {
    acknowledge: 'Xác nhận',
    override: 'Ghi đè',
    escalate: 'Leo thang',
    pending: 'Đang chờ',
    acknowledged: 'Đã xác nhận',
    overridden: 'Đã ghi đè',
    escalated: 'Đã leo thang',
    expired: 'Đã hết hạn',
  },
};

// Translation dictionary
const translations: Record<Locale, Translations> = { en, vi };

// Get translations for a locale
export function getTranslations(locale: Locale = 'en'): Translations {
  return translations[locale] || en;
}

// Translation hook context value
export interface I18nContext {
  locale: Locale;
  t: Translations;
  setLocale: (locale: Locale) => void;
}

// Re-export hooks from provider
export { useTranslations, useI18n, useLocale } from './provider';
export { useFormatters } from './useFormatters';

export default { en, vi, getTranslations };

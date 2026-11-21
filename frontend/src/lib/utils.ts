import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
export const date = (value: string) => new Intl.DateTimeFormat('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));

export function relativeTime(value: string) {
 const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
 if (minutes < 1) return '剛剛';
 if (minutes < 60) return `${minutes} 分鐘前`;
 if (minutes < 1440) return `${Math.floor(minutes / 60)} 小時前`;
 if (minutes < 10080) return `${Math.floor(minutes / 1440)} 天前`;
 return new Intl.DateTimeFormat('zh-TW', { month: 'numeric', day: 'numeric' }).format(new Date(value));
}

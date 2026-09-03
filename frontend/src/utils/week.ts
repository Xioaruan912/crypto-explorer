export interface WeekDay {
  date: Date;
  iso: string;
  weekday: string;
  shortDate: string;
  isToday: boolean;
}

export function startOfWeek(input: Date): Date {
  const date = new Date(input.getFullYear(), input.getMonth(), input.getDate());
  const mondayOffset = (date.getDay() + 6) % 7;
  date.setDate(date.getDate() - mondayOffset);
  return date;
}

export function addDays(input: Date, days: number): Date {
  const date = new Date(input.getFullYear(), input.getMonth(), input.getDate());
  date.setDate(date.getDate() + days);
  return date;
}

export function toLocalISODate(input: Date): string {
  const year = input.getFullYear();
  const month = String(input.getMonth() + 1).padStart(2, '0');
  const day = String(input.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function getWeekDays(weekStart: Date): WeekDay[] {
  const today = toLocalISODate(new Date());
  const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  return weekdays.map((weekday, index) => {
    const date = addDays(weekStart, index);
    const iso = toLocalISODate(date);
    return {
      date,
      iso,
      weekday,
      shortDate: `${date.getMonth() + 1}/${date.getDate()}`,
      isToday: iso === today,
    };
  });
}

export function formatWeekRange(weekStart: Date): string {
  const end = addDays(weekStart, 6);
  const sameYear = weekStart.getFullYear() === end.getFullYear();
  if (sameYear) {
    return `${weekStart.getFullYear()}年 ${weekStart.getMonth() + 1}/${weekStart.getDate()} – ${end.getMonth() + 1}/${end.getDate()}`;
  }
  return `${weekStart.getFullYear()}年 ${weekStart.getMonth() + 1}/${weekStart.getDate()} – ${end.getFullYear()}年 ${end.getMonth() + 1}/${end.getDate()}`;
}

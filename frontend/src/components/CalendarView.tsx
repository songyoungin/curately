import { useState, useMemo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import type { NewsletterEdition } from "../types";

interface CalendarViewProps {
  editions: NewsletterEdition[];
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
}

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function formatMonth(year: number, month: number): string {
  const date = new Date(year, month);
  return date.toLocaleDateString("en-US", { year: "numeric", month: "long" });
}

function toDateString(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export default function CalendarView({
  editions,
  selectedDate,
  onSelectDate,
}: CalendarViewProps) {
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());

  const editionDates = useMemo(() => {
    const set = new Set<string>();
    for (const edition of editions) {
      set.add(edition.date);
    }
    return set;
  }, [editions]);

  const editionCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const edition of editions) {
      map.set(edition.date, edition.article_count);
    }
    return map;
  }, [editions]);

  const calendarDays = useMemo(() => {
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

    const days: (number | null)[] = [];
    for (let i = 0; i < firstDay; i++) {
      days.push(null);
    }
    for (let d = 1; d <= daysInMonth; d++) {
      days.push(d);
    }
    return days;
  }, [viewYear, viewMonth]);

  function goToPrevMonth() {
    if (viewMonth === 0) {
      setViewYear(viewYear - 1);
      setViewMonth(11);
    } else {
      setViewMonth(viewMonth - 1);
    }
  }

  function goToNextMonth() {
    if (viewMonth === 11) {
      setViewYear(viewYear + 1);
      setViewMonth(0);
    } else {
      setViewMonth(viewMonth + 1);
    }
  }

  const todayStr = toDateString(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-6">
      {/* Header with month navigation */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={goToPrevMonth}
          className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-600"
          aria-label="Previous month"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <h3 className="text-lg font-semibold text-gray-900">
          {formatMonth(viewYear, viewMonth)}
        </h3>
        <button
          onClick={goToNextMonth}
          className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-600"
          aria-label="Next month"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-2">
        {WEEKDAY_LABELS.map((label) => (
          <div
            key={label}
            className="text-center text-xs font-medium text-gray-500 py-1"
          >
            {label}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {calendarDays.map((day, index) => {
          if (day === null) {
            return <div key={`empty-${index}`} />;
          }

          const dateStr = toDateString(viewYear, viewMonth, day);
          const hasEdition = editionDates.has(dateStr);
          const isSelected = dateStr === selectedDate;
          const isToday = dateStr === todayStr;
          const articleCount = editionCounts.get(dateStr);

          return (
            <button
              key={dateStr}
              onClick={() => hasEdition && onSelectDate(dateStr)}
              disabled={!hasEdition}
              className={`
                relative flex flex-col items-center justify-center py-2 rounded-lg text-sm transition-colors
                ${isSelected ? "bg-blue-600 text-white" : ""}
                ${!isSelected && hasEdition ? "hover:bg-blue-50 text-gray-900 cursor-pointer font-medium" : ""}
                ${!isSelected && !hasEdition ? "text-gray-300 cursor-default" : ""}
                ${isToday && !isSelected ? "ring-2 ring-blue-400 ring-inset" : ""}
              `}
            >
              <span>{day}</span>
              {hasEdition && (
                <span
                  className={`text-[10px] leading-none mt-0.5 ${isSelected ? "text-blue-200" : "text-blue-500"}`}
                >
                  {articleCount}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

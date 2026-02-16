interface DateHeaderProps {
  date: string;
  articleCount: number;
}

export default function DateHeader({ date, articleCount }: DateHeaderProps) {
  const formatted = new Date(date + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="flex items-center justify-between pb-4 border-b border-gray-200">
      <h2 className="text-2xl font-bold text-gray-900">{formatted}</h2>
      <span className="text-sm text-gray-500">
        {articleCount} {articleCount === 1 ? "article" : "articles"}
      </span>
    </div>
  );
}

import type { Article } from "../types/article";
import ArticleCard from "./ArticleCard";

interface CategorySectionProps {
  category: string;
  articles: Article[];
  onLike: (articleId: number) => void;
  onBookmark: (articleId: number) => void;
}

export default function CategorySection({
  category,
  articles,
  onLike,
  onBookmark,
}: CategorySectionProps) {
  return (
    <section className="mb-8">
      <div className="flex items-center gap-3 mb-4">
        <span className="font-semibold text-gray-700 whitespace-nowrap">
          {category}
        </span>
        <div className="flex-1 border-t border-gray-200" />
      </div>
      <div className="flex flex-col gap-4">
        {articles.map((article) => (
          <ArticleCard
            key={article.id}
            article={article}
            onLike={onLike}
            onBookmark={onBookmark}
          />
        ))}
      </div>
    </section>
  );
}

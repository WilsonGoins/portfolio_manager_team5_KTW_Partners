import { useEffect, useState } from 'react';
import { NewsArticleCard } from './NewsArticleCard.jsx';
import { NewsArticleSkeleton } from './NewsArticleSkeleton.jsx';
import './ExploreNews.css';

export function ExploreNews() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        const res = await fetch("api/news");
        const data = await res.json();
        setArticles(data);
      } catch (err) {
        console.error('Failed to get news:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchNews();
  }, []);

  return (
    <div className="explore-news-content">
      <div className="section-header">
        <h2>Market News</h2>
      </div>

      {loading ? (
        Array.from({ length: 3 }).map((_, idx) => (
          <NewsArticleSkeleton key={idx} />
        ))
      ) : articles && articles.length > 0 ? (
        articles.map((article) => (
          <NewsArticleCard key={article.title} data={article} />
        ))
      ) : (
        <p className="no-news">No news available.</p>
      )}
    </div>
  );
}

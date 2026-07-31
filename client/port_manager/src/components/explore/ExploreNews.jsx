import { useEffect, useState } from 'react';
import { NewsArticleCard } from './NewsArticleCard.jsx';
import './ExploreNews.css';

export function ExploreNews() {
  const [articles, setArticles] = useState([]);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const res = await fetch("api/news");
        const data = await res.json();

        setArticles(data);
      }
      catch (err) {
        console.error('Failed to get news:', err);
      }
      finally {

      }
    };
  fetchNews();
  }, []);

  return (
    <div className="explore-news-content">
      <div className="section-header">
        <h2>Market News</h2>
      </div>

      {articles && articles.length > 0 ? (
        articles.map(article => (
          <NewsArticleCard key={article.title} data={article} />
        ))
      ) : (
        <p className="no-news">No news available.</p>
      )}
    </div>
  );
}

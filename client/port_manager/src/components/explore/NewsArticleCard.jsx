import './NewsArticleCard.css'

export function NewsArticleCard({ data }) {
  const {
    image_url,
    publisher,
    ticker,
    title,
    url,
  } = data;

  return (
    <div className='news-card'>
      {image_url && (
        <div className='img-container'>
          <img src={image_url} alt={title} />
        </div>
      )}
      
      <div className='news-content'>
        <div className='news-meta'>
          {publisher && <span className='news-publisher'>{publisher}</span>}
          {ticker && <span className='news-ticker'>{ticker}</span>}
        </div>

        <h4 className='news-title'>
          <a href={url} target="_blank" rel="noopener noreferrer">
            {title}
          </a>
        </h4>
      </div>
    </div>
  )
}

import { PortfolioValueCard } from "../components/overview/PortfolioValueCard"
import { WatchListCard } from "../components/overview/WatchListCard"
import "./Overview.css"

export function Overview() {
  return (
    <>
      <h2>Overview Page</h2>

      <div className="overview-card-outer">
          <div className="overview-card-inner">
            <PortfolioValueCard />
            <PortfolioValueCard />
          </div>
          <div className="overview-card-inner">
            <WatchListCard />
            <WatchListCard />
          </div>
        
      </div>
    </>
  )
}

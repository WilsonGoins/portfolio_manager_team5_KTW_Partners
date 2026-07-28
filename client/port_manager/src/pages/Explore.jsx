import {ExploreSecurities} from "../components/explore/ExploreSecurities";
import {ExploreNews} from "../components/explore/ExploreNews";

export function Explore() {
  return (
    <>
      <div className="explore-page">
        <div className="explore-main-content">
          <ExploreSecurities />
          <ExploreNews />
        </div>
      </div>
    </>
  )
}
